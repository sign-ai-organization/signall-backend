#!/usr/bin/env python3
"""¿Las sesiones del backend sueltan el socket con el STT al cerrarse?

Cada sesión de `/ws/translate` abre un WebSocket al STT
(`SttServiceClientImpl`) y lo cierra en el `finally` de `translation_session`.
Abrir y cerrar una sesión sin que ese `finally` corro deja el socket colgado
para siempre: la fuga es lineal con el número de sesiones y no la delata ningún
contador del servicio.

La medición cuenta los sockets **establecidos cuyo par es el puerto del STT**,
en el host. Cuenta solo el lado del backend —el que tiene el puerto efímero
local— y no el del `docker-proxy`, que es el mismo cable visto del otro lado.

    python3 tools/verificar-conexiones-stt.py [n_sesiones]

Sale con código 1 si al final quedan conexiones colgando.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time

import websockets

URL = "ws://127.0.0.1:8080/ws/translate"
STT_PUERTO = 8000

# Un frame de 30 ms de silencio digital: abre el socket con el STT sin ensuciar
# el VAD. `end` cierra el utterance y obliga al STT a responder, así que cada
# iteración es una sesión real y no un socket abierto al vacío.
SILENCIO = bytes(960)


def conexiones_stt() -> int:
    out = subprocess.run(
        ["ss", "-tn", "state", "established", f"( dport = :{STT_PUERTO} )"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    total = 0
    for linea in out.splitlines()[1:]:
        campos = linea.split()
        if len(campos) < 4:
            continue
        local, remoto = campos[2], campos[3]
        if local.rsplit(":", 1)[1] != str(STT_PUERTO):
            total += 1
    return total


async def sesion() -> None:
    async with websockets.connect(URL, max_size=None) as ws:
        await ws.send(SILENCIO)
        await asyncio.sleep(0.2)
        await ws.send(json.dumps({"type": "end"}))
        try:
            await asyncio.wait_for(ws.recv(), timeout=5)
        except Exception:  # noqa: BLE001 - un final vacío o un error no invalidan la prueba
            pass


async def esperar_a_que_baje_de(hasta: int, segundos: float) -> tuple[int, float]:
    """Espera a que el número de conexiones baje de [hasta]. Devuelve (n, segundos).

    Espera en vez de contar una vez porque un socket que se acaba de cerrar sigue
    apareciendo en `ss` un rato, y una lectura puntual da un número que no tiene
    nada que ver con las sesiones de la prueba. Acá lo que se afirma es
    "después de un rato no quedó ninguna", que es exactamente lo que se quiere
    demostrar.
    """
    inicio = time.monotonic()
    limite = inicio + segundos
    while True:
        actual = conexiones_stt()
        if actual <= hasta:
            return actual, time.monotonic() - inicio
        if time.monotonic() >= limite:
            return actual, time.monotonic() - inicio
        await asyncio.sleep(0.5)


async def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    antes, _ = await esperar_a_que_baje_de(0, 10.0)
    if antes:
        # Lo más probable es la app del teléfono con una sesión abierta: cada
        # sesión del backend tiene su propio socket con el STT. No rompe la
        # medición —la pregunta es si vuelve a la línea de partida—, pero si esa
        # sesión se reconecta durante la corrida el número no es atribuible a
        # estas sesiones.
        print(f"aviso: la línea de partida es {antes} conexión(es) al STT "
              f"(¿la app del teléfono está abierta?). Se mide si la corrida vuelve "
              f"a ese número, no a cero.")
    for _ in range(n):
        await sesion()
        await asyncio.sleep(0.3)
    despues, espera = await esperar_a_que_baje_de(antes, 20.0)
    print(f"sesiones abiertas y cerradas: {n}")
    print(f"conexiones al STT antes:   {antes}")
    print(f"conexiones al STT después: {despues} (esperó {espera:.1f} s)")
    delta = despues - antes
    if delta > 0:
        print(f"conexiones que quedaron colgando: {delta}")
    elif delta == 0:
        print("conexiones que quedaron colgando: 0")
    else:
        # Negativo: se cerraron conexiones de antes (típico: la app del teléfono
        # estaba abierta y se cerró mientras corría la prueba).
        print(f"conexiones que quedaron colgando: 0 (y se cerraron {-delta} que "
              f"ya estaban antes de la prueba)")
    if despues > antes:
        print("FALLA: `translation_session` nunca llegó al `finally`; el socket con el STT")
        print("queda abierto por sesión. Ver `_forward_transcripts`, que bloquea en `recv()`")
        print("esperando un mensaje del STT que no llega, y el `asyncio.gather` de `router.py`")
        print("la espera para siempre.")
        return 1
    print("ok: cada sesión soltó su socket con el STT")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))