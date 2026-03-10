"""
Servicio de tiempo para MicroPython.

- Sincroniza el RTC usando NTP cuando hay red disponible.
- Permite configurar un offset UTC para mostrar hora local.
- Expone metodos para obtener epoch UTC y timestamp nanosegundos.

Para timestamps universales destinados a bases de datos, usa siempre UTC.
El offset configurado solo debe afectar vistas u horarios locales.
"""

import time

try:
    import ntptime
except ImportError:
    ntptime = None

try:
    from machine import RTC
except ImportError:
    RTC = None


NTP_HOST = "pool.ntp.org"
DEFAULT_UTC_OFFSET_HOURS = 0
NTP_RESYNC_INTERVAL = 6 * 60 * 60
VALID_EPOCH_MIN = 1704067200  # 2024-01-01T00:00:00Z

_utc_offset_seconds = DEFAULT_UTC_OFFSET_HOURS * 3600
_last_ntp_sync = 0
_last_ntp_error = None


def set_utc_offset(hours=0, minutes=0):
    """Configura el desfase local respecto a UTC para visualizacion."""
    global _utc_offset_seconds
    sign = -1 if hours < 0 or minutes < 0 else 1
    total_seconds = (abs(int(hours)) * 3600) + (abs(int(minutes)) * 60)
    _utc_offset_seconds = sign * total_seconds
    return _utc_offset_seconds


def get_utc_offset_seconds():
    """Retorna el offset configurado en segundos."""
    return _utc_offset_seconds


def is_time_valid():
    """Indica si el reloj parece estar sincronizado con una fecha razonable."""
    try:
        return int(time.time()) >= VALID_EPOCH_MIN
    except Exception:
        return False


def sync_ntp(force=False):
    """
    Sincroniza el RTC via NTP.
    Retorna True si la hora quedo sincronizada o ya estaba fresca.
    """
    global _last_ntp_sync, _last_ntp_error

    now = 0
    try:
        now = int(time.time())
    except Exception:
        pass

    if not force and _last_ntp_sync and now and (now - _last_ntp_sync) < NTP_RESYNC_INTERVAL:
        return True

    if ntptime is None:
        _last_ntp_error = "ntptime no disponible"
        return False

    try:
        ntptime.host = NTP_HOST
    except Exception:
        pass

    try:
        ntptime.settime()
        _last_ntp_sync = int(time.time())
        _last_ntp_error = None
        return True
    except Exception as exc:
        _last_ntp_error = str(exc)
        return False


def get_current_epoch_utc():
    """Retorna segundos UTC desde Unix epoch."""
    return int(time.time())


def get_current_epoch_local():
    """Retorna segundos epoch ajustados al offset configurado."""
    return get_current_epoch_utc() + _utc_offset_seconds


def get_timestamp_ns():
    """Retorna timestamp UTC en nanosegundos para ILP/QuestDB."""
    return get_current_epoch_utc() * 1_000_000_000


def get_current_datetime_utc():
    """Retorna la fecha/hora UTC como tupla de time.gmtime()."""
    return time.gmtime(get_current_epoch_utc())


def get_current_datetime_local():
    """Retorna la fecha/hora local usando el offset configurado."""
    return time.gmtime(get_current_epoch_local())


def format_iso8601_utc(epoch_seconds=None):
    """Formatea un epoch como ISO 8601 UTC."""
    if epoch_seconds is None:
        epoch_seconds = get_current_epoch_utc()
    year, month, mday, hour, minute, second, _, _ = time.gmtime(int(epoch_seconds))
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        year, month, mday, hour, minute, second
    )


def format_iso8601_local(epoch_seconds=None):
    """Formatea un epoch como ISO 8601 local con offset."""
    if epoch_seconds is None:
        epoch_seconds = get_current_epoch_utc()

    local_epoch = int(epoch_seconds) + _utc_offset_seconds
    year, month, mday, hour, minute, second, _, _ = time.gmtime(local_epoch)

    offset = _utc_offset_seconds
    sign = "+" if offset >= 0 else "-"
    offset = abs(offset)
    offset_hours = offset // 3600
    offset_minutes = (offset % 3600) // 60

    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}{}{:02d}:{:02d}".format(
        year,
        month,
        mday,
        hour,
        minute,
        second,
        sign,
        offset_hours,
        offset_minutes,
    )


def get_status():
    """Retorna un resumen util para debugging y monitoreo."""
    return {
        "time_valid": is_time_valid(),
        "epoch_utc": get_current_epoch_utc(),
        "iso_utc": format_iso8601_utc(),
        "iso_local": format_iso8601_local(),
        "utc_offset_seconds": _utc_offset_seconds,
        "last_ntp_sync": _last_ntp_sync,
        "last_ntp_error": _last_ntp_error,
        "rtc_available": RTC is not None,
        "ntptime_available": ntptime is not None,
    }
