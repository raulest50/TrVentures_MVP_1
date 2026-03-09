"""
Script de prueba para validar conexión con QuestDB
Prueba lectura y escritura de datos ficticios
"""

import requests
import json
from datetime import datetime
import time

# Configuración del servidor QuestDB
QUESTDB_HOST = "187.124.90.77"
QUESTDB_HTTP_PORT = 9000

# URLs base
BASE_URL = f"http://{QUESTDB_HOST}:{QUESTDB_HTTP_PORT}"
EXEC_URL = f"{BASE_URL}/exec"
WRITE_URL = f"{BASE_URL}/write"  # Endpoint para ILP

# Headers comunes para todas las peticiones
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

# Configuración de sesión para reutilizar conexiones
session = requests.Session()
session.headers.update(HEADERS)


def crear_tabla():
    """Crea una tabla de prueba para sensores"""
    query = """
    CREATE TABLE IF NOT EXISTS sensor_test (
        timestamp TIMESTAMP,
        sensor_id SYMBOL,
        temperatura DOUBLE,
        humedad DOUBLE
    ) timestamp(timestamp) PARTITION BY DAY;
    """

    try:
        response = session.get(EXEC_URL, params={'query': query}, timeout=(5, 10))
        if response.status_code == 200:
            print("✓ Tabla creada exitosamente")
            return True
        else:
            print(f"✗ Error al crear tabla: {response.status_code}")
            print(f"  Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        return False


def insertar_datos_ficticios():
    """Inserta datos ficticios usando Influx Line Protocol (ILP) por HTTP"""
    datos = [
        ("sensor_01", 25.5, 60.2),
        ("sensor_01", 26.1, 58.7),
        ("sensor_02", 22.3, 65.4),
        ("sensor_02", 23.0, 64.1),
    ]

    print("\nInsertando datos ficticios usando ILP...")

    # Construir payload en formato Influx Line Protocol
    now_ns = int(time.time() * 1e9)
    lines = []
    for i, (sensor_id, temp, hum) in enumerate(datos):
        ts = now_ns + i * 1_000_000_000  # Separar 1 segundo entre cada lectura
        lines.append(f"sensor_test,sensor_id={sensor_id} temperatura={temp},humedad={hum} {ts}")

    payload = "\n".join(lines)

    try:
        response = session.post(
            WRITE_URL,
            data=payload,
            headers={"Content-Type": "text/plain"},
            timeout=(5, 10)
        )
        # QuestDB /write responde 204 o 200 en éxito
        if response.status_code in [200, 204]:
            print(f"  ✓ Insertados {len(datos)} registros exitosamente")
            for sensor_id, temp, hum in datos:
                print(f"    - {sensor_id}: Temp={temp}°C, Hum={hum}%")
        else:
            print(f"  ✗ Error al insertar: {response.status_code}")
            print(f"    Respuesta: {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def leer_datos():
    """Lee los datos de la tabla"""
    query = "SELECT * FROM sensor_test ORDER BY timestamp DESC LIMIT 10;"

    try:
        response = session.get(EXEC_URL, params={'query': query}, timeout=(5, 10))
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Datos leídos exitosamente:")

            # Formatear salida más legible
            cols = [c["name"] for c in data.get("columns", [])]
            rows = data.get("dataset", [])

            print(f"\nColumnas: {cols}")
            print(f"Total filas: {data.get('count', 0)}\n")

            for row in rows:
                print(f"  {row}")

            return data
        else:
            print(f"✗ Error al leer datos: {response.status_code}")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error al leer: {e}")
        return None


def test_conexion():
    """Prueba la conexión básica al servidor"""
    print("Probando conexión con QuestDB...")
    print(f"URL: {EXEC_URL}")

    try:
        # Probar con una consulta simple usando GET
        response = session.get(
            EXEC_URL,
            params={'query': 'SELECT 1;'},
            timeout=(5, 10)  # (connect timeout, read timeout)
        )
        if response.status_code == 200:
            print("✓ Servidor accesible")
            print(f"  Status: {response.status_code}")
            result = response.json()
            print(f"  Respuesta: {result}")
            return True
        else:
            print(f"✗ Respuesta inesperada: {response.status_code}")
            print(f"  Respuesta: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout as e:
        print(f"✗ Timeout - El servidor no responde")
        print(f"  Detalles: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Error de conexión")
        print(f"  Detalles: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        return False


def main():
    print("=" * 60)
    print("TEST DE CONEXIÓN Y OPERACIONES CON QUESTDB")
    print("=" * 60)
    print()
    
    # 1. Test de conexión
    if not test_conexion():
        print("\n⚠ No se pudo conectar al servidor. Verifica:")
        print("  - Que el contenedor Docker esté corriendo")
        print("  - Que el puerto 9000 esté abierto en el firewall")
        print("  - Que la IP sea correcta")
        return
    
    print()
    
    # 2. Crear tabla
    print("-" * 60)
    if not crear_tabla():
        return
    
    # 3. Insertar datos
    print("-" * 60)
    insertar_datos_ficticios()
    
    # 4. Leer datos
    print("-" * 60)
    leer_datos()
    
    print()
    print("=" * 60)
    print("PRUEBA COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
