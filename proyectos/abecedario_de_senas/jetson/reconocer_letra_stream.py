# Abecedario de Senas LED - lado Jetson - variante de reconocer_letra.py para ver el video SIN
# monitor conectado a la Jetson.
#
# reconocer_letra.py usa cv2.imshow, que necesita una sesion grafica local (DISPLAY seteado) en la
# propia Jetson. Este script hace exactamente la misma clasificacion y el mismo estabilizador
# temporal (ver ese archivo para el porque de cada pieza), pero en vez de abrir una ventana local,
# codifica cada frame ya anotado como JPEG y lo sirve por HTTP en 127.0.0.1 -- solo alcanzable
# desde la propia Jetson.
#
# Para verlo desde la PC hay que abrir un tunel SSH que "estira" ese puerto hasta la PC:
#
#   ssh -L 8000:localhost:8000 <usuario>@<ip-jetson>
#
# y con ese tunel abierto (puede ser una segunda sesion SSH, no hace falta usar esa para nada mas)
# abrir http://localhost:8000/ en un navegador de la PC. El trafico viaja adentro del tunel SSH ya
# cifrado, asi que no hace falta abrir ningun puerto en la red ni exponer la camara a nadie mas.
#
# Antes de correr: mismos requisitos que reconocer_letra.py (mediapipe, opencv, hand_landmarker.task,
# scikit-learn/joblib en la misma version que se uso para generar el .pkl). Ver ../README.md.
#
# Paso 7: ademas manda por UDP a la Pico el sprite de la letra CONFIRMADA (nunca la cruda, para
# no titilar la matriz) -- ver enviar_a_matriz() y letras_matriz.py. Antes de correr esto, probar
# el camino de red aislado con probar_matriz.py (sin camara ni modelo de por medio).

import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import joblib
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import letras_matriz
import manos

MODELO_MANOS = '/home/indea/hand_landmarker.task'
# Absoluto, no solo el nombre del archivo: relativo dependia de desde que directorio se
# corriera el script, y joblib.load() fallaba si se corria desde otro lado aunque el .pkl
# estuviera al lado de este archivo. Se resuelve contra la ubicacion de este mismo script, no
# contra un directorio fijo, para no romper si se mueve la carpeta del proyecto entero.
MODELO_LETRAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'abecedario_modelo.pkl')

# Solo localhost: el puerto no se expone a la red, se llega a el a traves del tunel SSH.
HOST = '127.0.0.1'
PUERTO = 8000

# Misma IP/puerto que probar_matriz.py -- la asigna el DHCP del hotspot de la Jetson y puede
# cambiar entre sesiones (ver ../../espejo_facial_led/integracion.md, seccion 11).
IP_PICO = "10.42.0.170"
PORT_PICO = 5005

# La matriz queda reservada para el espejo facial: con los dos proyectos corriendo a la vez contra
# la misma Pico, si los dos le mandaran sprites la matriz titilaria entre la cara y la letra. Las
# senas se muestran solo en el LCD. En True vuelve a mandar la letra a la matriz (para mostrar
# este proyecto solo, sin el espejo facial).
MANDAR_A_MATRIZ = False

# La webcam USB por su nombre fijo, no por numero: con la camara CSI conectada (la usa el espejo
# facial), la CSI se queda con /dev/video0 y la webcam pasa a /dev/video1 -- y ese orden puede
# cambiar al reiniciar o reconectar. Abrir video0 a ciegas daria la imagen verde cruda de la CSI.
# El nombre sale de 'ls -l /dev/v4l/by-id/' (index0 es el nodo de video; index1 son metadatos).
CAMARA = "/dev/v4l/by-id/usb-SN0002_1080P_Web_Camera_SN0002-video-index0"

UMBRAL_ESTABLE = 8
UMBRAL_REPETICION = 16
UMBRAL_SIN_MANO = 10


class EstabilizadorLetra:
    """Filtra el ruido frame a frame del detector y decide QUE ESCRIBIR en cada frame.
    Ver reconocer_letra.py para la explicacion completa de las tres reglas -- es la misma clase."""

    def __init__(self, umbral=UMBRAL_ESTABLE, repeticion=UMBRAL_REPETICION,
                 umbral_sin_mano=UMBRAL_SIN_MANO):
        self.umbral = umbral
        self.repeticion = repeticion
        self.umbral_sin_mano = umbral_sin_mano
        self.candidata = None
        self.repeticiones = 0
        self.sin_mano = 0
        self.confirmada = None

    def procesar(self, letra_cruda):
        if letra_cruda is None:
            self.candidata = None
            self.repeticiones = 0
            self.sin_mano += 1
            if self.sin_mano >= self.umbral_sin_mano:
                self.confirmada = None
            return None

        self.sin_mano = 0
        if letra_cruda == self.candidata:
            self.repeticiones += 1
        else:
            self.candidata = letra_cruda
            self.repeticiones = 1

        if self.repeticiones == self.umbral:
            if self.candidata != self.confirmada:
                self.confirmada = self.candidata
                return self.candidata
            return None

        if (self.repeticiones > self.umbral
                and (self.repeticiones - self.umbral) % self.repeticion == 0):
            return self.candidata

        return None

    def faltan(self):
        if self.candidata is None:
            return None
        if self.repeticiones < self.umbral:
            return self.umbral - self.repeticiones
        return self.repeticion - ((self.repeticiones - self.umbral) % self.repeticion)


def aplicar_al_texto(texto, etiqueta):
    if etiqueta == "space":
        return texto + " "
    if etiqueta == "del":
        return texto[:-1]
    return texto + etiqueta


def mostrar_texto(texto):
    print(f"\rTexto: {texto:<60}", end="", flush=True)


def texto_con_borde(frame, texto, y, color=(0, 255, 0)):
    cv2.putText(frame, texto, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
    cv2.putText(frame, texto, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)


def enviar_a_matriz(letra):
    # 'del', 'space' y sin mano (letra=None) no tienen sprite a proposito -- ver letras_matriz.py:
    # la decision fue que la matriz se apague en esos tres casos. Se manda SIEMPRE, en cada frame,
    # no solo cuando la letra cambia: UDP puede perder un paquete en silencio, y si solo mandaramos
    # los cambios, un paquete perdido dejaria la matriz mostrando la letra vieja para siempre. Al
    # mandar siempre, el sistema se auto-corrige en el proximo frame (33 ms despues).
    if not MANDAR_A_MATRIZ:
        return
    if letra in letras_matriz.FUENTE:
        sprite = letras_matriz.sprite_de_letra(letra)
    else:
        sprite = ["0" * 8] * 8
    sock_pico.sendto(letras_matriz.sprite_a_bytes(sprite), (IP_PICO, PORT_PICO))


def enviar_a_lcd(texto, confirmada, faltan):
    # Paquete de 33 bytes para el LCD 16x2 de la Pico: 'L' + linea 1 + linea 2, cada linea
    # rellenada con espacios a 16 (ver ../LCD extension/README.md). Se manda la pantalla entera en
    # cada frame, igual que la matriz: un paquete perdido se corrige solo con el siguiente. Va al
    # mismo socket/IP/puerto que la matriz -- la Pico los distingue por el largo.
    linea1 = texto[-16:]            # los ultimos 16: el texto se corre a la izquierda al crecer
    linea2 = f"Letra: {confirmada or '-':<5} {faltan if faltan is not None else '-':>3}"
    paquete = b"L" + linea1.ljust(16).encode() + linea2.ljust(16).encode()
    sock_pico.sendto(paquete, (IP_PICO, PORT_PICO))


sock_pico = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Frame ya anotado, listo para servir, codificado a JPEG por el loop principal. El lock evita que
# el hilo del servidor lea un frame a medio escribir mientras el loop principal lo reemplaza.
frame_lock = threading.Lock()
ultimo_jpeg = None

PAGINA = (b"<html><body style='margin:0;background:#000'>"
          b"<img src='/stream' style='width:100%'></body></html>")


class ManejadorMJPEG(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        pass  # sin esto, cada frame pedido por el navegador ensucia la consola con un log

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(PAGINA)))
            self.end_headers()
            self.wfile.write(PAGINA)
            return
        if self.path != '/stream':
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        try:
            while True:
                with frame_lock:
                    jpeg = ultimo_jpeg
                if jpeg is None:
                    time.sleep(0.05)
                    continue
                self.wfile.write(b'--frame\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                self.wfile.write(f'Content-Length: {len(jpeg)}\r\n\r\n'.encode())
                self.wfile.write(jpeg)
                self.wfile.write(b'\r\n')
                time.sleep(0.03)
        except (BrokenPipeError, ConnectionResetError):
            pass  # el navegador cerro la pestana o se corto el tunel


servidor = ThreadingHTTPServer((HOST, PUERTO), ManejadorMJPEG)
hilo_servidor = threading.Thread(target=servidor.serve_forever, daemon=True)
hilo_servidor.start()

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODELO_MANOS),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

modelo = joblib.load(MODELO_LETRAS)
estabilizador = EstabilizadorLetra()

# CAP_V4L2 explicito: con un texto en vez de un numero, OpenCV si no lo trataria como un archivo
# de video o un pipeline de GStreamer.
cap = cv2.VideoCapture(CAMARA, cv2.CAP_V4L2)
if not cap.isOpened():
    raise SystemExit(
        f"No se pudo abrir la webcam ({CAMARA}). Revisar que este enchufada "
        "('ls /dev/v4l/by-id/') y que no la tenga otro proceso: "
        "'ps aux | grep -E \"probar_manos|reconocer_letra\" | grep -v grep'")

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print(f"Servidor de video en http://{HOST}:{PUERTO}/ (solo alcanzable con un tunel SSH, ver "
      f"el comentario al principio del archivo).")
print(f"Mandando a la matriz en {IP_PICO}:{PORT_PICO}. Ctrl+C en esta consola para cortar.\n")

texto = ""
inicio = time.time()

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        ts_ms = int((time.time() - inicio) * 1000)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = detector.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)

        if not resultado.hand_landmarks:
            estabilizador.procesar(None)
            texto_con_borde(frame, "Mano: no detectada", 30, (0, 0, 255))
            texto_con_borde(frame, f"Texto: {texto[-30:]}", 80, (255, 255, 0))
        else:
            lm = resultado.hand_landmarks[0]
            h, w = frame.shape[:2]
            for p in lm:
                cv2.circle(frame, (int(p.x * w), int(p.y * h)), 3, (0, 255, 0), -1)

            mundo = resultado.hand_world_landmarks[0]
            mano = resultado.handedness[0][0].category_name

            vector = manos.vector_normalizado(mundo, mano)
            if vector is None:
                letra_cruda = None
                texto_con_borde(frame, "Mano detectada, vector degenerado", 30, (0, 165, 255))
            else:
                letra_cruda = modelo.predict([vector])[0]
                texto_con_borde(frame, f"Letra cruda (este frame): {letra_cruda}", 30)

            a_escribir = estabilizador.procesar(letra_cruda)
            if a_escribir is not None:
                texto = aplicar_al_texto(texto, a_escribir)
                mostrar_texto(texto)

            confirmada = estabilizador.confirmada
            faltan = estabilizador.faltan()
            color_confirmada = (0, 255, 0) if confirmada == letra_cruda else (200, 200, 200)
            texto_con_borde(
                frame,
                f"Letra confirmada: {confirmada or '-'}  "
                f"(escribe en {faltan if faltan is not None else '-'})",
                55, color_confirmada)
            texto_con_borde(frame, f"Texto: {texto[-30:]}", 80, (255, 255, 0))

        enviar_a_matriz(estabilizador.confirmada)
        enviar_a_lcd(texto, estabilizador.confirmada, estabilizador.faltan())

        # Calidad 70 en vez de la maxima por defecto: bastante mas liviano para viajar por el
        # tunel SSH sin perderse detalle util para ver la mano y leer el texto superpuesto.
        ok_jpeg, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok_jpeg:
            with frame_lock:
                ultimo_jpeg = buffer.tobytes()

except KeyboardInterrupt:
    pass
finally:
    print(f"\nTexto final: {texto!r}")
    cap.release()
    servidor.shutdown()
    detector.close()
