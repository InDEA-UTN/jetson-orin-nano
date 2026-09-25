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

TIMEOUT_CONEXION = 15  # segundos por intento

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
# Antes de connect(), con el radio recien activado: aplicado despues de conectar, el ioctl
# competia con la propia negociacion wifi todavia en curso y tiraba timeout sin aplicarse de
# verdad (se vio "[CYW43] do_ioctl(...) timeout" en la consola). Sin esto, el chip entra en modo
# ahorro de energia apenas queda un rato sin mandar trafico saliente, y pierde paquetes UDP
# entrantes (o hasta un ping) hasta que se despierta en su proximo ciclo -- grave para este
# script porque solo RECIBE, nunca manda nada por su cuenta.
wlan.config(pm=0xa11140)


def conectar_wifi():
    """Bloquea hasta conectar. Sin timeout ni diagnostico, si la contrasena esta mal o el
    hotspot no esta levantado la Pico se queda colgada sin ninguna pista de que esta atascado.
    Version con timeout + status ya armada y documentada en lado_pico.md seccion 4 (se uso ahi
    para diagnosticar este mismo tipo de problema durante las pruebas) -- llevada aca al script
    final. Se reusa tambien para reconectar si el wifi se cae a mitad de sesion (ver el loop
    principal, mas abajo)."""
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        t0 = time.time()
        while not wlan.isconnected() and time.time() - t0 < TIMEOUT_CONEXION:
            print("Conectando a wifi... status:", wlan.status())
            time.sleep(1)
        if not wlan.isconnected():
            print("No conecto en", TIMEOUT_CONEXION, "s (status:", wlan.status(), "). Reintentando...")
            wlan.connect(SSID, PASSWORD)
    print("IP:", wlan.ifconfig()[0])


conectar_wifi()

spi = SPI(0, baudrate=10000000, sck=Pin(2), mosi=Pin(3))
cs = Pin(5, Pin.OUT)
display = max7219.Matrix8x8(spi, cs, 1)
display.brightness(2)

PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PORT))
print("Escuchando UDP en el puerto", PORT)

while True:
    try:
        data, addr = sock.recvfrom(64)
    except OSError as e:
        # Sin este try/except, un corte de WiFi a mitad de sesion tiraba un OSError sin manejar
        # y mataba el script entero -- habia que ir hasta la Pico y hacerle un power-cycle manual
        # para que volviera a andar. Ahora se detecta solo y se reconecta.
        print("Error de socket:", e, "- wifi conectado:", wlan.isconnected())
        if not wlan.isconnected():
            conectar_wifi()
        continue
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
