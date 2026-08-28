# Prueba standalone de la matriz MAX7219 real (sin WiFi, sin UDP todavia).
# Dibuja una carita feliz pixel por pixel, con el mismo formato de 8 filas de 8
# caracteres ('1'/'0') que se usa para los sprites del lado Jetson (ver
# ../lado_jetson.md seccion 7) -- pensado para poder copiar patrones entre los dos
# lados sin inventar una representacion nueva.
#
# Cableado usado (lado IN de la matriz, ver ../README.md seccion 7):
#   DIN -> GP3 (SPI0 MOSI) | CLK -> GP2 (SPI0 SCK) | CS -> GP5

from machine import Pin, SPI
import max7219

spi = SPI(0, baudrate=10000000, sck=Pin(2), mosi=Pin(3))
cs = Pin(5, Pin.OUT)
display = max7219.Matrix8x8(spi, cs, 1)
display.brightness(2)

CARA_FELIZ = [
    "00000000",
    "00100100",   # ojos
    "00100100",
    "00000000",
    "01000010",   # boca: puntas arriba...
    "00100100",   # ...bajando hacia el centro...
    "00011000",   # ...punto mas bajo, forma de sonrisa
    "00000000",
]

display.fill(0)
for y in range(8):
    for x in range(8):
        if CARA_FELIZ[y][x] == '1':
            display.pixel(x, y, 1)
display.show()
