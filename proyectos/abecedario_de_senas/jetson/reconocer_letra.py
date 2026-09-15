# Abecedario de Senas LED - lado Jetson - Fase 4/8: clasificar letra en vivo
#
# Mismo esqueleto que probar_manos.py (abrir camara, correr el detector), pero en vez de
# imprimir landmarks crudos, calcula el vector normalizado (con manos.py, el mismo codigo que
# usa el entrenamiento) y le pregunta al modelo entrenado (abecedario_modelo.pkl) que letra es.
#
# Corre por SSH sin monitor: no guarda nada en disco (ni imagenes ni video), solo imprime la
# letra reconocida por consola, una vez por segundo.
#
# Antes de correr: necesita, ademas de lo que ya usa probar_manos.py (mediapipe, opencv,
# hand_landmarker.task), tener scikit-learn y joblib instalados EN LA MISMA VERSION con la que
# se genero el .pkl en la PC de escritorio -- ver ../README.md, seccion "Compatibilidad de
# versiones entre la PC y la Jetson". Si no coinciden, joblib.load() puede tirar
# InconsistentVersionWarning (no siempre un error duro, pero sin garantia de resultado correcto).

import time

import cv2
import joblib
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import manos

MODELO_MANOS = '/home/indea/hand_landmarker.task'
MODELO_LETRAS = 'abecedario_modelo.pkl'

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODELO_MANOS),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

modelo = joblib.load(MODELO_LETRAS)  # se carga una sola vez, antes del loop

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    # Casi siempre es otro proceso que quedo con la camara tomada (ojo con Ctrl+Z, que
    # suspende en vez de cerrar). Se limpia con:  pkill -f reconocer_letra
    raise SystemExit(
        "No se pudo abrir la camara (/dev/video0). Suele ser otro proceso que la tiene "
        "ocupada: revisalo con 'ps aux | grep -E \"probar_manos|reconocer_letra\" | grep -v grep'")

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print("Camara abierta. Mostrale una letra - Ctrl+C para cortar")

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
        # ilegible y no se alcanza a leer nada (mismo motivo que en probar_manos.py).
        ahora = time.time()
        if ahora - ultimo_print < 1.0:
            continue
        ultimo_print = ahora

        mundo = resultado.hand_world_landmarks[0]
        mano = resultado.handedness[0][0].category_name

        vector = manos.vector_normalizado(mundo, mano)
        if vector is None:
            # Misma escala degenerada que ya filtraba extraer_landmarks.py durante el
            # entrenamiento: mano demasiado pegada al centro, distancia muneca->nudillo ~0.
            print("  (mano muy cerca del centro, vector degenerado, se salta)")
            continue

        letra = modelo.predict([vector])[0]
        print(f"letra: {letra}")

except KeyboardInterrupt:
    print("Cortado con Ctrl+C")
finally:
    # En un finally para que la camara se libere tambien si el script muere por un error
    # inesperado, no solo con Ctrl+C.
    cap.release()
    detector.close()
