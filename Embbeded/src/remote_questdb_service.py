"""
Servicio para enviar datos del sensor SCD41 a QuestDB
Corre en el Raspberry Pi Pico W con MicroPython

Arquitectura de 3 tablas:
- devices: Registro de dispositivos (board_id, sensor_type)
- deployments: Historial de deployments por ubicación
- telemetry: Datos de telemetría con referencia a deployment
"""

import urequests
import timer_service
from sensor_scd41 import get_latest_readings
import device_config

# ==================== CONFIGURACIÓN ====================

# QuestDB Server (VPS Hostinger)
QUESTDB_HOST = "187.124.90.77"
QUESTDB_PORT = 9000
QUESTDB_WRITE_URL = f"http://{QUESTDB_HOST}:{QUESTDB_PORT}/write"

# Nombres de tablas
TABLE_DEVICES = "devices"
TABLE_DEPLOYMENTS = "deployments"
TABLE_TELEMETRY = "telemetry"

# Intervalo de envío (segundos)
SEND_INTERVAL = 1200  # 20 minutos

# Estado del servicio
_last_send = 0
_send_count = 0
_error_count = 0
_enabled = True

# ==================== FUNCIÓN BASE ILP ====================


def _send_ilp(ilp_line):
    """
    Envía una línea ILP (Influx Line Protocol) a QuestDB.

    Args:
        ilp_line: String con la línea ILP a enviar

    Returns:
        True si tuvo éxito, False si hubo error
    """
    global _error_count

    try:
        response = urequests.post(
            QUESTDB_WRITE_URL,
            data=ilp_line,
            headers={"Content-Type": "text/plain"}
        )

        # QuestDB responde 200 o 204 en éxito
        if response.status_code in [200, 204]:
            response.close()
            return True
        else:
            _error_count += 1
            print(f"✗ QuestDB: Error {response.status_code}")
            print(f"  Respuesta: {response.text[:100]}")
            response.close()
            return False

    except OSError as e:
        _error_count += 1
        print(f"✗ QuestDB: Error de red ({e})")
        return False
    except Exception as e:
        _error_count += 1
        print(f"✗ QuestDB: Error inesperado ({e})")
        return False


# ==================== DEVICES ====================


def register_device():
    """
    Registra el device en la tabla devices si no está registrado.
    Solo se ejecuta una vez por dispositivo.

    Returns:
        True si el registro fue exitoso o ya estaba registrado, False si hubo error
    """
    # Verificar si ya está registrado
    if device_config.is_device_registered():
        print("✓ Device ya registrado en QuestDB")
        return True

    board_id = device_config.get_board_id()
    sensor_type = device_config.get_sensor_type()
    timestamp_ns = timer_service.get_timestamp_ns()

    # Línea ILP para devices
    # devices,board_id=XXX,sensor_type=SCD41 registered=1i timestamp
    ilp_line = (
        f"{TABLE_DEVICES},board_id={board_id},sensor_type={sensor_type} "
        f"registered=1i "
        f"{timestamp_ns}"
    )

    print(f"📝 Registrando device: {board_id}")

    if _send_ilp(ilp_line):
        device_config.set_device_registered(True)
        print(f"✓ Device {board_id} registrado exitosamente")
        return True
    else:
        print(f"✗ Error registrando device {board_id}")
        return False


# ==================== DEPLOYMENTS ====================


def create_deployment(latitude, longitude, location_name=""):
    """
    Crea un nuevo deployment en QuestDB y actualiza la configuración local.

    Args:
        latitude: Latitud en grados decimales
        longitude: Longitud en grados decimales
        location_name: Nombre descriptivo opcional del lugar

    Returns:
        String con el deployment_id creado, o None si hubo error
    """
    # Generar nuevo deployment_id y guardar en config
    deployment_id = device_config.create_new_deployment(latitude, longitude, location_name)
    board_id = device_config.get_board_id()
    timestamp_ns = timer_service.get_timestamp_ns()

    # Escapar location_name para ILP (reemplazar espacios con \)
    safe_location = location_name.replace(" ", "\\ ").replace(",", "\\,") if location_name else "unknown"

    # Línea ILP para deployments
    # deployments,deployment_id=XXX,board_id=YYY latitude=0.0,longitude=0.0,location_name="..." timestamp
    ilp_line = (
        f"{TABLE_DEPLOYMENTS},deployment_id={deployment_id},board_id={board_id} "
        f"latitude={latitude},longitude={longitude},location_name=\"{location_name or 'unknown'}\" "
        f"{timestamp_ns}"
    )

    print(f"📍 Creando deployment: {deployment_id}")
    print(f"   Ubicación: ({latitude}, {longitude}) - {location_name or '(sin nombre)'}")

    if _send_ilp(ilp_line):
        print(f"✓ Deployment {deployment_id} creado exitosamente")
        return deployment_id
    else:
        print(f"✗ Error creando deployment {deployment_id}")
        return None


def ensure_deployment():
    """
    Asegura que exista un deployment válido.
    Si no existe, crea uno con la ubicación actual de la configuración.

    Returns:
        String con el deployment_id actual o recién creado
    """
    deployment_id = device_config.get_deployment_id()

    if deployment_id:
        print(f"✓ Deployment activo: {deployment_id}")
        return deployment_id

    # No hay deployment, crear uno con la ubicación actual
    latitude, longitude = device_config.get_location()
    location_name = device_config.get_location_name()

    print("⚠️ No hay deployment activo, creando uno inicial...")
    return create_deployment(latitude, longitude, location_name)


# ==================== TELEMETRY ====================


def enviar_telemetria():
    """
    Envía los datos actuales del sensor a la tabla telemetry usando ILP.

    Formato: telemetry,deployment_id=XXX co2=...,temp=...,rh=...,errors=... timestamp

    Returns:
        True si tuvo éxito, False si hubo error
    """
    global _send_count

    # Verificar que existe deployment_id
    deployment_id = device_config.get_deployment_id()
    if not deployment_id:
        print("⚠️ QuestDB: No hay deployment_id, no se puede enviar telemetría")
        return False

    # Leer datos del sensor
    data = get_latest_readings()

    if not data:
        print("⚠️ QuestDB: No hay datos para enviar")
        return False

    # Extraer valores del sensor
    co2 = float(data.get('co2', 0))
    temp = float(data.get('temp', 0.0))
    rh = float(data.get('rh', 0.0))
    errors = int(data.get('errors', 0))

    # Timestamp UTC sincronizado con NTP
    timestamp_ns = timer_service.get_timestamp_ns()

    # Construir línea ILP para telemetry
    ilp_line = (
        f"{TABLE_TELEMETRY},deployment_id={deployment_id} "
        f"co2={co2},temp={temp},rh={rh},errors={errors}i "
        f"{timestamp_ns}"
    )

    if _send_ilp(ilp_line):
        _send_count += 1
        print(f"✓ QuestDB: Telemetría enviada #{_send_count}")
        print(f"  Deployment: {deployment_id} | CO2={co2:.0f}ppm, T={temp:.1f}°C, RH={rh:.1f}%")
        return True
    else:
        print(f"✗ QuestDB: Error enviando telemetría")
        return False


# ==================== COMPATIBILIDAD ====================


def enviar_a_questdb():
    """
    Función de compatibilidad - llama a enviar_telemetria().
    Mantener para código existente.
    """
    return enviar_telemetria()


def update_service():
    """
    Actualiza el servicio. Llamar en el loop principal.
    Envía datos a QuestDB cada SEND_INTERVAL segundos.
    """
    global _last_send

    if not _enabled:
        return

    now = timer_service.get_current_epoch_utc()

    # Verificar si es tiempo de enviar
    if now - _last_send < SEND_INTERVAL:
        return

    _last_send = now

    # Enviar telemetría
    enviar_telemetria()


def enable_service():
    """Activa el servicio de envío a QuestDB"""
    global _enabled
    _enabled = True
    print("QuestDB: Servicio activado")


def disable_service():
    """Desactiva el servicio de envío a QuestDB"""
    global _enabled
    _enabled = False
    print("QuestDB: Servicio desactivado")


def get_service_stats():
    """Retorna estadísticas del servicio"""
    return {
        "enabled": _enabled,
        "send_count": _send_count,
        "error_count": _error_count,
        "last_send": _last_send
    }


def set_send_interval(seconds):
    """Cambia el intervalo de envío dinámicamente"""
    global SEND_INTERVAL
    SEND_INTERVAL = seconds
    print(f"QuestDB: Intervalo cambiado a {seconds}s")


def get_send_interval():
    """Retorna el intervalo de envío actual"""
    return SEND_INTERVAL


def get_board_id():
    """Retorna el Board ID (MAC address)"""
    return device_config.get_board_id()


def get_table_name():
    """Retorna el nombre de la tabla principal de telemetría"""
    return TABLE_TELEMETRY
