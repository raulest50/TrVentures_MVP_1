"""
Script de prueba para timer_service en PC (CPython)
Simula el comportamiento de MicroPython para debugging de sincronización NTP

Este script NO usa el timer_service.py original de MicroPython.
Es una adaptación para probar la lógica de sincronización NTP en tu PC.
"""

import time
import socket
import struct
from datetime import datetime, timezone


# ==================== CONFIGURACIÓN ====================

NTP_HOST = "pool.ntp.org"
NTP_PORT = 123
DEFAULT_UTC_OFFSET_HOURS = 0
NTP_RESYNC_INTERVAL = 6 * 60 * 60  # 6 horas
VALID_EPOCH_MIN = 1704067200  # 2024-01-01T00:00:00Z

# Estado interno (simula las variables globales de timer_service.py)
_utc_offset_seconds = DEFAULT_UTC_OFFSET_HOURS * 3600
_last_ntp_sync = 0
_last_ntp_error = None


# ==================== FUNCIONES NTP ====================

def get_ntp_time(host=NTP_HOST, port=NTP_PORT, timeout=10):
    """
    Consulta un servidor NTP y retorna el timestamp Unix en segundos.

    Implementación compatible con CPython (no MicroPython).
    """
    # Construir paquete NTP (formato básico)
    # NTP packet: 48 bytes, primer byte = 0x1B (version 3, client mode)
    ntp_packet = b'\x1b' + 47 * b'\0'

    try:
        # Crear socket UDP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)

            # Enviar request
            sock.sendto(ntp_packet, (host, port))

            # Recibir respuesta
            data, _ = sock.recvfrom(1024)

            if len(data) < 48:
                raise ValueError(f"Respuesta NTP incompleta: {len(data)} bytes")

            # Extraer timestamp del servidor (bytes 40-43: segundos)
            # NTP epoch: 1 Jan 1900, Unix epoch: 1 Jan 1970
            # Diferencia: 2208988800 segundos
            ntp_time = struct.unpack('!I', data[40:44])[0]
            unix_time = ntp_time - 2208988800

            return unix_time

    except socket.timeout:
        raise TimeoutError(f"Timeout al conectar con {host}:{port}")
    except socket.gaierror as e:
        raise ConnectionError(f"No se pudo resolver DNS para {host}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error consultando NTP: {e}")


# ==================== FUNCIONES DE timer_service (adaptadas) ====================

def set_utc_offset(hours=0, minutes=0):
    """Configura el desfase local respecto a UTC para visualización."""
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
    Sincroniza el tiempo vía NTP.

    En PC (CPython) no podemos cambiar el reloj del sistema,
    pero podemos verificar que la sincronización funciona.

    Retorna True si la hora está sincronizada o se pudo obtener de NTP.
    """
    global _last_ntp_sync, _last_ntp_error

    now = int(time.time())

    # Verificar si necesitamos re-sincronizar
    if not force and _last_ntp_sync and (now - _last_ntp_sync) < NTP_RESYNC_INTERVAL:
        return True

    try:
        # Obtener tiempo desde NTP
        ntp_timestamp = get_ntp_time(NTP_HOST, NTP_PORT)

        # Comparar con tiempo del sistema
        system_time = int(time.time())
        time_diff = abs(ntp_timestamp - system_time)

        print(f"\n✓ Sincronización NTP exitosa:")
        print(f"  • Servidor NTP: {NTP_HOST}")
        print(f"  • Tiempo NTP:     {datetime.fromtimestamp(ntp_timestamp, tz=timezone.utc).isoformat()}")
        print(f"  • Tiempo Sistema: {datetime.fromtimestamp(system_time, tz=timezone.utc).isoformat()}")
        print(f"  • Diferencia:     {time_diff}s")

        if time_diff > 5:
            print(f"  ⚠️ El reloj del sistema está desincronizado por {time_diff}s")
        else:
            print(f"  ✓ El reloj del sistema está sincronizado")

        _last_ntp_sync = system_time
        _last_ntp_error = None
        return True

    except Exception as exc:
        _last_ntp_error = str(exc)
        print(f"\n✗ Error de sincronización NTP: {_last_ntp_error}")
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


def format_iso8601_utc(epoch_seconds=None):
    """Formatea un epoch como ISO 8601 UTC."""
    if epoch_seconds is None:
        epoch_seconds = get_current_epoch_utc()

    dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_iso8601_local(epoch_seconds=None):
    """Formatea un epoch como ISO 8601 local con offset."""
    if epoch_seconds is None:
        epoch_seconds = get_current_epoch_utc()

    local_epoch = int(epoch_seconds) + _utc_offset_seconds
    dt = datetime.fromtimestamp(local_epoch, tz=timezone.utc)

    offset = _utc_offset_seconds
    sign = "+" if offset >= 0 else "-"
    offset = abs(offset)
    offset_hours = offset // 3600
    offset_minutes = (offset % 3600) // 60

    return dt.strftime(f"%Y-%m-%dT%H:%M:%S{sign}{offset_hours:02d}:{offset_minutes:02d}")


def get_status():
    """Retorna un resumen útil para debugging y monitoreo."""
    return {
        "time_valid": is_time_valid(),
        "epoch_utc": get_current_epoch_utc(),
        "iso_utc": format_iso8601_utc(),
        "iso_local": format_iso8601_local(),
        "utc_offset_seconds": _utc_offset_seconds,
        "last_ntp_sync": _last_ntp_sync,
        "last_ntp_error": _last_ntp_error,
    }


# ==================== TESTS ====================

def test_basic_functionality():
    """Test 1: Funciones básicas de tiempo"""
    print("\n" + "="*70)
    print("TEST 1: FUNCIONES BÁSICAS DE TIEMPO")
    print("="*70)

    print("\n1. Tiempo válido:")
    print(f"   is_time_valid() = {is_time_valid()}")

    print("\n2. Epoch actual:")
    print(f"   get_current_epoch_utc() = {get_current_epoch_utc()}")

    print("\n3. Timestamp nanosegundos:")
    print(f"   get_timestamp_ns() = {get_timestamp_ns()}")

    print("\n4. Formato ISO 8601 UTC:")
    print(f"   format_iso8601_utc() = {format_iso8601_utc()}")

    print("\n5. Offset UTC (default = 0):")
    print(f"   get_utc_offset_seconds() = {get_utc_offset_seconds()}")

    print("\n✓ Test 1 completado")


def test_utc_offset():
    """Test 2: Configuración de offset UTC"""
    print("\n" + "="*70)
    print("TEST 2: CONFIGURACIÓN DE OFFSET UTC")
    print("="*70)

    print("\n1. Sin offset (UTC):")
    set_utc_offset(hours=0)
    print(f"   UTC:   {format_iso8601_utc()}")
    print(f"   Local: {format_iso8601_local()}")

    print("\n2. México City (UTC-6):")
    set_utc_offset(hours=-6)
    print(f"   UTC:   {format_iso8601_utc()}")
    print(f"   Local: {format_iso8601_local()}")

    print("\n3. Nueva York (UTC-5):")
    set_utc_offset(hours=-5)
    print(f"   UTC:   {format_iso8601_utc()}")
    print(f"   Local: {format_iso8601_local()}")

    print("\n4. Madrid (UTC+1):")
    set_utc_offset(hours=1)
    print(f"   UTC:   {format_iso8601_utc()}")
    print(f"   Local: {format_iso8601_local()}")

    print("\n5. Tokio (UTC+9):")
    set_utc_offset(hours=9)
    print(f"   UTC:   {format_iso8601_utc()}")
    print(f"   Local: {format_iso8601_local()}")

    # Restaurar a UTC-6 para siguientes tests
    set_utc_offset(hours=-6)

    print("\n✓ Test 2 completado")


def test_ntp_sync():
    """Test 3: Sincronización NTP"""
    print("\n" + "="*70)
    print("TEST 3: SINCRONIZACIÓN NTP")
    print("="*70)

    print("\n1. Intentando sincronización con NTP...")
    success = sync_ntp(force=True)

    if success:
        print("\n2. Estado después de sincronización:")
        status = get_status()
        for key, value in status.items():
            print(f"   • {key}: {value}")

        print("\n3. Verificando re-sincronización (debería usar cache)...")
        success2 = sync_ntp(force=False)
        print(f"   sync_ntp(force=False) = {success2}")
        print(f"   (Debería retornar True sin re-sincronizar)")

        print("\n✓ Test 3 completado exitosamente")
    else:
        print("\n✗ Test 3 FALLÓ - No se pudo sincronizar con NTP")
        print(f"   Error: {_last_ntp_error}")


def test_multiple_ntp_servers():
    """Test 4: Probar múltiples servidores NTP"""
    print("\n" + "="*70)
    print("TEST 4: MÚLTIPLES SERVIDORES NTP")
    print("="*70)

    servers = [
        "pool.ntp.org",
        "time.google.com",
        "time.cloudflare.com",
        "time.windows.com",
    ]

    for server in servers:
        print(f"\nProbando servidor: {server}")
        try:
            ntp_time = get_ntp_time(server, timeout=5)
            print(f"  ✓ Éxito: {datetime.fromtimestamp(ntp_time, tz=timezone.utc).isoformat()}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("\n✓ Test 4 completado")


def main():
    """Ejecuta todos los tests"""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + " "*15 + "TIMER SERVICE - TEST SUITE" + " "*27 + "█")
    print("█" + " "*68 + "█")
    print("█"*70)

    try:
        test_basic_functionality()
        test_utc_offset()
        test_ntp_sync()
        test_multiple_ntp_servers()

        print("\n" + "="*70)
        print("✓ TODOS LOS TESTS COMPLETADOS")
        print("="*70)

        print("\n📊 RESUMEN FINAL:")
        status = get_status()
        for key, value in status.items():
            print(f"  • {key}: {value}")

    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrumpidos por el usuario")
    except Exception as e:
        print(f"\n\n✗ Error durante los tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
