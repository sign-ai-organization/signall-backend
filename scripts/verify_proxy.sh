#!/usr/bin/env bash
# Verifica que el proxy TLS del sistema esté arriba y sirviendo.
#
# El proxy (Caddy) vive en `docker-compose.host.yml`, no en el archivo base, así que
# `docker compose up -d` a secas deja el backend arriba y el proxy abajo. Ese estado se
# confunde con un error del backend: el 8080 responde y la app `demo` no conecta porque
# habla `wss://`. Este script lo detecta y sale con código 1.
#
#   scripts/verify_proxy.sh
#
# Variables:
#   PROXY_HEALTH_URL   URL a pedir (default https://127.0.0.1/health)
#
# Diseño y fases: deploy/README.md y docs/plan-proxy-tls.md.

set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 1

compose=(docker compose -f docker-compose.yml -f docker-compose.host.yml)
ca="deploy/certs/lab-ca.crt"
url="${PROXY_HEALTH_URL:-https://127.0.0.1/health}"

fail() {
    echo "FALLA: $*" >&2
    exit 1
}

# 1. El certificado de laboratorio. Sin la CA no se puede verificar el TLS, y sin el
#    certificado y la clave el contenedor de Caddy no arranca.
[ -f "$ca" ] || fail "no existe $ca: el certificado de laboratorio no se emitió en esta máquina.
       Emitirlo con mkcert según deploy/README.md (una vez por máquina)."
for f in deploy/certs/lab.pem deploy/certs/lab-key.pem; do
    [ -f "$f" ] || fail "no existe $f: el servicio caddy no puede arrancar sin certificado y clave.
       Emitirlos con mkcert según deploy/README.md."
done

# 2. El contenedor tiene que estar corriendo, no solo existir.
if ! "${compose[@]}" ps caddy 2>/dev/null | grep -q 'signall-backend-caddy-1.*Up'; then
    fail "el proxy no está arriba (se esperaba signall-backend-caddy-1 en Up).
       Se levantó probablemente con un solo archivo de Compose. Levantar el sistema completo:
           docker compose -f docker-compose.yml -f docker-compose.host.yml up -d
       Si el contenedor existe y reinicia, ver el motivo con:
           docker compose -f docker-compose.yml -f docker-compose.host.yml logs caddy"
fi

# 3. Y tiene que responder por TLS. El backend por el 8080 no prueba nada del proxy.
if ! body="$(curl -sS --fail --cacert "$ca" "$url" 2>&1)"; then
    fail "el proxy no respondió en $url:
       $body
       Si el mensaje es '502 Bad Gateway', el proxy está bien y el backend no:
           curl -sS http://localhost:8080/health
       Si es un error de conexión, Caddy no está escuchando: revisar los logs del paso 2."
fi

echo "OK: el proxy TLS responde en $url"
echo "    $body"
