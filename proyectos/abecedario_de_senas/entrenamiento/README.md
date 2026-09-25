# Entrenamiento — abecedario de señas

Esta carpeta tiene los dos scripts que se corren **una sola vez, en una PC de escritorio** (no en
la Jetson: no usan cámara, solo procesan fotos de un dataset) para producir el modelo entrenado
que después clasifica letras en vivo en la Jetson (`../jetson/reconocer_letra.py`).

Para el porqué de cada decisión (por qué un clasificador y no reglas, de dónde salen los 63
números, por qué KNN, los resultados completos del entrenamiento y la trampa de versiones entre
la PC y la Jetson) ver el **[README principal del proyecto](../README.md)** — este archivo es
solo la guía práctica de esta carpeta puntual.

## Los dos scripts, en orden

### 1. `extraer_landmarks.py`

Recorre las 28 carpetas del dataset de Kaggle "ASL Alphabet" que están listadas en
`manos.LETRAS` (las 26 letras más `del` y `space`; `nothing` queda afuera porque no hay mano que
detectar), toma una muestra de fotos
de cada una (300 por etiqueta por defecto, constante `MUESTRAS_POR_LETRA`), le corre `HandLandmarker`
de MediaPipe a cada foto, y convierte la mano detectada en un vector normalizado de 63 números
(usando `../jetson/manos.py`, compartido con el reconocimiento en vivo). Guarda todos los vectores
válidos junto con su letra en `../dataset_landmarks.npz`.

Es el paso que traduce "fotos" a "algo que un clasificador puede comparar" — sin esto no hay nada
para entrenar.

### 2. `entrenar.py`

Carga `dataset_landmarks.npz`, separa al azar un 20% de los vectores que el modelo nunca ve
durante el entrenamiento (`train_test_split(..., stratify=y)`), entrena un clasificador KNN
(K=5) con el 80% restante, y mide la precisión preguntando ese 20% apartado — la única forma
honesta de saber si generaliza en vez de haber memorizado las respuestas. Imprime el
`classification_report` (precisión y recall por letra) y guarda el modelo en
`../abecedario_modelo.pkl`, que es el único archivo que después se copia a la Jetson.

## Cómo correrlos

Con el venv de este proyecto ya armado (ver "Notas del entorno" en el README principal):

```bash
cd proyectos/abecedario_de_senas
source entrenamiento_venv/bin/activate

python3 entrenamiento/extraer_landmarks.py   # tarda unos minutos, procesa miles de fotos
python3 entrenamiento/entrenar.py            # rápido, solo opera sobre los vectores ya calculados
```

`extraer_landmarks.py` solo hace falta volver a correrlo si cambia el dataset o
`MUESTRAS_POR_LETRA`. Si lo único que cambia es algo del entrenamiento (por ejemplo la versión de
scikit-learn, ver el README principal), alcanza con volver a correr `entrenar.py` — el `.npz` ya
generado se reusa tal cual.

## Qué no vive acá

El dataset de Kaggle (`../dataset_kaggle/`, ~1.2 GB) y los archivos generados
(`dataset_landmarks.npz`, `entrenamiento_venv/`) están excluidos de git por pesados — se
regeneran corriendo estos scripts, no se versionan. Lo único que sí se sube al repo es el
`abecedario_modelo.pkl` resultante (chico, ~1 MB) y estos dos scripts `.py`.
