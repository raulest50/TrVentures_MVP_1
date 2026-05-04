"""
boot.py - Frontera Data Labs IoT Device
Se ejecuta ANTES que main.py al arrancar la Raspberry Pi Pico W.
Configura el entorno y maneja errores críticos de arranque.
"""

import sys
import time

def safe_boot():
    """
    Rutina de arranque segura con manejo de excepciones.
    Si algo falla crítico, intenta indicarlo con LED.
    """
    try:
        print("\n" + "="*60)
        print("  BOOT.PY - Frontera Data Labs IoT Device")
        print("  Raspberry Pi Pico W + MicroPython")
        print("="*60)

        # Mostrar información de arranque
        epoch = time.time()
        print(f"• Tiempo actual (epoch): {epoch}")

        # Verificar si el tiempo es válido (posterior a 2024)
        VALID_EPOCH_MIN = 1704067200  # 2024-01-01T00:00:00Z
        if epoch < VALID_EPOCH_MIN:
            print("⚠️  ADVERTENCIA: RTC no sincronizado (año < 2024)")
            print("   Se sincronizará con NTP en main.py")
        else:
            print("✓ RTC parece sincronizado")

        # Información del sistema
        print(f"• Python version: {sys.version}")
        print(f"• Platform: {sys.platform}")

        # Verificar espacio en filesystem (si está disponible)
        try:
            import os
            stat = os.statvfs('/')
            block_size = stat[0]
            total_blocks = stat[2]
            free_blocks = stat[3]
            total_kb = (total_blocks * block_size) // 1024
            free_kb = (free_blocks * block_size) // 1024
            print(f"• Filesystem: {free_kb}KB libre de {total_kb}KB total")
        except Exception:
            print("• Filesystem: información no disponible")

        print("\n✓ boot.py completado exitosamente")
        print("  Iniciando main.py...\n")
        print("="*60 + "\n")

        return True

    except Exception as e:
        # Si boot.py falla, intentar indicarlo visualmente
        print(f"\n❌ ERROR CRÍTICO EN BOOT.PY: {e}")
        print("   Tipo:", type(e).__name__)

        # Intentar parpadear LED para indicar error
        try:
            from machine import Pin
            led = Pin("LED", Pin.OUT)
            print("   Parpadeando LED para indicar error...")

            for _ in range(20):
                led.toggle()
                time.sleep(0.1)

            led.value(0)  # Apagar LED

        except Exception as led_error:
            print(f"   No se pudo controlar LED: {led_error}")

        # No bloquear el arranque, permitir que main.py intente ejecutarse
        print("   Continuando con main.py de todas formas...\n")
        return False


# Ejecutar boot seguro
safe_boot()
