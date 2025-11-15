# scd4x.py — Driver SCD41 para MicroPython (compatible con Pico2W)
# Fuente: Sensirion (recortado para uso directo)

import time

class SCD4X:
    def __init__(self, i2c, address=0x62):
        self.i2c = i2c
        self.addr = address

    def _write(self, cmd, data=None):
        buf = cmd.to_bytes(2, 'big')
        if data:
            buf += data
        self.i2c.writeto(self.addr, buf)

    def _read(self, cmd, nbytes):
        self._write(cmd)
        time.sleep_ms(1)
        return self.i2c.readfrom(self.addr, nbytes)

    def start_periodic_measurement(self):
        self._write(0x21B1)

    def stop_periodic_measurement(self):
        self._write(0x3F86)

    def get_data_ready(self):
        raw = self._read(0xE4B8, 3)
        return (raw[0] << 8 | raw[1]) & 0x07FF

    def read_measurement(self):
        raw = self._read(0xEC05, 9)

        co2 = raw[0] << 8 | raw[1]
        temp_raw = raw[3] << 8 | raw[4]
        rh_raw = raw[6] << 8 | raw[7]

        temperature = -45 + 175 * (temp_raw / 65535)
        humidity = 100 * (rh_raw / 65535)

        return co2, temperature, humidity

    @property
    def co2(self):
        dr = self.get_data_ready()
        if dr == 0:
            return None
        return self.read_measurement()[0]

    @property
    def temperature(self):
        dr = self.get_data_ready()
        if dr == 0:
            return None
        return self.read_measurement()[1]

    @property
    def relative_humidity(self):
        dr = self.get_data_ready()
        if dr == 0:
            return None
        return self.read_measurement()[2]
