# QuestDB Connection Test

Script de prueba para conectar Python con QuestDB en VPS Hostinger.

## Quick Start
```bash
python test_connection.py
```
Crea tabla, inserta datos de prueba y lee resultados.

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
