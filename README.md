# MicroPython ST7302 ST7305 driver
MicroPython driver for ST7302/ST7305 2.13/2.9 inch Reflective TFT, viper(faster) and bytecode version provided. No additional memory is required after init.

example for [ESP32-S2](https://micropython.org/download/LOLIN_S2_MINI/)

> `refresh()` on ESP32-S2: viper cost 7 ms, byte code cost 140 ms.

```python
import time
from machine import Pin, SPI
from st7302viper import TFT213

led = Pin(15, Pin.OUT, value = 1)

pw = Pin(16, Pin.OUT, value = 1)
cs = Pin(39, Pin.OUT, value = 1)
dc = Pin(37, Pin.OUT, value = 1)
rs = Pin(35, Pin.OUT, value = 1)
spi = SPI(1, baudrate=40_000_000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(33), miso=Pin(17))

lcd = TFT213(spi, cs, dc, rs)
lcd.text('Hello, World', 0, 0, 1)
t = time.ticks_ms()
lcd.refresh()

t = time.ticks_diff(time.ticks_ms(), t)
lcd.text(f'Cost {t} ms.', 0, 10, 1)
lcd.refresh()
```

Special thanks to @zhcong for the ST7302 LCD screen driver implementation.
Check out the original project here: [ST7302-for-micropython](https://github.com/zhcong/ST7302-for-micropython).
