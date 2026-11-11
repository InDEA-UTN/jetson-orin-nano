# Espejo Facial LED — lado Pico W
# Fase 6 (integración): conecta por WiFi, abre un socket UDP y dibuja en la matriz MAX7219 real
# el sprite de 8 bytes recibido en cada paquete (protocolo en ../README.md, sección 9 — byte[fila],
# bit 7 = píxel izquierdo). Reemplaza la versión con el LED de a bordo (fases 1-2 simplificada,
# ver ../lado_pico.md) ahora que la matriz ya está cableada y probada (demo_cara_feliz.py).
#
# Ademas maneja un LCD 16x2 por I2C si esta conectado (extension del abecedario de senas, ver
# ../../abecedario_de_senas/extension_lcd/README.md): un segundo tipo de paquete, de 33 bytes
# ('L' + linea 1 + linea 2), con el texto ya armado por la Jetson. Si el LCD no esta, todo lo
# demas anda igual -- el espejo facial no lo usa.
#
# Necesita wifi_config.py al lado (copiá wifi_config.example.py y completá SSID/PASSWORD;
# no se commitea, ver .gitignore). Para el LCD, ademas, lcd_i2c.py (de la carpeta extension_lcd)
# guardado en la Pico -- es opcional: sin el, se sigue solo con la matriz.

import network
import socket
import time
from machine import Pin, SPI, I2C
import max7219
from wifi_config import SSID, PASSWORD

# lcd_i2c.py es de otro proyecto (abecedario de senas): si no esta guardado en la Pico, se sigue
# sin LCD en vez de morir con ImportError -- el espejo facial no lo necesita.
try:
    from lcd_i2c import LcdI2C
except ImportError:
    LcdI2C = None

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
    """Bloquea hasta conectar, reintentando cada TIMEOUT_CONEXION segundos. Mientras espera
    imprime wlan.status() una vez por segundo, para que se vea por que no conecta (por ejemplo
    -2 = no encuentra la red: el hotspot no esta levantado). Es la version con timeout armada en
    lado_pico.md seccion 4. Se usa al arrancar y tambien para reconectar si el wifi se cae a mitad
    de sesion (ver el loop principal, mas abajo)."""
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

# I2C1 en GP6/GP7: la matriz ya ocupa GP2/GP3/GP5. Se busca el LCD en vez de asumirlo: sin el,
# LcdI2C() tiraria error al primer envio y mataria el script, y el espejo facial no lo tiene.
i2c = I2C(1, sda=Pin(6), scl=Pin(7))
if LcdI2C is None:
    lcd = None
    print("Sin lcd_i2c.py en la Pico - sigo solo con la matriz")
elif 0x27 in i2c.scan():
    lcd = LcdI2C(i2c, 0x27)
    lcd.linea(0, "Esperando...")
    print("LCD encontrado en 0x27")
else:
    lcd = None
    print("Sin LCD (no responde en 0x27) - sigo solo con la matriz")

PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PORT))
print("Escuchando UDP en el puerto", PORT)

# El ultimo paquete de cada tipo: la Jetson manda los dos en cada frame (~30 por segundo), casi
# siempre iguales al anterior. Se usan para imprimir solo cuando algo cambia (si no, la consola
# de Thonny se llena de 60 lineas por segundo) y para no reescribir el LCD sin necesidad --
# escribir 32 caracteres por I2C tarda ~15 ms, y mientras tanto no se atienden paquetes.
ultimo_sprite = None
ultimo_texto = None

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
    # Se mira el LARGO primero: un sprite tambien puede empezar con el byte 'L' (0x4C = la fila
    # 01001100), asi que la 'L' sola no alcanza para reconocer un paquete de texto.
    if len(data) == 33 and data[0] == ord('L'):
        if lcd is not None and data != ultimo_texto:
            # chr() byte por byte en vez de .decode(): con un paquete con bytes raros, decode()
            # tiraria error y mataria el script; asi, lcd_i2c los muestra como '?'.
            texto = "".join(chr(b) for b in data[1:])
            # Mismo criterio que el try de recvfrom: un error de I2C a mitad de sesion (un cable
            # flojo) no tiene que matar el script y dejar la matriz congelada. Se marca el texto
            # como escrito igual, para no imprimir el error 30 veces por segundo: se vuelve a
            # intentar con el proximo texto distinto.
            try:
                lcd.linea(0, texto[:16])
                lcd.linea(1, texto[16:])
                print("Texto de", addr, ":", texto)
            except OSError as e:
                print("Error escribiendo en el LCD:", e, "- revisar cables SDA/SCL")
            ultimo_texto = data
        continue
    if len(data) != 8:
        print("Paquete de", addr, "ignorado (esperaba 8 o 33 bytes, llegaron", len(data), ")")
        continue
    if data != ultimo_sprite:
        print("Sprite de", addr, ":", data)
        ultimo_sprite = data
    display.fill(0)
    for fila in range(8):
        byte_fila = data[fila]
        for columna in range(8):
            if byte_fila & (1 << (7 - columna)):
                display.pixel(columna, fila, 1)
    display.show()
