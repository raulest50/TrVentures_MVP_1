import socket
import time
import ujson as json

from wifi import connect_wifi, ensure_connected, get_wifi_info
from sensor_scd41 import init_sensor, update_sensor, get_latest_readings, set_sample_interval
from remote_questdb_service import update_service as update_questdb
import timer_service
import device_config

# ---- Cargar index.html solamente una vez al inicio ----
with open("index.html", "rb") as f:
    INDEX_HTML = f.read()

# ---- Conexión WiFi ----
wlan = connect_wifi(do_scan=True, verbose=True)

if not wlan or not wlan.isconnected():
    print("\n❌ No hay WiFi, el servidor HTTP no se iniciará.")
    while True:
        time.sleep(5)

# ---- Sincronizar tiempo con NTP ----
print("\n🕐 Sincronizando hora con NTP...")
if timer_service.sync_ntp(force=True):
    print("✓ Hora sincronizada correctamente")
    print(f"  UTC: {timer_service.format_iso8601_utc()}")
    # Configurar offset para zona horaria local (ajustar según tu ubicación)
    # Ejemplo: México (UTC-6): timer_service.set_utc_offset(hours=-6)
    timer_service.set_utc_offset(hours=-6)  # Ajustar según tu zona horaria
    print(f"  Local: {timer_service.format_iso8601_local()}")
else:
    print("⚠️ No se pudo sincronizar con NTP, continuando con hora del sistema")

# ---- Cargar configuración del dispositivo ----
print("\n📍 Cargando configuración del dispositivo...")
device_config.print_config()

# ---- Registrar device y asegurar deployment en QuestDB ----
print("\n📡 Inicializando registro en QuestDB...")
from remote_questdb_service import register_device, ensure_deployment

# Registrar device si no está registrado
register_device()

# Asegurar que existe un deployment válido
deployment_id = ensure_deployment()
print(f"✓ Deployment activo: {deployment_id}")

# ---- Cargar y aplicar intervalos de muestreo desde configuración ----
sample_interval = device_config.get_sample_interval()
questdb_interval = device_config.get_questdb_interval()

print(f"\n⏱ Aplicando intervalos configurados:")
print(f"  • Muestreo del sensor: {sample_interval}s ({sample_interval // 60} min)")
print(f"  • Envío a QuestDB: {questdb_interval}s ({questdb_interval // 60} min)")

# Aplicar intervalos
set_sample_interval(sample_interval)
from remote_questdb_service import set_send_interval
set_send_interval(questdb_interval)

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

        elif path.startswith("/wifi/scan"):
            # Devolver lista de redes WiFi detectadas
            from wifi import get_nearby_networks
            scan_result = get_nearby_networks(wlan, limit=5)
            send_response(
                cl,
                "HTTP/1.1 200 OK",
                json.dumps(scan_result),
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

        elif path.startswith("/questdb"):
            # Devolver estadísticas de QuestDB
            from remote_questdb_service import get_service_stats, get_send_interval, get_board_id, get_table_name
            stats = get_service_stats()
            stats["send_interval"] = get_send_interval()
            stats["board_id"] = get_board_id()
            stats["table_name"] = get_table_name()
            send_response(
                cl,
                "HTTP/1.1 200 OK",
                json.dumps(stats),
                "application/json",
            )

        elif path.startswith("/time"):
            # Devolver información de sincronización de tiempo
            time_info = timer_service.get_status()
            send_response(
                cl,
                "HTTP/1.1 200 OK",
                json.dumps(time_info),
                "application/json",
            )

        elif path.startswith("/device/config"):
            # Endpoint para configuración del dispositivo
            if method == "GET":
                # Devolver configuración actual del dispositivo
                config = device_config.get_config_dict()
                send_response(
                    cl,
                    "HTTP/1.1 200 OK",
                    json.dumps(config),
                    "application/json",
                )
            elif method == "POST":
                # Crear nuevo deployment con la ubicación proporcionada
                try:
                    # Buscar el body del request
                    body_start = request.find(b"\r\n\r\n")
                    if body_start != -1:
                        body = request[body_start + 4:]
                        data = json.loads(body)

                        # Validar que se proporcionaron latitud y longitud
                        if "latitude" not in data or "longitude" not in data:
                            send_response(
                                cl,
                                "HTTP/1.1 400 Bad Request",
                                json.dumps({"error": "missing latitude or longitude"}),
                                "application/json",
                            )
                            return

                        lat = float(data["latitude"])
                        lon = float(data["longitude"])
                        location_name = data.get("location_name", "")

                        # Crear nuevo deployment en QuestDB
                        from remote_questdb_service import create_deployment
                        new_deployment_id = create_deployment(lat, lon, location_name)

                        if new_deployment_id:
                            response_data = {
                                "status": "ok",
                                "deployment_id": new_deployment_id,
                                "latitude": lat,
                                "longitude": lon
                            }
                            if location_name:
                                response_data["location_name"] = location_name
                            print(f"✓ Nuevo deployment creado: {new_deployment_id}")

                            send_response(
                                cl,
                                "HTTP/1.1 200 OK",
                                json.dumps(response_data),
                                "application/json",
                            )
                        else:
                            send_response(
                                cl,
                                "HTTP/1.1 500 Internal Server Error",
                                json.dumps({"error": "failed to create deployment"}),
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

        elif path.startswith("/config"):
            if method == "GET":
                # Devolver configuración actual de intervalos
                config_data = {
                    "sample_interval": device_config.get_sample_interval(),
                    "questdb_interval": device_config.get_questdb_interval()
                }
                send_response(
                    cl,
                    "HTTP/1.1 200 OK",
                    json.dumps(config_data),
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

                        response_data = {"status": "ok"}

                        # Procesar sample_interval (intervalo del sensor)
                        if "sample_interval" in data:
                            new_sample_interval = int(data["sample_interval"])
                            if new_sample_interval > 0:
                                set_sample_interval(new_sample_interval)
                                response_data["sample_interval"] = new_sample_interval
                            else:
                                send_response(
                                    cl,
                                    "HTTP/1.1 400 Bad Request",
                                    json.dumps({"error": "sample_interval must be positive"}),
                                    "application/json",
                                )
                                return

                        # Procesar questdb_interval (intervalo de envío a QuestDB)
                        if "questdb_interval" in data:
                            from remote_questdb_service import set_send_interval
                            new_questdb_interval = int(data["questdb_interval"])
                            if new_questdb_interval > 0:
                                set_send_interval(new_questdb_interval)
                                response_data["questdb_interval"] = new_questdb_interval
                            else:
                                send_response(
                                    cl,
                                    "HTTP/1.1 400 Bad Request",
                                    json.dumps({"error": "questdb_interval must be positive"}),
                                    "application/json",
                                )
                                return

                        # Si no se envió ningún parámetro válido
                        if len(response_data) == 1:  # Solo contiene "status"
                            send_response(
                                cl,
                                "HTTP/1.1 400 Bad Request",
                                json.dumps({"error": "missing sample_interval or questdb_interval"}),
                                "application/json",
                            )
                        else:
                            # Guardar intervalos en configuración persistente
                            sample = response_data.get("sample_interval", device_config.get_sample_interval())
                            questdb = response_data.get("questdb_interval", device_config.get_questdb_interval())
                            device_config.set_intervals(sample, questdb)

                            send_response(
                                cl,
                                "HTTP/1.1 200 OK",
                                json.dumps(response_data),
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
