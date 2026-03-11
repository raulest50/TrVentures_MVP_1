"""
Gestión de configuración persistente del dispositivo IoT.
Maneja: board_id (MAC), latitud, longitud, y otras configuraciones.
"""

import ujson as json
import network

CONFIG_FILE = "device_config.json"

# Configuración por defecto
DEFAULT_CONFIG = {
    "board_id": None,           # Se inicializa con MAC al primer uso
    "latitude": 0.0,            # Configurar desde la UI
    "longitude": 0.0,           # Configurar desde la UI
    "sensor_type": "SCD41",     # Tipo de sensor principal
    "location_name": "",        # Nombre descriptivo opcional
    "sample_interval": 300,     # Intervalo de muestreo del sensor (5 minutos por defecto)
    "questdb_interval": 1200    # Intervalo de envío a QuestDB (20 minutos por defecto)
}

_config_cache = None


def get_mac_address():
    """
    Obtiene la dirección MAC de la interfaz WiFi del Pico W.
    Retorna string en formato: 'AABBCCDDEEFF'
    """
    try:
        wlan = network.WLAN(network.STA_IF)
        mac_bytes = wlan.config('mac')
        # Convertir bytes a string hexadecimal sin separadores
        mac_str = ''.join(['{:02X}'.format(b) for b in mac_bytes])
        return mac_str
    except Exception as e:
        print(f"⚠️ Error obteniendo MAC address: {e}")
        return "UNKNOWN_MAC"


def load_config():
    """
    Carga la configuración desde el archivo JSON.
    Si no existe, crea uno con valores por defecto.
    Retorna diccionario con la configuración.
    """
    global _config_cache

    # Si ya está en cache, retornar
    if _config_cache is not None:
        return _config_cache

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            print(f"✓ Configuración cargada desde {CONFIG_FILE}")
            _config_cache = config
            return config
    except OSError:
        # Archivo no existe, crear uno nuevo
        print(f"⚠️ {CONFIG_FILE} no encontrado, creando con valores por defecto...")
        config = DEFAULT_CONFIG.copy()
        config["board_id"] = get_mac_address()
        save_config(config)
        _config_cache = config
        return config
    except Exception as e:
        print(f"✗ Error cargando configuración: {e}")
        # En caso de error, usar valores por defecto
        config = DEFAULT_CONFIG.copy()
        config["board_id"] = get_mac_address()
        _config_cache = config
        return config


def save_config(config):
    """
    Guarda la configuración en el archivo JSON.
    Retorna True si tuvo éxito, False si hubo error.
    """
    global _config_cache

    try:
        # Validar que board_id exista
        if not config.get("board_id"):
            config["board_id"] = get_mac_address()

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        print(f"✓ Configuración guardada en {CONFIG_FILE}")
        _config_cache = config
        return True
    except Exception as e:
        print(f"✗ Error guardando configuración: {e}")
        return False


def get_board_id():
    """Retorna el board_id (MAC address)"""
    config = load_config()
    return config.get("board_id", get_mac_address())


def get_location():
    """Retorna tupla (latitude, longitude)"""
    config = load_config()
    return (
        float(config.get("latitude", 0.0)),
        float(config.get("longitude", 0.0))
    )


def set_location(latitude, longitude, location_name=""):
    """
    Actualiza la ubicación del dispositivo.

    Args:
        latitude: Latitud en grados decimales
        longitude: Longitud en grados decimales
        location_name: Nombre descriptivo opcional

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config["latitude"] = float(latitude)
    config["longitude"] = float(longitude)
    if location_name:
        config["location_name"] = location_name
    return save_config(config)


def get_sensor_type():
    """Retorna el tipo de sensor principal"""
    config = load_config()
    return config.get("sensor_type", "SCD41")


def get_sample_interval():
    """Retorna el intervalo de muestreo del sensor en segundos"""
    config = load_config()
    return int(config.get("sample_interval", 300))


def get_questdb_interval():
    """Retorna el intervalo de envío a QuestDB en segundos"""
    config = load_config()
    return int(config.get("questdb_interval", 1200))


def set_intervals(sample_interval, questdb_interval):
    """
    Actualiza los intervalos de muestreo y envío.

    Args:
        sample_interval: Intervalo de muestreo del sensor en segundos
        questdb_interval: Intervalo de envío a QuestDB en segundos

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config["sample_interval"] = int(sample_interval)
    config["questdb_interval"] = int(questdb_interval)
    return save_config(config)


def get_config_dict():
    """Retorna todo el diccionario de configuración"""
    return load_config()


def update_config(updates):
    """
    Actualiza múltiples campos de configuración.

    Args:
        updates: Diccionario con los campos a actualizar

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    config = load_config()
    config.update(updates)
    return save_config(config)


def reset_config():
    """
    Resetea la configuración a valores por defecto.
    Mantiene el board_id (MAC).
    """
    config = DEFAULT_CONFIG.copy()
    config["board_id"] = get_mac_address()
    return save_config(config)


def print_config():
    """Imprime la configuración actual (útil para debugging)"""
    config = load_config()
    print("\n" + "="*50)
    print("CONFIGURACIÓN DEL DISPOSITIVO")
    print("="*50)
    print(f"Board ID:           {config.get('board_id', 'N/A')}")
    print(f"Sensor Type:        {config.get('sensor_type', 'N/A')}")
    print(f"Latitud:            {config.get('latitude', 0.0)}")
    print(f"Longitud:           {config.get('longitude', 0.0)}")
    print(f"Ubicación:          {config.get('location_name', '(sin nombre)')}")
    print(f"Intervalo Sensing:  {config.get('sample_interval', 300)}s")
    print(f"Intervalo QuestDB:  {config.get('questdb_interval', 1200)}s")
    print("="*50 + "\n")
