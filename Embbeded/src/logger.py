"""
Sistema de logging para MicroPython con buffer circular.
Captura todos los logs y los expone via HTTP para debugging.
"""

import time

# Buffer circular de logs (últimos N mensajes)
MAX_LOGS = 100
_log_buffer = []
_log_index = 0


def log(level, module, message):
    """
    Registra un mensaje de log con timestamp.

    Args:
        level: Nivel del log (DEBUG, INFO, WARNING, ERROR)
        module: Nombre del módulo que genera el log
        message: Mensaje a registrar
    """
    global _log_buffer, _log_index

    try:
        # Timestamp local (epoch UTC en segundos)
        timestamp = int(time.time())

        # Crear entrada de log
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "module": module,
            "message": str(message)
        }

        # Agregar al buffer circular
        if len(_log_buffer) < MAX_LOGS:
            _log_buffer.append(log_entry)
        else:
            # Sobrescribir el log más antiguo
            _log_buffer[_log_index % MAX_LOGS] = log_entry
            _log_index += 1

        # Imprimir en consola (REPL)
        print(f"[{level}] {module}: {message}")

    except Exception as e:
        # Fallback: solo imprimir en consola
        print(f"[{level}] {module}: {message}")
        print(f"  (Error en logger: {e})")


def debug(module, message):
    """Log nivel DEBUG"""
    log("DEBUG", module, message)


def info(module, message):
    """Log nivel INFO"""
    log("INFO", module, message)


def warning(module, message):
    """Log nivel WARNING"""
    log("WARNING", module, message)


def error(module, message):
    """Log nivel ERROR"""
    log("ERROR", module, message)


def get_logs(limit=None, level_filter=None):
    """
    Retorna los logs almacenados en el buffer.

    Args:
        limit: Número máximo de logs a retornar (default: todos)
        level_filter: Filtrar por nivel (ej: "ERROR", "WARNING")

    Returns:
        Lista de diccionarios con los logs
    """
    logs = _log_buffer.copy()

    # Filtrar por nivel si se especifica
    if level_filter:
        logs = [log for log in logs if log["level"] == level_filter]

    # Limitar cantidad
    if limit and limit < len(logs):
        logs = logs[-limit:]  # Últimos N logs

    return logs


def get_logs_count():
    """Retorna el número total de logs en el buffer"""
    return len(_log_buffer)


def clear_logs():
    """Limpia el buffer de logs"""
    global _log_buffer, _log_index
    _log_buffer = []
    _log_index = 0
    print("✓ Buffer de logs limpiado")
