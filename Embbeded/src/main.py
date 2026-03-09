import socket
import time
import ujson as json

from wifi import connect_wifi, ensure_connected, get_wifi_info
from sensor_scd41 import init_sensor, update_sensor, get_latest_readings, set_sample_interval

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

        method = parts[0].decode()
        path = parts[1].decode()

        if path == "/" or path.startswith("/index"):
            cl.send(HTML_HEADER)
            cl.send(INDEX_HTML)

        elif path.startswith("/data"):
            cl.send(JSON_HEADER)
            cl.send(json.dumps(get_latest_readings()))

        elif path.startswith("/wifi"):
            # Devolver información WiFi actual
            cl.send(JSON_HEADER)
            cl.send(json.dumps(get_wifi_info(wlan)))

        elif path.startswith("/config"):
            if method == "GET":
                # Devolver configuración actual
                cl.send(JSON_HEADER)
                cl.send(json.dumps(get_latest_readings()))
            elif method == "POST":
                # Cambiar intervalo de muestreo
                try:
                    # Buscar el body del request
                    body_start = request.find(b"\r\n\r\n")
                    if body_start != -1:
                        body = request[body_start + 4:]
                        data = json.loads(body)

                        if "sample_interval" in data:
                            new_interval = int(data["sample_interval"])
                            if new_interval > 0:
                                set_sample_interval(new_interval)
                                cl.send(JSON_HEADER)
                                cl.send(json.dumps({"status": "ok", "sample_interval": new_interval}))
                            else:
                                cl.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                                cl.send(json.dumps({"error": "interval must be positive"}))
                        else:
                            cl.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                            cl.send(json.dumps({"error": "missing sample_interval"}))
                    else:
                        cl.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                except Exception as e:
                    cl.send("HTTP/1.1 500 Internal Server Error\r\n\r\n")
                    cl.send(json.dumps({"error": str(e)}))
            else:
                cl.send("HTTP/1.1 405 Method Not Allowed\r\n\r\n")

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
