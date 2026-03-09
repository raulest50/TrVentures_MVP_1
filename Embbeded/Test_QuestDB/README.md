# QuestDB Connection & Data Ingestion

Scripts para conectar Python con QuestDB en VPS Hostinger e ingerir datos del sensor SCD41 desde ESP32.

## Scripts Disponibles

### 1. `test_connection.py` - Test de Conexión
Prueba básica de conectividad con QuestDB.
```bash
python test_connection.py
```
Crea tabla de prueba, inserta datos ficticios y lee resultados.

### 2. `setup_database.py` - Configuración de Base de Datos
Crea la tabla necesaria para almacenar datos del sensor.
```bash
python setup_database.py
```
Ejecutar **una vez** antes de iniciar la ingesta.

### 3. `ingest_sensor_data.py` - Ingesta Continua
Lee datos del sensor ESP32 y los guarda en QuestDB cada 60 segundos.
```bash
python ingest_sensor_data.py
```

## Setup Rápido

1. **Instalar dependencias**:
   ```bash
   pip install requests
   ```

2. **Configurar IP del ESP32** en `config.py`:
   ```python
   ESP32_HOST = "192.168.1.100"  # Cambiar a tu IP real
   ```

3. **Probar conexión con ESP32**:
   ```bash
   python test_esp32.py
   ```

4. **Configurar base de datos**:
   ```bash
   python setup_database.py
   ```

5. **Iniciar ingesta continua**:
   ```bash
   python ingest_sensor_data.py
   ```

6. **Detener**: Presionar `Ctrl+C`

## Estructura de la Tabla

La tabla `sensor_scd41_data` almacena:
- `timestamp`: Marca temporal de la medición
- `sensor_id`: Identificador del sensor (SYMBOL para optimización)
- `co2`: Concentración de CO2 en ppm
- `temp`: Temperatura en °C
- `rh`: Humedad relativa en %
- `errors`: Contador de errores del sensor

## Consultas Útiles

Ver últimas 10 lecturas:
```sql
SELECT * FROM sensor_scd41_data
ORDER BY timestamp DESC
LIMIT 10;
```

Promedio de CO2 por hora:
```sql
SELECT
    timestamp_floor('1h', timestamp) AS hour,
    avg(co2) AS avg_co2,
    avg(temp) AS avg_temp,
    avg(rh) AS avg_rh
FROM sensor_scd41_data
WHERE timestamp > dateadd('d', -1, now())
GROUP BY hour
ORDER BY hour DESC;
```

Ver datos de hoy:
```sql
SELECT * FROM sensor_scd41_data
WHERE timestamp > dateadd('d', -1, now())
ORDER BY timestamp DESC;
```

## Config
- Host: `187.124.90.77:9000` (VPS Hostinger)
- Endpoints:
  - SQL queries: `GET /exec?query=...` - Para consultas y DDL
  - ILP ingestion: `POST /write` - Para insertar datos rápido

## Common Errors Fixed

### ❌ `Read timed out`
- **Causa**: Intentar `GET /` (la raíz no responde rápido en QuestDB)
- **Fix**: Usar `GET /exec` con query de prueba como `SELECT 1;`

### ❌ `Method POST not supported`
- **Causa**: Usar `POST` en `/exec` (error común por confusión con otras APIs)
- **Fix**: `/exec` requiere `GET` con params, no POST con data

### ❌ `Non-multipart POST not supported`
- **Causa**: Usar `/imp` para ILP (endpoint equivocado, `/imp` es solo para CSV)
- **Fix**: Usar `/write` para Influx Line Protocol, que es el estándar para time-series

## API Correcta

### SQL (Lectura/Escritura)
Para cualquier query SQL: SELECT, CREATE, INSERT, etc.
```python
response = requests.get(
    'http://187.124.90.77:9000/exec',
    params={'query': 'SELECT * FROM tabla;'}
)
```

### ILP (Ingesta rápida)
Formato: `tabla,tag=val field=val timestamp_ns`. Mucho más rápido que INSERT para sensores.
```python
payload = "sensor_test,sensor_id=S1 temperatura=25.5,humedad=60.2 1234567890000000000"
response = requests.post(
    'http://187.124.90.77:9000/write',
    data=payload,
    headers={'Content-Type': 'text/plain'}
)
```

## Notas
- `/exec` acepta CREATE, INSERT, SELECT todo con GET (no POST)
- ILP es más rápido que INSERT para ingesta masiva (recomendado para IoT)
- Timestamp en ILP: nanosegundos desde epoch (usar `int(time.time() * 1e9)`)
- Success codes: 200 (exec), 204 o 200 (write)
