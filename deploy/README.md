# Despliegue con TLS de laboratorio

`Caddyfile` es el proxy inverso que termina el TLS delante del backend. Escucha en el
443, presenta un certificado emitido por una autoridad de laboratorio y reenvía todo al
backend por `127.0.0.1:8080`, que sigue escuchando en claro y no sabe que el proxy
existe. El servicio `caddy` vive en `docker-compose.host.yml`, en red de host: desde la
red de compose no alcanza al backend por loopback.

El plan completo, con las fases y las verificaciones, está en
[`docs/plan-proxy-tls.md`](../docs/plan-proxy-tls.md).

## Emitir el certificado (una vez por máquina)

```bash
mkdir -p deploy/certs
mkcert -install
mkcert -cert-file deploy/certs/lab.pem -key-file deploy/certs/lab-key.pem \
  127.0.0.1 localhost 192.168.80.49
cp "$(mkcert -CAROOT)/rootCA.pem" deploy/certs/lab-ca.crt
openssl verify -CAfile deploy/certs/lab-ca.crt deploy/certs/lab.pem
```

`deploy/certs/` está en `.gitignore` y solo se conserva el `.gitkeep`: la clave privada
no entra al repositorio. **Al clonar hay que reemitir los tres archivos**, y si la IP de
la máquina cambia (es DHCP) hay que reemitir el certificado o reservar la IP.

Un solo certificado sirve para los dos caminos: `127.0.0.1` para USB con `adb reverse` y
`192.168.80.49` para Wi-Fi.

## Levantar

```bash
docker compose -f docker-compose.yml -f docker-compose.host.yml up -d
curl --cacert deploy/certs/lab-ca.crt https://127.0.0.1/health
```

Sin el `--cacert` el `curl` falla: la CA de laboratorio no está en el almacén del
sistema. El backend por el 8080 sigue respondiendo igual que siempre.

## Probar desde el teléfono

```bash
adb push deploy/certs/lab-ca.crt /sdcard/Download/
# Ajustes → Seguridad → Cifrado y credenciales → Instalar un certificado → CA
adb reverse tcp:8443 tcp:443
cd ../signall-android && ./gradlew installDemo
adb logcat -s SignAiNet      # esperado: sesión abierta: wss://… (TLS)
```

El 443 no se puede mapear en el teléfono (`cannot bind listener: Permission denied`), por
eso el 8443 del lado del teléfono; el certificado no depende del puerto. El APK `demo`
comparte `applicationId` con `debug` y lo reemplaza: para volver a medir latencia hay que
reinstalar `debug`.
