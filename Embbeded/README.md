## Flashing micropython into pico2W


## Direccion Ip Pico2W

```
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
print(wlan.ifconfig())
```