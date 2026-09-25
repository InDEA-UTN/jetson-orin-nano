# Abecedario de Senas LED - lado Jetson - Fase 1: ver la mano
#
# El objetivo de este script es UNO SOLO: confirmar que MediaPipe encuentra una mano en la
# camara de la Jetson y que los 21 landmarks tienen sentido. Todavia no hay letras, ni
# clasificador, ni matriz: eso viene en las fases siguientes (ver ../README.md).
#
# Necesita, con el venv del proyecto del espejo ya activado (source ~/espejo_facial_venv/bin/activate),
# el modelo de manos descargado:
#   wget -O ~/hand_landmarker.task \
#     https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
#
# Se corre por SSH sin monitor: toda la salida es texto en la terminal.

import time

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODELO = '/home/indea/hand_landmarker.task'

# Los 21 landmarks de la mano van en este orden fijo:
#   0 muneca | 1-4 pulgar | 5-8 indice | 9-12 medio | 13-16 anular | 17-20 menique
# Dentro de cada dedo el orden va de la base a la punta, asi que las PUNTAS son los ultimos
# de cada grupo. Son los que se imprimen aca porque son los que mas se mueven y hacen mas
# facil ver a ojo si el seguimiento esta bien.
PUNTAS = {"pulgar": 4, "indice": 8, "medio": 12, "anular": 16, "menique": 20}

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODELO),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    # Casi siempre es otro proceso que quedo con la camara tomada (ojo con Ctrl+Z, que
    # suspende en vez de cerrar). Se limpia con:  pkill -f probar_manos
    raise SystemExit(
        "No se pudo abrir la camara (/dev/video0). Suele ser otro proceso que la tiene "
        "ocupada: revisalo con 'ps aux | grep -E \"probar_manos|jetson_face\" | grep -v grep'")

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print("Camara abierta. Mostrale una mano - Ctrl+C para cortar")

habia_mano = False
ultimo_print = 0.0
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
            if habia_mano:
                print("-- se perdio la mano --")
                habia_mano = False
            continue

        if not habia_mano:
            print("-- mano detectada --")
            habia_mano = True

        # Se imprime una vez por segundo y no en cada frame: a 30 fps la terminal se vuelve
        # ilegible y no se alcanza a leer nada.
        ahora = time.time()
        if ahora - ultimo_print < 1.0:
            continue
        ultimo_print = ahora

        # MediaPipe devuelve dos juegos de coordenadas para la misma mano:
        #   - hand_landmarks: normalizados 0..1 sobre la imagen, sirven para dibujar.
        #   - hand_world_landmarks: en METROS y con el origen en el centro de la mano; son los
        #     que traen profundidad real y los que van a alimentar al clasificador mas
        #     adelante. Por ahora solo se miran para confirmar que llegan.
        lm = resultado.hand_landmarks[0]
        mundo = resultado.hand_world_landmarks[0]
        mano = resultado.handedness[0][0]

        # Ojo: MediaPipe decide "Left"/"Right" asumiendo la imagen espejada (vista tipo
        # selfie) y aca se le pasa el frame crudo de la camara, asi que la etiqueta puede
        # venir al reves de la mano real. No es un error: lo unico que importa despues es que
        # sea consistente.
        print(f"mano={mano.category_name} ({mano.score:.2f})  "
              f"landmarks={len(lm)}  world={len(mundo)}")

        puntas = "  ".join(
            f"{nombre}=({lm[i].x:.2f},{lm[i].y:.2f})" for nombre, i in PUNTAS.items())
        print(f"  muneca=({lm[0].x:.2f},{lm[0].y:.2f})  {puntas}")

except KeyboardInterrupt:
    print("Cortado con Ctrl+C")
finally:
    # En un finally para que la camara se libere tambien si el script muere por un error
    # inesperado, no solo con Ctrl+C.
    cap.release()
    detector.close()
