# Abecedario de Senas LED - entrenamiento: paso 2, entrenar el clasificador
#
# Toma el dataset_landmarks.npz que armo extraer_landmarks.py (vectores normalizados + letra) y
# entrena un clasificador de vecinos mas cercanos (KNN): no hay "aprendizaje" complejo, guarda
# el dataset entero y en cada prediccion mide distancia a todas las muestras. Es liviano,
# rapido, y tiene la ventaja de que siempre se puede ver A QUE muestra se parecio una prediccion
# -- misma filosofia que gestos.py del proyecto del espejo facial, pero para clasificar en vez
# de medir umbrales.
#
# Corre en la misma PC que extraer_landmarks.py, con el mismo venv.

import os
import sys

import joblib
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "jetson"))
import manos

RAIZ = os.path.join(os.path.dirname(__file__), "..")
DATASET = os.path.join(RAIZ, "dataset_landmarks.npz")
SALIDA_MODELO = os.path.join(RAIZ, "abecedario_modelo.pkl")

K_VECINOS = 5

X, y = manos.cargar_dataset(DATASET)
print(f"Dataset cargado: {len(y)} muestras")
print(manos.resumen_dataset(y))

# 80/20: se separa una porcion que el modelo NUNCA ve durante el entrenamiento, para medir que
# tan bien generaliza a fotos nuevas (aunque sean fotos del mismo dataset -- ver el aviso abajo).
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

modelo = KNeighborsClassifier(n_neighbors=K_VECINOS, weights="distance")
modelo.fit(X_train, y_train)

precision = modelo.score(X_test, y_test)
print(f"\nPrecision sobre el 20% separado: {precision:.2%}")
print(classification_report(y_test, modelo.predict(X_test)))

# AVISO IMPORTANTE: este numero mide que tan bien predice sobre MAS FOTOS DEL MISMO DATASET DE
# KAGGLE (mismo tipo de fondo, misma distancia a camara, mismo estudio fotografico). No dice
# nada sobre como le va con la camara real de la Jetson, en el laboratorio -- eso solo se sabe
# probandolo en vivo (../jetson/, fase siguiente).

joblib.dump(modelo, SALIDA_MODELO)
print(f"\nModelo guardado en {SALIDA_MODELO}")
