# Prueba standalone del LCD 16x2 con modulo I2C PCF8574 (sin WiFi, sin UDP todavia). Mismo rol
# que demo_cara_feliz.py para la matriz: confirmar cableado y driver antes de meterlo en main.py.
#
# Cableado (I2C1, para no chocar con la matriz que usa GP2/GP3/GP5):
#   GND -> GND (pin 8) | VCC -> VBUS (pin 40, 5V del USB) | SDA -> GP6 (pin 9) | SCL -> GP7 (pin 10)
#
# Necesita lcd_i2c.py guardado en la Pico, al lado de este archivo.
#
# Si se prende la luz pero no se ve texto (o solo una fila de cuadraditos): girar el
# potenciometro azul de atras del modulo, es el contraste.

from machine import Pin, I2C
from lcd_i2c import LcdI2C

i2c = I2C(1, sda=Pin(6), scl=Pin(7))
print("Dispositivos I2C:", [hex(d) for d in i2c.scan()])   # tiene que aparecer 0x27

lcd = LcdI2C(i2c, 0x27)
lcd.linea(0, "Hola")
lcd.linea(1, "Senas + LCD")
