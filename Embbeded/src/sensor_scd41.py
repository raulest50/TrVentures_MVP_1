import timer_service
from machine import Pin, I2C
from scd4x import SCD4X

# Intervalo minimo permitido para el muestreo automatico del sensor.
MIN_SAMPLE_INTERVAL = 300

# Se carga desde device_config.json al iniciar (ver main.py).
SAMPLE_INTERVAL = MIN_SAMPLE_INTERVAL

# Ventana de warm-up durante la cual ignoramos errores del sensor.
WARMUP_SECONDS = 30

# Estado global interno del modulo.
_i2c = None
_scd = None
_last_sample = -999999
START_TIME = timer_service.get_current_epoch_utc()
_init_error = None

latest_readings = {
    "co2": None,
    "temp": None,
    "rh": None,
    "last_ok": 0,
    "errors": 0,
    "sample_interval": SAMPLE_INTERVAL,
    "last_status": "idle",
    "last_error": None,
    "last_manual_sample": 0,
    "last_manual_status": "idle",
}


def init_sensor():
    """
    Inicializa el bus I2C y el SCD41, y arranca la medicion periodica.
    Debe llamarse una sola vez al inicio del programa.
    """
    global _i2c, _scd, START_TIME, _init_error

    import time

    try:
        _i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)
        _scd = SCD4X(_i2c)
        _scd.start_periodic_measurement()
        print("SCD41: medicion periodica iniciada (intervalo hardware ~5 s)")

        time.sleep(10)
        START_TIME = timer_service.get_current_epoch_utc()
        _init_error = None
        latest_readings["last_status"] = "idle"
        latest_readings["last_error"] = None
        return True
    except Exception as error:
        _scd = None
        _init_error = str(error)
        latest_readings["last_status"] = "init_error"
        latest_readings["last_error"] = _init_error
        print("SCD41 no disponible en este arranque: {}".format(error))
        return False


def set_sample_interval(seconds):
    """
    Cambia el intervalo de muestreo automatico dinamicamente.
    """
    global SAMPLE_INTERVAL

    seconds = int(seconds)
    if seconds < MIN_SAMPLE_INTERVAL:
        raise ValueError(
            "sample_interval debe ser mayor o igual a {} segundos".format(
                MIN_SAMPLE_INTERVAL
            )
        )

    SAMPLE_INTERVAL = seconds
    latest_readings["sample_interval"] = seconds
    print("Intervalo de muestreo cambiado a {} segundos".format(seconds))


def _build_result(success, now, message, data_ready):
    snapshot = get_latest_readings()
    return {
        "success": bool(success),
        "timestamp": now,
        "data_ready": bool(data_ready),
        "message": message,
        "readings": snapshot,
    }


def _perform_read(now, source):
    in_warmup = (now - START_TIME) < WARMUP_SECONDS
    data_ready = False

    try:
        data_ready = bool(_scd.get_data_ready())
        if not data_ready:
            message = (
                "Sensor en warm-up; aun sin datos listos."
                if in_warmup
                else "No hay datos listos aun."
            )
            latest_readings["last_status"] = "waiting_data"
            latest_readings["last_error"] = None
            if source == "manual":
                latest_readings["last_manual_sample"] = now
                latest_readings["last_manual_status"] = "waiting_data"
            else:
                print("SCD41: {}".format(message))
            return _build_result(False, now, message, False)

        co2, temp, rh = _scd.read_measurement()
        latest_readings["co2"] = float(co2)
        latest_readings["temp"] = float(temp)
        latest_readings["rh"] = float(rh)
        latest_readings["last_ok"] = now
        latest_readings["last_status"] = "ok"
        latest_readings["last_error"] = None

        if source == "manual":
            latest_readings["last_manual_sample"] = now
            latest_readings["last_manual_status"] = "ok"

        message = "Lectura actualizada correctamente."
        print("SCD41 [{}] -> CO2={}, Temp={}, RH={}".format(source, co2, temp, rh))
        return _build_result(True, now, message, True)

    except Exception as error:
        latest_readings["last_status"] = "error"
        latest_readings["last_error"] = str(error)

        if source == "manual":
            latest_readings["last_manual_sample"] = now
            latest_readings["last_manual_status"] = "error"

        if in_warmup:
            message = "Warm-up del SCD41: error temporal ignorado."
            print("Warm-up SCD41, error esperado: {}".format(error))
            return _build_result(False, now, message, data_ready)

        latest_readings["errors"] += 1
        message = "Error leyendo SCD41: {}".format(error)
        print(message)
        return _build_result(False, now, message, data_ready)


def update_sensor():
    """
    Actualiza latest_readings como maximo una vez cada SAMPLE_INTERVAL.
    Llamar a esta funcion en el loop principal.
    """
    global _last_sample

    if _scd is None:
        return None

    now = timer_service.get_current_epoch_utc()
    if now - _last_sample < SAMPLE_INTERVAL:
        return None

    _last_sample = now
    return _perform_read(now, "auto")


def sample_now():
    """
    Fuerza una lectura local inmediata sin alterar la cadencia automatica.
    No agrega muestras al backlog ni dispara subida a nube.
    """
    if _scd is None:
        return {
            "success": False,
            "data_ready": False,
            "message": "Sensor no inicializado o no disponible.",
            "readings": get_latest_readings(),
        }

    now = timer_service.get_current_epoch_utc()
    return _perform_read(now, "manual")


def get_latest_readings():
    """Devuelve una copia enriquecida de las ultimas lecturas del sensor."""
    snapshot = latest_readings.copy()
    valid = (
        snapshot.get("co2") is not None
        and snapshot.get("temp") is not None
        and snapshot.get("rh") is not None
        and snapshot.get("last_ok", 0) > 0
    )

    snapshot["valid"] = valid
    snapshot["last_ok_reading"] = snapshot.get("last_ok", 0) or None
    snapshot["error_count"] = snapshot.get("errors", 0)
    snapshot["sensor_initialized"] = _scd is not None
    snapshot["init_error"] = _init_error
    return snapshot
