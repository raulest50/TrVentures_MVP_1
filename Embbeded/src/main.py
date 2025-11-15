import socket
import time
import ujson as json

from wifi import connect_wifi, ensure_connected
from sensor_scd41 import init_sensor, update_sensor, get_latest_readings

# ---- Cargar index.html solamente una vez al inicio ----
with open("index.html", "r") as f:
    INDEX_HTML = f.read()

# ---- Conexión WiFi ----
wlan = connect_wifi(do_scan=True, verbose=True)

if not wlan or not wlan.isconnected():
    print("\n❌ No hay WiFi, el servidor HTTP no se iniciará.")
    while True:
        time.sleep(5)

# ---- Inicializar sensor SCD41 ----
init_sensor()

# ---- Servidor HTTP ----
addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
s = socket.socket()
# En algunas builds de MicroPython SO_REUSEADDR está disponible;
# si no, puedes comentar la siguiente línea.
try:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
except Exception:
    pass

s.bind(addr)
s.listen(2)
s.settimeout(0.3)

print("Servidor web en http://%s" % wlan.ifconfig()[0])

HTML_HEADER = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Connection: close\r\n\r\n"
)

JSON_HEADER = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: application/json\r\n"
    "Connection: close\r\n\r\n"
)


def handle_client(cl):
    try:
        request = cl.recv(1024)
        if not request:
            return

        first_line = request.split(b"\r\n", 1)[0]
        parts = first_line.split()
        if len(parts) < 2:
            return

        path = parts[1].decode()

        if path == "/" or path.startswith("/index"):
            cl.send(HTML_HEADER)
            cl.send(INDEX_HTML)

        elif path.startswith("/data"):
            cl.send(JSON_HEADER)
            cl.send(json.dumps(get_latest_readings()))

        else:
            cl.send("HTTP/1.1 404 Not Found\r\n\r\n404")
    finally:
        cl.close()


# ---- Loop principal ----
while True:
    # 1) Mantener WiFi vivo
    wlan = ensure_connected(wlan, verbose=False)

    # 2) Actualizar sensor (cada 20 s, con warm-up y tolerancia a errores)
    update_sensor()

    # 3) Atender clientes HTTP
    try:
        cl, addr = s.accept()
        print("Cliente:", addr)
        handle_client(cl)
    except OSError:
        # timeout del socket (normal), simplemente seguimos el loop
        pass
