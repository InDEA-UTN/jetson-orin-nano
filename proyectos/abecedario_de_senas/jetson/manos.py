# Abecedario de Senas LED - logica compartida de manos
#
# La usan tanto el entrenamiento (proyecto/entrenamiento/, corre en una PC de escritorio, sobre
# el dataset de fotos) como el reconocimiento en vivo en la Jetson: TIENE que ser el mismo
# codigo en los dos lados, porque el modelo solo funciona si el vector que recibe en vivo se
# calculo exactamente igual que los vectores con los que se entreno.
#
# Ver ../README.md para el resto del plan.

import numpy as np

# --- Indices de los 21 landmarks que devuelve MediaPipe Hands ---
# 0 muneca | 1-4 pulgar | 5-8 indice | 9-12 medio | 13-16 anular | 17-20 menique
MUNECA = 0
NUDILLO_MEDIO = 9

# --- Que letras se reconocen ---
# ASL tiene 26 letras, pero J y Z se hacen con MOVIMIENTO (se dibuja la letra en el aire) y este
# sistema clasifica una foto/frame quieto por vez: un solo frame no alcanza para distinguirlas.
# Quedan afuera a proposito (ver ../README.md). Coincide con los nombres de carpeta del dataset
# de Kaggle, salvo 'del'/'nothing'/'space', que tampoco son letras y no se usan.
LETRAS = tuple("ABCDEFGHIKLMNOPQRSTUVWXY")


def vector_normalizado(world_landmarks, mano):
    """Convierte los 21 landmarks 3D de una mano (en metros, con origen en el centro de la
    mano -- los `hand_world_landmarks` de MediaPipe, no los normalizados 0..1 de la imagen) en
    el vector de 63 numeros que come el clasificador. Devuelve None si la mano salio degenerada
    (escala ~0, landmarks todos pegados).

    Por que world_landmarks y no los 2D: traen la profundidad relativa real de cada dedo, y en
    ASL hay letras que solo se distinguen por eso (en M, N y T el pulgar queda por delante o por
    detras de los otros dedos; en una foto 2D esas tres se ven casi iguales).

    Tres pasos, los mismos para el dataset de fotos y para la camara en vivo:
      1. Si es mano izquierda se espeja (se invierte x), para que una misma letra hecha con
         cualquiera de las dos manos caiga en el mismo lugar y no haga falta el doble de fotos.
      2. Se traslada el origen a la muneca (landmark 0), para que no importe donde este la mano.
      3. Se divide todo por la distancia muneca -> nudillo del dedo medio (landmark 9), para que
         no importe el tamano de la mano ni la distancia a la camara.

    A proposito NO se normaliza la ROTACION: en ASL la orientacion es parte de la letra (G y Q
    son la misma forma de dedos apuntando en distinta direccion). El precio es que hay que
    senar mas o menos de frente a la camara, que es como se dactilologa igual.
    """
    p = np.array([[lm.x, lm.y, lm.z] for lm in world_landmarks], dtype=np.float32)

    if mano == "Left":
        p[:, 0] = -p[:, 0]

    p = p - p[MUNECA]
    escala = float(np.linalg.norm(p[NUDILLO_MEDIO]))
    if escala < 1e-6:
        return None
    return (p / escala).reshape(-1)


def guardar_dataset(ruta, X, y):
    """X: (N, 63) float32, un vector normalizado por muestra. y: (N,) con la letra de cada una."""
    np.savez(ruta, X=np.asarray(X, dtype=np.float32), y=np.asarray(y, dtype="<U1"))


def cargar_dataset(ruta):
    d = np.load(ruta)
    return d["X"].astype(np.float32), d["y"]


def resumen_dataset(y):
    """Texto con cuantas muestras hay de cada letra y cuales faltan, para pegar en la consola."""
    lineas = []
    for letra in LETRAS:
        n = int(np.count_nonzero(y == letra))
        lineas.append(f"{letra}:{n:<5}")
    salida = ["  " + "".join(lineas[i:i + 8]) for i in range(0, len(lineas), 8)]
    salida.append(f"  total: {len(y)} muestras")
    return "\n".join(salida)
