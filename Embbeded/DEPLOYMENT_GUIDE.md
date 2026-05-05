# Guia corta de despliegue - Firmware IoT Pico 2 W

> La guia principal de operacion vive en [`README.md`](README.md). Este archivo es solo una referencia rapida para flashear MicroPython y copiar el firmware.

## Archivos a copiar

Copia todos los archivos de `src/` a la **raiz** del filesystem de la Pico, no dentro de una carpeta `src/`.

```text
boot.py
main.py
device_config.py
cloud_buffer.py
remote_questdb_service.py
sensor_scd41.py
scd4x.py
timer_service.py
wifi.py
logger.py
index.html
setup.html
```

Archivos persistentes generados por el nodo:

```text
device_config.json
wifi_config.json
cloud_buffer.json
```

## Proceso resumido

1. Descarga el `.uf2` de MicroPython para Raspberry Pi Pico 2 W desde [micropython.org/download](https://micropython.org/download/).
2. Conecta la Pico manteniendo presionado `BOOTSEL`.
3. Arrastra el `.uf2` al almacenamiento USB.
4. Abre Thonny, PyCharm, `mpremote` o tu herramienta MicroPython.
5. Sube todos los archivos de `src/` a la raiz de la Pico.
6. Reinicia con `Ctrl + D`, boton `RESET` o reconectando USB.

Verificacion desde REPL:

```python
import os
print(os.listdir())
```

## Despues del reinicio

- Si no hay una red valida, el nodo activa `setup_ap`.
- En `setup_ap`, conectate a `FDL-Setup-*` y abre `http://192.168.4.1`.
- Si la red guardada funciona, el nodo entra a `STA`.
- En `STA`, abre `http://<ip-del-nodo>` o `http://<mdns_hostname>.local`.
- Para crear un deployment, usa la UI local y llena nombre, latitud y longitud.

## Troubleshooting minimo

### El servidor no arranca

1. Confirma que `main.py`, `index.html`, `setup.html` y `wifi.py` estan en la raiz.
2. Revisa el error en el REPL.
3. Vuelve a copiar todos los archivos de `src/` si falta alguno.

### El nodo no conecta a WiFi

1. Confirma que la red es 2.4 GHz.
2. Busca el AP `FDL-Setup-*`.
3. Conectate al AP y abre `http://192.168.4.1`.
4. Corrige o agrega la red WiFi.

### `.local` no abre

1. Usa la IP del nodo como fallback.
2. Confirma que PC y Pico estan en la misma red.
3. Revisa que mDNS este habilitado.

### El sensor no reporta datos

1. Espera el primer ciclo de lectura.
2. Verifica cableado I2C.
3. Revisa logs desde la UI local.
