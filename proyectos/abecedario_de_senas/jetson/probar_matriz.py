# Abecedario de Senas LED - Paso 7 (parte 1): probar el envio UDP a la Pico, SIN camara ni
# clasificador de por medio.
#
# Aisla la variable de red/protocolo de la variable de reconocimiento: si la letra no aparece
# bien en la matriz, el problema esta en la IP, el protocolo o el sprite -- no en mediapipe ni en
# el modelo. Mismo criterio que se uso para probar joblib.load() aislado antes de la prueba en
# vivo del reconocedor (ver ../README.md).
#
# Manda el sprite de UNA letra repetido cada 0.5s hasta Ctrl+C, no una vez sola: UDP puede perder
# un paquete en silencio, y un solo intento perdido haria parecer que el sprite esta mal cuando en
# realidad se perdio en el camino.
#
# IP_PICO es la que asigna el DHCP del hotspot de la Jetson (ver ../../espejo_facial_led/
# integracion.md, seccion 11) -- confirmala en la consola de Thonny si dejo de andar, puede
# cambiar entre sesiones.
#
# Uso: python3 probar_matriz.py A

import socket
import sys
import time

import letras_matriz

IP_PICO = "10.42.0.170"
PORT = 5005

if len(sys.argv) != 2:
    raise SystemExit("Uso: python3 probar_matriz.py <LETRA>")

letra = sys.argv[1].upper()
sprite = letras_matriz.sprite_de_letra(letra)
paquete = letras_matriz.sprite_a_bytes(sprite)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Mandando '{letra}' a {IP_PICO}:{PORT} cada 0.5s - Ctrl+C para cortar")
try:
    while True:
        sock.sendto(paquete, (IP_PICO, PORT))
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
