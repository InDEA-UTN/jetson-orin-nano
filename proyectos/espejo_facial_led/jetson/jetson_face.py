# Espejo Facial LED - lado Jetson
# Fase 6 + 7: captura la webcam USB, corre MediaPipe Face Landmarker en vivo, cuantiza los
# gestos a estados discretos (ojos abierto/cerrado por ojo, cejas en 3 posiciones, boca en 4
# formas), compone un sprite de 8x8 y lo manda por UDP a la Pico W, que lo dibuja en la matriz
# MAX7219 (ver ../lado_pico.md seccion 9 y ../lado_jetson.md).
#
# Necesita, con el venv (~/espejo_facial_venv) activado:
#   - mediapipe, opencv (ver ../lado_jetson.md secciones 3 y 5)
#   - el modelo descargado en /home/indea/face_landmarker.task
#   - gestos.py al lado de este archivo (la logica de metricas, estados y sprite)
#
# Al arrancar hace 3 segundos de calibracion: hay que quedarse con CARA NEUTRA mirando a la
# camara mientras dura. Con ese promedio arma los umbrales de esta persona y recien despues
# empieza a reaccionar a los gestos (ver gestos.py). Durante la calibracion la matriz ya
# muestra la cara neutra, asi que se ve que el sistema esta vivo.
#
# IP_PICO es la IP actual de la Pico en la red WiFi (lab-raspi) - cambia entre sesiones
# porque no tiene IP reservada todavia (ver ../lado_pico.md, "Proximos pasos").

import cv2, time, socket
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import gestos

MODEL = '/home/indea/face_landmarker.task'
IP_PICO = "192.168.1.100"
PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1)
detector = vision.FaceLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    # Casi siempre es otro proceso que quedo con la camara tomada (ojo con Ctrl+Z, que
    # suspende en vez de cerrar). Se limpia con:  pkill -f jetson_face ; pkill -f ver_camara
    raise SystemExit(
        "No se pudo abrir la camara (/dev/video0). Suele ser otro proceso que la tiene "
        "ocupada: revisalo con 'ps aux | grep -E \"jetson_face|ver_camara\" | grep -v grep'")

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print("Camara abierta. Mandando a", IP_PICO, "puerto", PORT, "- Ctrl+C para cortar")
print(f"Calibrando {gestos.SEGUNDOS_CALIBRACION:.0f} s: quedate con CARA NEUTRA mirando a la camara...")

analizador = gestos.AnalizadorGestos()
anterior = None
ultimo_restante = None
start = time.time()

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        ts_ms = int((time.time() - start) * 1000)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)
        if not result.face_landmarks:
            continue

        estados = analizador.procesar(result.face_landmarks[0])
        sprite = gestos.construir_sprite(
            estados["ojo_izq"], estados["ojo_der"], estados["cejas"], estados["boca"])
        sock.sendto(gestos.sprite_a_bytes(sprite), (IP_PICO, PORT))

        if estados["calibrando"]:
            # Cuenta regresiva, una linea por segundo entero
            restante = int(estados["restante"]) + 1
            if restante != ultimo_restante:
                print(f"  calibrando... {restante} s (cara neutra)")
                ultimo_restante = restante
            continue

        if ultimo_restante is not None:      # primer frame ya calibrado: se muestra que salio
            print("Calibracion lista. Umbrales de esta cara:")
            print(gestos.resumen_calibracion(estados["base"], estados["umbrales"]))
            ultimo_restante = None

        # Solo se imprime cuando cambia algun estado, para no llenar la consola a 30 por segundo
        actual = (estados["ojo_izq"], estados["ojo_der"], estados["cejas"], estados["boca"])
        if actual != anterior:
            print(f"ojo_izq={actual[0]:<9} ojo_der={actual[1]:<9} "
                  f"cejas={actual[2]:<11} boca={actual[3]}")
            anterior = actual

except KeyboardInterrupt:
    print("Cortado con Ctrl+C")
finally:
    # En un finally para que la camara se libere tambien si el script muere por un error
    # inesperado, no solo con Ctrl+C.
    cap.release()
    detector.close()
