# Abecedario de Senas LED - entrenamiento: paso 1, extraer landmarks del dataset
#
# Recorre las carpetas del dataset de Kaggle "ASL Alphabet" (una carpeta por letra, con miles
# de fotos adentro) y para cada foto calcula el vector normalizado de 63 numeros (ver
# ../jetson/manos.py). El resultado es un archivo .npz con todos los vectores y su letra --
# eso es lo liviano que despues entrena el clasificador (entrenar.py) y lo unico que hace falta
# mirar para saber si el dataset quedo bien armado.
#
# Corre en una PC de escritorio, no en la Jetson: no necesita camara, solo lee fotos del disco.
#
# Antes de correr:
#   python3 -m venv entrenamiento_venv && source entrenamiento_venv/bin/activate
#   pip install mediapipe opencv-python-headless numpy scikit-learn joblib
#   wget -O hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
#   (bajar y descomprimir el dataset de Kaggle "ASL Alphabet" en dataset_kaggle/, al lado de
#   esta carpeta -- queda dataset_kaggle/asl_alphabet_train/asl_alphabet_train/<letra>/*.jpg)

import os
import random
import sys
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "jetson"))
import manos

RAIZ = os.path.join(os.path.dirname(__file__), "..")
DATASET = os.path.join(RAIZ, "dataset_kaggle", "asl_alphabet_train", "asl_alphabet_train")
MODELO_MEDIAPIPE = os.path.join(RAIZ, "hand_landmarker.task")
SALIDA = os.path.join(RAIZ, "dataset_landmarks.npz")

# Cuantas fotos tomar de cada letra (hay 3000 en el dataset). Un numero chico alcanza para un
# primer modelo y para confirmar que toda la cadena funciona; se puede subir despues sin tocar
# nada mas que este numero.
MUESTRAS_POR_LETRA = 300

random.seed(42)  # para que elegir "300 al azar" de cada carpeta de resultado igual entre corridas

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODELO_MEDIAPIPE),
    running_mode=vision.RunningMode.IMAGE,
    num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

X, y = [], []
inicio = time.time()

for letra in manos.LETRAS:
    carpeta = os.path.join(DATASET, letra)
    if not os.path.isdir(carpeta):
        print(f"AVISO: no existe la carpeta de la letra {letra} ({carpeta}), se salta")
        continue

    archivos = os.listdir(carpeta)
    random.shuffle(archivos)
    archivos = archivos[:MUESTRAS_POR_LETRA]

    procesadas, detectadas, degeneradas = 0, 0, 0
    for nombre in archivos:
        imagen = cv2.imread(os.path.join(carpeta, nombre))
        if imagen is None:
            continue
        procesadas += 1
        rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
        resultado = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))

        if not resultado.hand_landmarks:
            continue
        detectadas += 1

        mundo = resultado.hand_world_landmarks[0]
        mano = resultado.handedness[0][0].category_name
        vector = manos.vector_normalizado(mundo, mano)
        if vector is None:
            degeneradas += 1
            continue

        X.append(vector)
        y.append(letra)

    print(f"{letra}: {procesadas} fotos -> mano detectada en {detectadas} "
          f"({degeneradas} descartadas por escala degenerada)")

manos.guardar_dataset(SALIDA, X, y)
print(f"\nListo en {time.time() - inicio:.0f}s. Guardado en {SALIDA}")
print(manos.resumen_dataset(np.asarray(y)))
