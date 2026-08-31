# Espejo Facial LED — lado Pico W
# Fase 6 (integración): conecta por WiFi, abre un socket UDP y dibuja en la matriz MAX7219 real
# el sprite de 8 bytes recibido en cada paquete (protocolo en ../README.md, sección 9 — byte[fila],
# bit 7 = píxel izquierdo). Reemplaza la versión con el LED de a bordo (fases 1-2 simplificada,
# ver ../lado_pico.md) ahora que la matriz ya está cableada y probada (demo_cara_feliz.py).
#
# Necesita wifi_config.py al lado (copiá wifi_config.example.py y completá SSID/PASSWORD;
# no se commitea, ver .gitignore).

import network
import socket
import time
from machine import Pin, SPI
import max7219
from wifi_config import SSID, PASSWORD

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
while not wlan.isconnected():
    time.sleep(0.5)
print("IP:", wlan.ifconfig()[0])

spi = SPI(0, baudrate=10000000, sck=Pin(2), mosi=Pin(3))
cs = Pin(5, Pin.OUT)
display = max7219.Matrix8x8(spi, cs, 1)
display.brightness(2)

PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PORT))
print("Escuchando UDP en el puerto", PORT)

while True:
    data, addr = sock.recvfrom(64)
    if len(data) != 8:
        print("Paquete de", addr, "ignorado (esperaba 8 bytes, llegaron", len(data), ")")
        continue
    print("Sprite de", addr, ":", data)
    display.fill(0)
    for fila in range(8):
        byte_fila = data[fila]
        for columna in range(8):
            if byte_fila & (1 << (7 - columna)):
                display.pixel(columna, fila, 1)
    display.show()
