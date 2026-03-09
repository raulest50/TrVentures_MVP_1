import socket
import time
import ujson as json

from wifi import connect_wifi, ensure_connected, get_wifi_info
from sensor_scd41 import init_sensor, update_sensor, get_latest_readings, set_sample_interval
from remote_questdb_service import update_service as update_questdb

# ---- Cargar index.html solamente una vez al inicio ----
with open("index.html", "rb") as f:
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

def _to_bytes(data):
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    return str(data).encode("utf-8")


def _send_bytes(cl, payload):
    payload = _to_bytes(payload)
    if not payload:
        return

    try:
        cl.sendall(payload)
        return
    except AttributeError:
        pass
    except Exception:
        # Algunas builds no implementan sendall() correctamente.
        pass

    sent = 0
    total = len(payload)
    while sent < total:
        chunk = payload[sent:sent + 512]
        written = cl.send(chunk)
        if written is None:
            written = len(chunk)
        if written <= 0:
            raise OSError("socket send failed")
        sent += written


def send_response(cl, status_line, body=b"", content_type="text/plain; charset=utf-8"):
    body_bytes = _to_bytes(body)
    header = (
        status_line + "\r\n"
        + "Content-Type: " + content_type + "\r\n"
        + "Content-Length: " + str(len(body_bytes)) + "\r\n"
        + "Connection: close\r\n\r\n"
    )
    _send_bytes(cl, header)
    _send_bytes(cl, body_bytes)


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
            send_response(cl, "HTTP/1.1 200 OK", INDEX_HTML, "text/html; charset=utf-8")

        elif path.startswith("/data"):
            send_response(
                cl,
                "HTTP/1.1 200 OK",
                json.dumps(get_latest_readings()),
                "application/json",
            )

        elif path.startswith("/wifi"):
            # Devolver información WiFi actual
            send_response(
                cl,
                "HTTP/1.1 200 OK",
                json.dumps(get_wifi_info(wlan)),
                "application/json",
            )

        elif path.startswith("/config"):
            if method == "GET":
                # Devolver configuración actual
                send_response(
                    cl,
                    "HTTP/1.1 200 OK",
                    json.dumps(get_latest_readings()),
                    "application/json",
                )
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
                                send_response(
                                    cl,
                                    "HTTP/1.1 200 OK",
                                    json.dumps({"status": "ok", "sample_interval": new_interval}),
                                    "application/json",
                                )
                            else:
                                send_response(
                                    cl,
                                    "HTTP/1.1 400 Bad Request",
                                    json.dumps({"error": "interval must be positive"}),
                                    "application/json",
                                )
                        else:
                            send_response(
                                cl,
                                "HTTP/1.1 400 Bad Request",
                                json.dumps({"error": "missing sample_interval"}),
                                "application/json",
                            )
                    else:
                        send_response(
                            cl,
                            "HTTP/1.1 400 Bad Request",
                            json.dumps({"error": "missing request body"}),
                            "application/json",
                        )
                except Exception as e:
                    send_response(
                        cl,
                        "HTTP/1.1 500 Internal Server Error",
                        json.dumps({"error": str(e)}),
                        "application/json",
                    )
            else:
                send_response(
                    cl,
                    "HTTP/1.1 405 Method Not Allowed",
                    json.dumps({"error": "method not allowed"}),
                    "application/json",
                )

        else:
            send_response(cl, "HTTP/1.1 404 Not Found", "404")
    finally:
        cl.close()


# ---- Loop principal ----
while True:
    # 1) Mantener WiFi vivo
    wlan = ensure_connected(wlan, verbose=False)

    # 2) Actualizar sensor (cada 20 s, con warm-up y tolerancia a errores)
    update_sensor()

    # 3) Enviar datos a QuestDB (cada 20 s)
    update_questdb()

    # 4) Atender clientes HTTP
    try:
        cl, addr = s.accept()
        print("Cliente:", addr)
        handle_client(cl)
    except OSError:
        # timeout del socket (normal), simplemente seguimos el loop
        pass
