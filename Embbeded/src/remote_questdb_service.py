"""
Servicio para enviar datos del sensor SCD41 a QuestDB
Corre en el Raspberry Pi Pico W con MicroPython
Lee datos localmente y los envía a QuestDB cada 20 minutos

Nueva tabla: frontera_dtlabs_v2
Schema mejorado con board_id, geolocalización y timestamps duales
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

# Nueva tabla con schema mejorado
TABLE_NAME = "frontera_dtlabs_v2"

# Intervalo de envío (segundos)
SEND_INTERVAL = 1200  # 20 minutos

# Estado del servicio
_last_send = 0
_send_count = 0
_error_count = 0
_enabled = True

# ==================== FUNCIONES ====================


def enviar_a_questdb():
    """
    Envía los datos actuales del sensor a QuestDB usando Influx Line Protocol.

    Nuevo schema: frontera_dtlabs_v2
    - sense_time: timestamp del sensor (designated timestamp)
    - board_id: MAC address único del dispositivo
    - sensor_type: tipo de sensor (SCD41)
    - co2, temp, rh: métricas del sensor
    - latitude, longitude: ubicación del dispositivo
    - errors: contador de errores

    Retorna True si tuvo éxito, False si hubo error.
    """
    global _send_count, _error_count

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

    # Obtener configuración del dispositivo
    board_id = device_config.get_board_id()
    sensor_type = device_config.get_sensor_type()
    latitude, longitude = device_config.get_location()

    # Timestamp del sensor (sense_time) - UTC sincronizado con NTP
    sense_time_ns = timer_service.get_timestamp_ns()

    # Construir línea ILP (Influx Line Protocol) con nuevo schema
    # Formato: table,tag1=val1,tag2=val2 field1=val1,field2=val2 timestamp
    #
    # Tags (SYMBOL): board_id, sensor_type
    # Fields (métricas): co2, temp, rh, latitude, longitude, errors
    # Timestamp: sense_time (designated timestamp)
    ilp_line = (
        f"{TABLE_NAME},board_id={board_id},sensor_type={sensor_type} "
        f"co2={co2},temp={temp},rh={rh},"
        f"latitude={latitude},longitude={longitude},"
        f"errors={errors}i "
        f"{sense_time_ns}"
    )

    try:
        # Enviar a QuestDB
        response = urequests.post(
            QUESTDB_WRITE_URL,
            data=ilp_line,
            headers={"Content-Type": "text/plain"}
        )

        # QuestDB responde 200 o 204 en éxito
        if response.status_code in [200, 204]:
            _send_count += 1
            print(f"✓ QuestDB: Enviado #{_send_count}")
            print(f"  Board: {board_id} | CO2={co2:.0f}ppm, T={temp:.1f}°C, RH={rh:.1f}%")
            print(f"  Ubicación: ({latitude:.6f}, {longitude:.6f})")
            response.close()
            return True
        else:
            _error_count += 1
            print(f"✗ QuestDB: Error {response.status_code}")
            print(f"  Respuesta: {response.text[:100]}")
            response.close()
            return False

    except OSError as e:
        # Errores de red (timeout, conexión, DNS, etc.)
        _error_count += 1
        print(f"✗ QuestDB: Error de red ({e})")
        return False
    except Exception as e:
        # Cualquier otro error
        _error_count += 1
        print(f"✗ QuestDB: Error inesperado ({e})")
        return False


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

    # Enviar datos
    enviar_a_questdb()


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
    """Retorna el nombre de la tabla en QuestDB"""
    return TABLE_NAME
