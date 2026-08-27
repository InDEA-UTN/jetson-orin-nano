# Espejo Facial LED — lado Pico W
# Validado el 2026-08-25 (ver ../lado_pico.md): conecta por WiFi y prende/apaga el LED de a
# bordo al recibir cualquier paquete UDP. Reemplazo provisorio de la matriz MAX7219 (Fase 1-2
# simplificada) mientras no llega el hardware — cuando llegue, cambiar led.toggle() por la
# escritura del framebuffer de 8 bytes vía SPI (protocolo en ../README.md, sección 9).
#
# Necesita wifi_config.py al lado (copiá wifi_config.example.py y completá SSID/PASSWORD;
# no se commitea, ver .gitignore).

import network
import socket
import time
from machine import Pin
from wifi_config import SSID, PASSWORD

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
while not wlan.isconnected():
    time.sleep(0.5)
print("IP:", wlan.ifconfig()[0])

try:
    led = Pin("LED", Pin.OUT)   # Pico W: LED en el chip WiFi (CYW43), no en un GPIO común
except TypeError:
    led = Pin(25, Pin.OUT)      # Pico sin W: GPIO25 directo

PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PORT))
print("Escuchando UDP en el puerto", PORT)

while True:
    data, addr = sock.recvfrom(64)
    print("Paquete de", addr, ":", data)
    led.toggle()
