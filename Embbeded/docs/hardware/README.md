# Hardware wiring

Esta carpeta contiene la documentación mínima del cableado funcional del nodo:

- `wiring.yaml`: fuente de verdad textual en formato WireViz
- `wiring.svg`: salida visual para embebido en `README.md`

## Alcance de esta primera versión

Solo se documenta:

- Raspberry Pi Pico 2 W
- módulo / breakout SCD41
- conexiones funcionales de `3V3`, `GND`, `SDA`, `SCL`

No se documentan todavía:

- fixture mecánico
- tornillería
- alimentación USB completa
- periféricos externos del escritorio

## Verdad técnica usada

La configuración del firmware actual define el bus I2C así:

- `SDA = GP0`
- `SCL = GP1`

Esto está implementado en `src/sensor_scd41.py` con:

```python
I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)
```

Para los nombres del módulo sensor se usa la serigrafía visible del breakout en las fotos del prototipo:

- `VCC`
- `GND`
- `SCL`
- `SDA`

## Colores de cable usados en la documentación

Se registran con intención descriptiva, no como restricción obligatoria de ensamblaje:

- `RD` = 3V3
- `BK` = GND
- `OG` = SDA
- `BU` = SCL

Si el prototipo físico cambia de color de cables, debe priorizarse la tabla de señales por encima del color.

## Regeneración

La fuente WireViz está pensada para regenerar el diagrama si se instala la herramienta localmente.

Referencia oficial:

- [WireViz en GitHub](https://github.com/wireviz/WireViz)

Flujo esperado:

1. Instalar WireViz y GraphViz en la máquina local.
2. Ejecutar WireViz sobre `wiring.yaml`.
3. Exportar de nuevo `wiring.svg`.

Ejemplo orientativo:

```bash
wireviz docs/hardware/wiring.yaml
```

Si cambia el cableado real:

1. primero se actualiza `wiring.yaml`
2. luego se regenera `wiring.svg`
3. después se revisa la tabla del `README.md`
