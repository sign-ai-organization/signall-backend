"""Verifies what `/health` and `/metrics.json` publish.

Two decisions of the owner (2026-11-03):

- **`/metrics.json` does not publish internal addresses.** It has no
  authentication and it is read from a phone during a demo, so the host and the
  port of the LLM and of the STT are replaced with `***`. The scheme and the
  path stay, because they identify the endpoint without saying which machine
  serves it.
- **`/health` says whether the catalog is loaded.** A backend that started
  without its catalog is answering, but it cannot translate: every gloss comes
  out as unavailable. Reporting `ok` in that state hides a failure the operator
  can still fix by restarting the service, so the status becomes `degraded`.

This script needs neither Neon nor the network: the state of the app is filled
with doubles and the endpoint functions are called directly. Run it with

    python -m scripts.verify_endpoints
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")
os.environ["LLM_BASE_URL"] = "http://host.docker.internal:11434/v1"
os.environ["STT_WS_URL"] = "ws://stt:8000/ws/transcribe"

from app.config.settings import settings  # noqa: E402
from app.main import _redact_url, app, health, metrics_json  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

failures: list[str] = []


def check(name: str, got, expected) -> None:
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        expected: {expected!r}")
        print(f"        got:      {got!r}")
        failures.append(name)


def check_that(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        if detail:
            print(f"        {detail}")
        failures.append(name)


class FakeCache:
    is_loaded = True
    row_count = 12


class FakeCatalog:
    def __init__(self, glosses: int) -> None:
        self.cache = {f"GLS-{i:02d}": object() for i in range(glosses)}


class FakeReloadableCache:
    """The only method `/admin/cache/reload` uses."""

    def __init__(self, rows: int = 3) -> None:
        self.rows = rows
        self.row_count = 0
        self.reloads = 0
        self.fail = False

    async def reload(self) -> int:
        self.reloads += 1
        if self.fail:
            raise RuntimeError("neon did not answer")
        self.row_count = self.rows
        return self.rows


def check_admin_reload() -> None:
    """The admin route (fase 5) is closed unless `ADMIN_TOKEN` is set.

    A route that makes the service re-read a table has to be the one thing that
    is not open: the deployment without a token answers 404, as if the route did
    not exist, and a wrong token is 403 without touching the cache.
    """
    print("\n/admin/cache/reload only exists when ADMIN_TOKEN is configured")
    client = TestClient(app)
    configured = settings.admin_token

    settings.admin_token = ""
    response = client.post("/admin/cache/reload")
    check("without a configured token the route is not there", response.status_code, 404)

    settings.admin_token = "token-de-prueba"
    cache = FakeReloadableCache()
    app.state.semantic_cache = cache

    response = client.post("/admin/cache/reload")
    check("without the header it is forbidden", response.status_code, 403)
    response = client.post("/admin/cache/reload", headers={"X-Admin-Token": "otro"})
    check("with the wrong token it is forbidden", response.status_code, 403)
    check_that("a rejected call does not reload anything", cache.reloads == 0)

    response = client.post("/admin/cache/reload", headers={"X-Admin-Token": "token-de-prueba"})
    check("with the right token it answers 200", response.status_code, 200)
    check("and says how many rows were loaded", response.json()["rows"], 3)
    check("and how many are in memory", response.json()["cache_rows"], 3)

    cache.fail = True
    response = client.post("/admin/cache/reload", headers={"X-Admin-Token": "token-de-prueba"})
    check("a failed read answers 503", response.status_code, 503)
    check_that(
        "and says the previous cache is still serving",
        "se sigue usando la anterior" in response.json()["detail"],
    )

    settings.admin_token = configured


def main() -> None:
    print("\nan address keeps the scheme and the path, not the machine")
    check("the LLM endpoint", _redact_url("http://host.docker.internal:11434/v1"), "http://***/v1")
    check("the STT endpoint", _redact_url("ws://stt:8000/ws/transcribe"), "ws://***/ws/transcribe")
    check("an empty address stays empty", _redact_url(""), "")
    check("a value that is not a URL is hidden", _redact_url("not a url"), "***")
    check("credentials do not survive", _redact_url("http://user:pass@db:5432/db"), "http://***/db")

    print("\n/metrics.json does not publish an internal address")
    app.state.semantic_cache = FakeCache()
    payload = metrics_json()
    config = payload["config"]
    check("the LLM address is hidden", config["llm_base_url"], "http://***/v1")
    check("the STT address is hidden", config["stt_ws_url"], "ws://***/ws/transcribe")
    check("the model name still travels", config["llm_model"], settings.llm_model)
    for secret in ("host.docker.internal", "11434", "stt:", "8000"):
        check_that(f"the payload does not contain {secret!r}", secret not in str(payload))

    print("\n/health reports a loaded catalog as ok")
    app.state.catalog_repository = FakeCatalog(50)
    app.state.stt_config = {"silence_timeout_ms": 1500}
    body = health()
    check("the status", body["status"], "ok")
    check("the catalog is loaded", body["catalog_loaded"], True)
    check("and the count is published", body["catalog_glosses"], 50)
    check("the cache still travels", body["cache_rows"], 12)
    check("and the STT configuration too", body["silence_timeout_ms"], 1500)

    print("\n/health reports an empty catalog as degraded")
    app.state.catalog_repository = FakeCatalog(0)
    body = health()
    check("the status", body["status"], "degraded")
    check("the catalog is not loaded", body["catalog_loaded"], False)
    check("and the count is zero", body["catalog_glosses"], 0)

    print("\n/health does not break before the state exists")
    del app.state.catalog_repository
    del app.state.semantic_cache
    body = health()
    check("the status", body["status"], "degraded")
    check("the count", body["catalog_glosses"], 0)

    check_admin_reload()

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("all OK")


if __name__ == "__main__":
    main()
