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
QUERY_URL = f"{BASE_URL}/exec"


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
        response = requests.get(EXEC_URL, params={'query': query})
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
    """Inserta algunos datos ficticios en la tabla"""
    datos = [
        ("sensor_01", 25.5, 60.2),
        ("sensor_01", 26.1, 58.7),
        ("sensor_02", 22.3, 65.4),
        ("sensor_02", 23.0, 64.1),
    ]
    
    print("\nInsertando datos ficticios...")
    
    for sensor_id, temp, hum in datos:
        query = f"""
        INSERT INTO sensor_test 
        VALUES(now(), '{sensor_id}', {temp}, {hum});
        """
        
        try:
            response = requests.get(EXEC_URL, params={'query': query})
            if response.status_code == 200:
                print(f"  ✓ Insertado: {sensor_id} - Temp: {temp}°C, Hum: {hum}%")
            else:
                print(f"  ✗ Error al insertar: {response.status_code}")
                print(f"    Respuesta: {response.text}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        time.sleep(0.1)  # Pequeña pausa entre inserciones


def leer_datos():
    """Lee los datos de la tabla"""
    query = "SELECT * FROM sensor_test ORDER BY timestamp DESC LIMIT 10;"
    
    try:
        response = requests.get(QUERY_URL, params={'query': query})
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Datos leídos exitosamente:")
            print(json.dumps(data, indent=2))
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
    print(f"URL: {BASE_URL}")
    
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code in [200, 404]:  # 404 es normal para la raíz
            print("✓ Servidor accesible")
            return True
        else:
            print(f"✗ Respuesta inesperada: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("✗ Timeout - El servidor no responde")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Error de conexión - Verifica la IP y el puerto")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
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
