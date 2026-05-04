import socket
import time
import ujson as json

from wifi import (
    add_or_update_network,
    connect_to_known_network,
    connect_wifi,
    delete_network,
    ensure_connected,
    get_active_ip,
    get_nearby_networks,
    get_setup_ap_credentials,
    get_wifi_config_summary,
    get_wifi_info,
    get_wifi_mode,
    reset_wifi_config,
    update_setup_ap_password,
)
from sensor_scd41 import init_sensor, update_sensor, get_latest_readings, set_sample_interval
from remote_questdb_service import update_service as update_questdb
import timer_service
import device_config


try:
    with open("index.html", "rb") as html_file:
        INDEX_HTML = html_file.read()
    print("index.html cargado correctamente")
except Exception as e:
    print("ERROR cargando index.html: {}".format(e))
    INDEX_HTML = b"<html><body><h1>Error: index.html no encontrado</h1></body></html>"


def _to_bytes(data):
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    return str(data).encode("utf-8")


def _json_response(payload):
    return json.dumps(payload)


def _read_request(cl):
    request = b""

    while b"\r\n\r\n" not in request:
        chunk = cl.recv(512)
        if not chunk:
            break
        request += chunk
        if len(request) > 4096:
            break

    header_end = request.find(b"\r\n\r\n")
    if header_end == -1:
        return request

    headers_blob = request[:header_end].decode("utf-8", "ignore")
    content_length = 0
    for line in headers_blob.split("\r\n")[1:]:
        lower_line = line.lower()
        if lower_line.startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except Exception:
                content_length = 0
            break

    body = request[header_end + 4:]
    while len(body) < content_length:
        chunk = cl.recv(512)
        if not chunk:
            break
        body += chunk
        request += chunk

    return request


def _parse_request(request):
    first_line = request.split(b"\r\n", 1)[0]
    parts = first_line.split()
    if len(parts) < 2:
        return None, None, {}

    method = parts[0].decode("utf-8", "ignore")
    path = parts[1].decode("utf-8", "ignore")
    body_start = request.find(b"\r\n\r\n")
    body = {}

    if body_start != -1:
        raw_body = request[body_start + 4:]
        if raw_body:
            try:
                body = json.loads(raw_body)
            except Exception:
                body = {}

    return method, path, body


def _url_decode(value):
    value = str(value or "")
    decoded = ""
    idx = 0

    while idx < len(value):
        char = value[idx]
        if char == "+":
            decoded += " "
        elif char == "%" and idx + 2 < len(value):
            try:
                decoded += chr(int(value[idx + 1:idx + 3], 16))
                idx += 2
            except Exception:
                decoded += char
        else:
            decoded += char
        idx += 1

    return decoded


def _send_bytes(cl, payload):
    payload = _to_bytes(payload)
    if not payload:
        return

    try:
        cl.sendall(payload)
        return
    except Exception:
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


def send_json(cl, status_line, payload):
    send_response(cl, status_line, _json_response(payload), "application/json")


def _log_wifi_endpoint():
    mode = get_wifi_mode()
    ip = get_active_ip()

    if mode == "sta" and ip:
        print("\nServidor web iniciado en http://{}".format(ip))
        print("Dashboard local disponible en modo operativo\n")
        return

    if mode == "setup_ap":
        setup_ssid, setup_password = get_setup_ap_credentials()
        print("\nServidor web iniciado en modo setup")
        print("  SSID setup: {}".format(setup_ssid))
        print("  Password setup: {}".format(setup_password))
        print("  URL: http://{}".format(ip or "192.168.4.1"))
        print("  Conecta tu telefono o laptop a la red del nodo para configurarlo\n")
        return

    print("\nServidor web iniciado sin enlace WiFi activo")
    print("La IP se mostrara cuando el nodo conecte por STA o active su AP de setup\n")


print("Iniciando conectividad WiFi...")
wlan = connect_wifi(do_scan=True, verbose=True)
wifi_available = bool(wlan and wlan.isconnected())

if not wifi_available:
    print("\nAdvertencia: el nodo arranco sin WiFi operativo")
    if get_wifi_mode() == "setup_ap":
        print("Se activo el modo setup automaticamente.")
    else:
        print("El servidor local seguira disponible para soporte cuando haya IP.")


if wifi_available:
    print("\nSincronizando hora con NTP...")
    try:
        if timer_service.sync_ntp(force=True):
            print("Hora sincronizada correctamente")
            timer_service.set_utc_offset(hours=-6)
            print("UTC: {}".format(timer_service.format_iso8601_utc()))
            print("Local: {}".format(timer_service.format_iso8601_local()))
        else:
            print("No se pudo sincronizar NTP, se conserva la hora local actual.")
    except Exception as e:
        print("Error durante sincronizacion NTP: {}".format(e))
        timer_service.set_utc_offset(hours=-6)
else:
    print("\nSaltando sincronizacion NTP (sin WiFi STA)")
    timer_service.set_utc_offset(hours=-6)


print("\nCargando configuracion del dispositivo...")
device_config.print_config()


if wifi_available:
    print("\nInicializando registro en backend...")
    try:
        from remote_questdb_service import register_device, ensure_deployment

        register_device()
        deployment_id = ensure_deployment()
        print("Deployment activo: {}".format(deployment_id))
    except Exception as e:
        print("Error durante registro en backend: {}".format(e))
        print("El dispositivo seguira funcionando en modo local.")
else:
    print("\nSaltando registro en backend (sin WiFi STA)")


sample_interval = device_config.get_sample_interval()
questdb_interval = device_config.get_questdb_interval()
print("\nAplicando intervalos configurados:")
print("  Muestreo del sensor: {}s".format(sample_interval))
print("  Envio al backend: {}s".format(questdb_interval))

set_sample_interval(sample_interval)
from remote_questdb_service import set_send_interval
set_send_interval(questdb_interval)


init_sensor()


addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
s = socket.socket()
try:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
except Exception:
    pass
s.bind(addr)
s.listen(2)
s.settimeout(0.3)

_log_wifi_endpoint()


def _refresh_wifi_state():
    global wlan, wifi_available
    wifi_available = bool(wlan and wlan.isconnected())
    return get_wifi_info(wlan)


def handle_client(cl):
    global wlan, wifi_available

    try:
        request = _read_request(cl)
        if not request:
            return

        method, path, body = _parse_request(request)
        if not method or not path:
            send_response(cl, "HTTP/1.1 400 Bad Request", "Solicitud invalida")
            return

        if path == "/" or path.startswith("/index"):
            send_response(cl, "HTTP/1.1 200 OK", INDEX_HTML, "text/html; charset=utf-8")
            return

        if path.startswith("/data"):
            send_json(cl, "HTTP/1.1 200 OK", get_latest_readings())
            return

        if path.startswith("/wifi/scan"):
            send_json(cl, "HTTP/1.1 200 OK", get_nearby_networks(wlan, limit=8))
            return

        if path.startswith("/wifi/config/"):
            if method != "DELETE":
                send_json(cl, "HTTP/1.1 405 Method Not Allowed", {"error": "method not allowed"})
                return

            ssid = _url_decode(path[len("/wifi/config/"):])
            if not ssid:
                send_json(cl, "HTTP/1.1 400 Bad Request", {"error": "ssid missing"})
                return

            summary = delete_network(ssid)
            send_json(
                cl,
                "HTTP/1.1 200 OK",
                {"status": "ok", "deleted_ssid": ssid, "wifi": summary},
            )
            return

        if path.startswith("/wifi/config"):
            if method == "GET":
                send_json(cl, "HTTP/1.1 200 OK", get_wifi_config_summary())
                return

            if method != "POST":
                send_json(cl, "HTTP/1.1 405 Method Not Allowed", {"error": "method not allowed"})
                return

            ssid = str(body.get("ssid", "")).strip()
            password = body.get("password")
            priority = int(body.get("priority", 10))
            enabled = bool(body.get("enabled", True))

            try:
                summary = add_or_update_network(ssid, password, priority, enabled)
                send_json(cl, "HTTP/1.1 200 OK", {"status": "ok", "wifi": summary})
            except ValueError as e:
                send_json(cl, "HTTP/1.1 400 Bad Request", {"error": str(e)})
            except Exception as e:
                send_json(cl, "HTTP/1.1 500 Internal Server Error", {"error": str(e)})
            return

        if path.startswith("/wifi/connect"):
            if method != "POST":
                send_json(cl, "HTTP/1.1 405 Method Not Allowed", {"error": "method not allowed"})
                return

            ssid = body.get("ssid")
            try:
                wlan = connect_to_known_network(ssid=ssid, verbose=True)
                info = _refresh_wifi_state()
                send_json(cl, "HTTP/1.1 200 OK", {"status": "ok", "wifi": info})
            except Exception as e:
                send_json(cl, "HTTP/1.1 500 Internal Server Error", {"error": str(e)})
            return

        if path.startswith("/wifi/reset"):
            if method != "POST":
                send_json(cl, "HTTP/1.1 405 Method Not Allowed", {"error": "method not allowed"})
                return

            try:
                summary = reset_wifi_config()
                wlan = connect_wifi(do_scan=False, verbose=False)
                info = _refresh_wifi_state()
                send_json(
                    cl,
                    "HTTP/1.1 200 OK",
                    {"status": "ok", "wifi": summary, "current": info},
                )
            except Exception as e:
                send_json(cl, "HTTP/1.1 500 Internal Server Error", {"error": str(e)})
            return

        if path.startswith("/wifi/setup-ap/password"):
            if method != "POST":
                send_json(cl, "HTTP/1.1 405 Method Not Allowed", {"error": "method not allowed"})
                return

            password = body.get("password", "")
            try:
                summary = update_setup_ap_password(password)
                send_json(cl, "HTTP/1.1 200 OK", {"status": "ok", "wifi": summary})
            except ValueError as e:
                send_json(cl, "HTTP/1.1 400 Bad Request", {"error": str(e)})
            except Exception as e:
                send_json(cl, "HTTP/1.1 500 Internal Server Error", {"error": str(e)})
            return

        if path.startswith("/wifi"):
            send_json(cl, "HTTP/1.1 200 OK", get_wifi_info(wlan))
            return

        if path.startswith("/questdb"):
            from remote_questdb_service import get_service_stats, get_send_interval, get_board_id, get_table_name

            stats = get_service_stats()
            stats["send_interval"] = get_send_interval()
            stats["board_id"] = get_board_id()
            stats["table_name"] = get_table_name()
            send_json(cl, "HTTP/1.1 200 OK", stats)
            return

        if path.startswith("/time"):
            send_json(cl, "HTTP/1.1 200 OK", timer_service.get_status())
            return

        if path.startswith("/logger"):
            import logger
            send_json(cl, "HTTP/1.1 200 OK", {"errors": logger.get_logs(level_filter="ERROR")})
            return

        if path.startswith("/device/config"):
            if method == "GET":
                send_json(cl, "HTTP/1.1 200 OK", device_config.get_config_dict())
                return

            if method != "POST":
                send_json(cl, "HTTP/1.1 405 Method Not Allowed", {"error": "method not allowed"})
                return

            try:
                if "latitude" not in body or "longitude" not in body:
                    send_json(cl, "HTTP/1.1 400 Bad Request", {"error": "missing latitude or longitude"})
                    return

                lat = float(body["latitude"])
                lon = float(body["longitude"])
                location_name = body.get("location_name", "")

                from remote_questdb_service import create_deployment
                new_deployment_id = create_deployment(lat, lon, location_name)

                if not new_deployment_id:
                    send_json(cl, "HTTP/1.1 500 Internal Server Error", {"error": "failed to create deployment"})
                    return

                response_data = {
                    "status": "ok",
                    "deployment_id": new_deployment_id,
                    "latitude": lat,
                    "longitude": lon,
                    "location_name": location_name,
                }
                print("Nuevo deployment creado: {}".format(new_deployment_id))
                send_json(cl, "HTTP/1.1 200 OK", response_data)
            except Exception as e:
                send_json(cl, "HTTP/1.1 500 Internal Server Error", {"error": str(e)})
            return

        if path.startswith("/config"):
            if method == "GET":
                config_data = {
                    "sample_interval": device_config.get_sample_interval(),
                    "questdb_interval": device_config.get_questdb_interval(),
                }
                send_json(cl, "HTTP/1.1 200 OK", config_data)
                return

            if method != "POST":
                send_json(cl, "HTTP/1.1 405 Method Not Allowed", {"error": "method not allowed"})
                return

            try:
                response_data = {"status": "ok"}

                if "sample_interval" in body:
                    new_sample_interval = int(body["sample_interval"])
                    if new_sample_interval <= 0:
                        send_json(cl, "HTTP/1.1 400 Bad Request", {"error": "sample_interval must be positive"})
                        return
                    set_sample_interval(new_sample_interval)
                    response_data["sample_interval"] = new_sample_interval

                if "questdb_interval" in body:
                    new_questdb_interval = int(body["questdb_interval"])
                    if new_questdb_interval <= 0:
                        send_json(cl, "HTTP/1.1 400 Bad Request", {"error": "questdb_interval must be positive"})
                        return
                    set_send_interval(new_questdb_interval)
                    response_data["questdb_interval"] = new_questdb_interval

                if len(response_data) == 1:
                    send_json(
                        cl,
                        "HTTP/1.1 400 Bad Request",
                        {"error": "missing sample_interval or questdb_interval"},
                    )
                    return

                sample = response_data.get("sample_interval", device_config.get_sample_interval())
                questdb_interval = response_data.get("questdb_interval", device_config.get_questdb_interval())
                device_config.set_intervals(sample, questdb_interval)
                send_json(cl, "HTTP/1.1 200 OK", response_data)
            except Exception as e:
                send_json(cl, "HTTP/1.1 500 Internal Server Error", {"error": str(e)})
            return

        send_response(cl, "HTTP/1.1 404 Not Found", "404")

    finally:
        try:
            cl.close()
        except Exception:
            pass


print("=" * 60)
print("LOOP PRINCIPAL INICIADO")
print("=" * 60 + "\n")

_wifi_reconnect_logs = 0
_max_reconnect_log = 3

while True:
    try:
        previously_available = wifi_available
        previous_mode = get_wifi_mode()
        wlan = ensure_connected(wlan, verbose=False)
        current_info = _refresh_wifi_state()

        if wifi_available and not previously_available:
            _wifi_reconnect_logs += 1
            if _wifi_reconnect_logs <= _max_reconnect_log:
                print("\nWiFi reconectado en modo STA: http://{}\n".format(current_info.get("ip", "--")))

        if current_info.get("mode") == "setup_ap" and previous_mode != "setup_ap":
            print("\nFallback a modo setup activo: http://{}\n".format(current_info.get("ip") or "192.168.4.1"))

    except Exception as e:
        if _wifi_reconnect_logs <= _max_reconnect_log:
            print("Error manteniendo WiFi: {}".format(e))
        wifi_available = False

    try:
        update_sensor()
    except Exception as e:
        print("Error actualizando sensor: {}".format(e))

    if wifi_available:
        try:
            update_questdb()
        except Exception as e:
            print("Error enviando al backend: {}".format(e))

    try:
        cl, client_addr = s.accept()
        print("Cliente: {}".format(client_addr))
        handle_client(cl)
    except OSError:
        pass
    except Exception as e:
        print("Error manejando cliente HTTP: {}".format(e))
