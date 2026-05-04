"""
Servicio para enviar datos del sensor SCD41 al backend API.
Corre en el Raspberry Pi Pico W con MicroPython.

El backend traduce estas peticiones JSON a QuestDB.
"""

import ujson as json
import urequests

import cloud_buffer
import device_config
import timer_service
from sensor_scd41 import get_latest_readings

DEVICE_REGISTER_PATH = "/api/iot/devices/register"
DEPLOYMENT_PATH = "/api/iot/deployments"
TELEMETRY_PATH = "/api/iot/telemetry"
DEPLOYMENT_EXISTS_PATH_TEMPLATE = "/api/iot/deployments/{deployment_id}/exists"

TABLE_DEVICES = "devices"
TABLE_DEPLOYMENTS = "deployments"
TABLE_TELEMETRY = "telemetria_datos"

SEND_INTERVAL = 1200

_last_send = 0
_send_count = 0
_error_count = 0
_enabled = True
_api_base_url = None


def _get_api_base_url():
    global _api_base_url

    if _api_base_url:
        return _api_base_url

    _api_base_url = device_config.get_api_base_url().rstrip("/")
    return _api_base_url


def _decode_json_response(response):
    try:
        text = response.text
    except Exception:
        return None

    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        return None


def _request_json(method, path, payload=None):
    """
    Ejecuta una peticion JSON al backend API.

    Returns:
        (status_code, payload_json)
    """
    global _error_count

    try:
        headers = {"Content-Type": "application/json"}
        if method == "GET":
            response = urequests.get(_get_api_base_url() + path, headers=headers)
        else:
            response = urequests.post(
                _get_api_base_url() + path,
                data=json.dumps(payload),
                headers=headers,
            )

        status_code = response.status_code
        response_payload = _decode_json_response(response)
        response.close()
        return status_code, response_payload

    except OSError as e:
        _error_count += 1
        print(f"Backend API: Error de red ({e})")
        return None, None
    except Exception as e:
        _error_count += 1
        print(f"Backend API: Error inesperado ({e})")
        return None, None


def _post_json(path, payload):
    global _error_count

    status_code, response_payload = _request_json("POST", path, payload)

    if status_code in [200, 204]:
        return True, response_payload

    if status_code is not None:
        _error_count += 1
        print(f"Backend API: Error {status_code}")
        if response_payload is not None:
            print(f"  Respuesta: {response_payload}")

    return False, response_payload


def _build_current_sample():
    deployment_id = device_config.get_deployment_id()
    if not deployment_id:
        print("Backend API: No hay deployment_id, no se puede procesar telemetria")
        return None

    data = get_latest_readings()
    if not data:
        print("Backend API: No hay datos para procesar")
        return None

    return {
        "deployment_id": deployment_id,
        "co2": float(data.get("co2", 0)),
        "temp": float(data.get("temp", 0.0)),
        "rh": float(data.get("rh", 0.0)),
        "errors": int(data.get("errors", 0)),
        "timestamp": str(timer_service.get_timestamp_ns()),
    }


def _buffer_sample(sample):
    summary = cloud_buffer.append_sample(sample)
    print(
        "Backend API: subida a nube deshabilitada. "
        "Muestra guardada localmente (pendientes: {}).".format(summary.get("pending_sample_count", 0))
    )
    return summary


def _deployment_exists(deployment_id):
    path = DEPLOYMENT_EXISTS_PATH_TEMPLATE.format(deployment_id=deployment_id)
    status_code, payload = _request_json("GET", path)
    if status_code is None:
        return None
    if status_code != 200 or not payload:
        return False
    return bool(payload.get("exists"))


def _reconcile_active_deployment():
    deployment_id = device_config.get_deployment_id()
    if not deployment_id:
        return ensure_deployment()

    latitude, longitude = device_config.get_location()
    location_name = device_config.get_location_name()

    print(f"Backend API: Reconciliando deployment {deployment_id}...")
    payload = {
        "deploymentId": deployment_id,
        "boardId": device_config.get_board_id(),
        "latitude": latitude,
        "longitude": longitude,
        "locationName": location_name or "",
        "timestamp": str(timer_service.get_timestamp_ns()),
    }

    success, _ = _post_json(DEPLOYMENT_PATH, payload)
    if success:
        device_config.activate_deployment(deployment_id, latitude, longitude, location_name or "")
        print(f"Backend API: Deployment reconciliado: {deployment_id}")
        return deployment_id

    print(f"Backend API: No se pudo reconciliar {deployment_id}")
    return None


def register_device():
    """
    Registra el device en el backend si no esta registrado.
    Solo se ejecuta una vez por dispositivo.
    """
    if device_config.is_device_registered():
        print("Device ya registrado en backend")
        return True

    board_id = device_config.get_board_id()
    sensor_type = device_config.get_sensor_type()
    payload = {
        "boardId": board_id,
        "sensorType": sensor_type,
        "timestamp": str(timer_service.get_timestamp_ns()),
    }

    print(f"Registrando device en backend: {board_id}")

    success, _ = _post_json(DEVICE_REGISTER_PATH, payload)
    if success:
        device_config.set_device_registered(True)
        print(f"Device {board_id} registrado exitosamente")
        return True

    print(f"Error registrando device {board_id}")
    return False


def create_deployment(latitude, longitude, location_name=""):
    """
    Crea un nuevo deployment via backend API y actualiza la configuracion local.
    """
    deployment_id = device_config.peek_next_deployment_id()
    board_id = device_config.get_board_id()
    payload = {
        "deploymentId": deployment_id,
        "boardId": board_id,
        "latitude": latitude,
        "longitude": longitude,
        "locationName": location_name or "",
        "timestamp": str(timer_service.get_timestamp_ns()),
    }

    print(f"Creando deployment via backend: {deployment_id}")
    print(f"  Ubicacion: ({latitude}, {longitude}) - {location_name or '(sin nombre)'}")

    success, _ = _post_json(DEPLOYMENT_PATH, payload)
    if success:
        device_config.activate_deployment(deployment_id, latitude, longitude, location_name or "")
        print(f"Deployment {deployment_id} creado exitosamente")
        return deployment_id

    print(f"Error creando deployment {deployment_id}")
    return None


def ensure_deployment():
    """
    Asegura que exista un deployment valido.
    """
    deployment_id = device_config.get_deployment_id()

    if deployment_id:
        exists = _deployment_exists(deployment_id)
        if exists is True:
            print(f"Deployment activo: {deployment_id}")
            return deployment_id
        if exists is None:
            print(f"Backend API: No se pudo verificar {deployment_id}, se conserva el deployment local.")
            return deployment_id

        print(f"Backend API: Deployment local {deployment_id} no existe en backend, recreando...")
        return _reconcile_active_deployment()

    latitude, longitude = device_config.get_location()
    location_name = device_config.get_location_name()

    print("No hay deployment activo, creando uno inicial...")
    return create_deployment(latitude, longitude, location_name)


def enviar_telemetria():
    """
    Envia los datos actuales del sensor al backend API.
    """
    global _send_count

    sample = _build_current_sample()
    if not sample:
        return False

    if not device_config.is_cloud_upload_enabled():
        _buffer_sample(sample)
        return True

    deployment_id = sample["deployment_id"]
    co2 = sample["co2"]
    temp = sample["temp"]
    rh = sample["rh"]
    errors = sample["errors"]

    payload = {
        "deploymentId": deployment_id,
        "co2": co2,
        "temp": temp,
        "rh": rh,
        "errors": errors,
        "timestamp": sample["timestamp"],
    }

    success, response_payload = _post_json(TELEMETRY_PATH, payload)
    if success:
        _send_count += 1
        print(f"Backend API: Telemetria enviada #{_send_count}")
        print(
            f"  Deployment: {deployment_id} | CO2={co2:.0f}ppm, "
            f"T={temp:.1f}C, RH={rh:.1f}%"
        )
        return True

    if response_payload and response_payload.get("code") == "deployment_not_registered":
        print(f"Backend API: Deployment no registrado ({deployment_id}), intentando reconciliar...")
        if _reconcile_active_deployment():
            retry_success, _ = _post_json(TELEMETRY_PATH, payload)
            if retry_success:
                _send_count += 1
                print(f"Backend API: Telemetria enviada tras reconciliacion #{_send_count}")
                return True

    print("Backend API: Error enviando telemetria")
    return False


def enviar_a_questdb():
    """
    Funcion de compatibilidad - llama a enviar_telemetria().
    """
    return enviar_telemetria()


def update_service():
    """
    Actualiza el servicio. Llamar en el loop principal.
    Envia datos al backend cada SEND_INTERVAL segundos.
    """
    global _last_send

    if not _enabled:
        return

    now = timer_service.get_current_epoch_utc()
    if now - _last_send < SEND_INTERVAL:
        return

    _last_send = now
    enviar_telemetria()


def enable_service():
    global _enabled
    _enabled = True
    print("Backend API: Servicio activado")


def disable_service():
    global _enabled
    _enabled = False
    print("Backend API: Servicio desactivado")


def get_service_stats():
    return {
        "enabled": _enabled,
        "send_count": _send_count,
        "error_count": _error_count,
        "last_send": _last_send,
        "cloud_upload_enabled": device_config.is_cloud_upload_enabled(),
    }


def set_send_interval(seconds):
    global SEND_INTERVAL
    SEND_INTERVAL = seconds
    print(f"Backend API: Intervalo cambiado a {seconds}s")


def get_send_interval():
    return SEND_INTERVAL


def get_board_id():
    return device_config.get_board_id()


def get_table_name():
    return TABLE_TELEMETRY
