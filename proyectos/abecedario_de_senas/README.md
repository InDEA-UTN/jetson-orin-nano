# Abecedario de Señas LED

**Estado.** Al 07/09/2026: la fase 1 (ver la mano) está verificada en la Jetson. El plan original
de usar un modelo pre-entrenado por otra persona se abandonó (motivo abajo, sección "Decisiones")
y se pivotó a entrenar un modelo propio con un dataset público de fotos. **El código de ese
entrenamiento ya está escrito, pero todavía no se corrió ninguna vez** — es lo primero para
retomar, ver "Próximos pasos" al final.

## Objetivo

Traducir el abecedario dactilológico (lenguaje de señas) a letras normales, mostrando cada letra
reconocida en la matriz LED 8×8, con el mismo equipo del proyecto
[`espejo_facial_led/`](../espejo_facial_led/): Jetson Orin Nano (cámara + MediaPipe), Raspberry
Pi Pico W (WiFi + matriz MAX7219), y el mismo protocolo UDP de 8 bytes entre las dos.

Es un proyecto separado del espejo facial porque el problema de fondo es otro: ahí se
cuantizaban gestos de cara con reglas simples sobre 1-2 métricas (EAR, MAR); acá hay que
clasificar 24 poses de mano distintas a partir de 21 puntos cada una, que es un problema de
clasificación, no de umbrales a mano — ver "Por qué un clasificador y no reglas" más abajo.

## Decisiones de alcance ya tomadas

- **Abecedario: ASL (americano), no LSA.** 26 letras. Es el alfabeto con más documentación y
  material de referencia disponible — más fácil de hacer andar bien en una primera versión que
  LSA.
- **V1: solo letras estáticas — 24 de las 26.** Un solo frame de la mano, sin ventana temporal.
  **J y Z quedan afuera**, porque en ASL se hacen dibujando la letra en el aire (movimiento): un
  solo frame no alcanza para distinguirlas. Quedan anotadas como fase futura si se agrega
  reconocimiento de movimiento (una ventana temporal de varios frames en vez de uno solo).

## Por qué un clasificador y no reglas escritas a mano

En el espejo facial cada gesto era una regla simple ("boca abierta si MAR > umbral"), viable con
4-5 gestos. Acá son 24 poses definidas por la posición relativa de 21 puntos (63 números);
escribir 24 reglas que no se pisen entre sí es inviable, y una regla a mano no generaliza bien a
manos de distinto tamaño o ángulo. Un clasificador resuelve eso comparando una mano nueva contra
ejemplos ya etiquetados, en vez de contra umbrales fijos — para eso hace falta un **dataset**:
un conjunto de ejemplos (mano → letra correcta) del que "aprender" comparando.

## Decisiones sobre el clasificador (con el porqué de cada giro)

Este proyecto cambió de plan dos veces sobre cómo conseguir ese dataset, y las dos veces por una
razón concreta encontrada en el camino — vale la pena dejarlas escritas para no repetir el
mismo callejón sin salida:

1. **Plan original: usar un modelo ya entrenado por otra persona** (sin grabar ni entrenar nada
   propio). Se encontró [VivanRajath/ASL](https://github.com/VivanRajath/ASL) en GitHub: Random
   Forest sobre landmarks de MediaPipe, licencia MIT, A-Z sin J/Z.
2. **Se abandonó ese plan** al revisar el repo de cerca: **el modelo entrenado (`asl_model.pkl`)
   no está en el repositorio** — solo están `asl_scaler.pkl`, `asl_label_encoder.pkl` y el código
   para entrenarlo (`train.py`, `data_extractor.py`), pero no el resultado. Sin el modelo en sí,
   "usar uno ya entrenado" ya no era gratis: había que entrenarlo nosotros de todas formas.
3. **Se decidió no reusar tampoco su código de extracción**, aunque igual había que entrenar
   algo: `data_extractor.py` usa `mp.solutions.hands`, la API **vieja** de MediaPipe, que ya no
   existe en la versión moderna instalada en este proyecto (mismo problema ya documentado en
   [`../espejo_facial_led/lado_jetson.md`](../espejo_facial_led/lado_jetson.md), tabla de
   trampas: *"`mp.solutions` no existe — MediaPipe 1.0.1 eliminó la API clásica a favor de la
   API Tasks"*). Había que reescribir la extracción de landmarks de todas formas para usar
   `HandLandmarker` (API Tasks) — y ya que se reescribía esa parte, se decidió aplicar también
   **nuestra propia normalización geométrica** (restar la muñeca, escalar por el tamaño de la
   mano, espejar la mano izquierda — ver `jetson/manos.py` más abajo) en vez de la de ellos, que
   no normalizaba nada más allá de un `StandardScaler` estadístico de scikit-learn. Esa
   diferencia importa: el dataset de origen son fotos de estudio (mano grande, centrada, fondo
   uniforme) y sin normalización geométrica el modelo podía haber aprendido a depender de dónde
   y de qué tamaño aparece la mano en la foto — algo que no se sostiene con una cámara real de
   laboratorio. Nuestra normalización elimina esa dependencia.
4. **Lo único que se sigue reutilizando de ese hallazgo es el dataset de fotos**, no el código:
   [Kaggle "ASL Alphabet"](https://www.kaggle.com/datasets/grassknoted/asl-alphabet) (usuario
   `grassknoted`) — 29 carpetas (26 letras + `del`/`nothing`/`space`, que no se usan), 3000 fotos
   por letra, estructura `asl_alphabet_train/asl_alphabet_train/<letra>/*.jpg` (la carpeta
   duplicada es así en el ZIP original de Kaggle, no es un error de descarga). Es la materia
   prima cara de conseguir (miles de fotos ya etiquetadas a mano por otra persona); el
   procesamiento de esas fotos es enteramente nuestro.

## Arquitectura

Mismo protocolo que el espejo facial: la Jetson procesa la cámara y manda un sprite de 8 bytes
por UDP a la Pico W, que lo dibuja en la matriz MAX7219. **La Pico W no necesita ningún cambio**
— [`../espejo_facial_led/pico/main.py`](../espejo_facial_led/pico/main.py) y
[`max7219.py`](../espejo_facial_led/pico/max7219.py) sirven tal cual, con el mismo formato de
byte por fila / bit 7 = píxel izquierdo (ver
[`../espejo_facial_led/README.md`](../espejo_facial_led/README.md) sección 9).

Del lado Jetson hay dos partes bien separadas, igual que en el espejo facial (`gestos.py`
compartido entre el programa real y el visor de diagnóstico):

- **Entrenamiento** (`entrenamiento/`, corre en una PC de escritorio, no en la Jetson — no
  necesita cámara, solo procesa fotos de un dataset): produce el archivo `abecedario_modelo.pkl`
  una sola vez.
- **Reconocimiento en vivo** (`jetson/`, corre en la Jetson con la cámara real): carga ese
  `.pkl` y clasifica cada frame.

Las dos partes comparten `jetson/manos.py` — **tiene que ser el mismo código en las dos**,
porque el modelo solo predice bien si el vector que recibe en vivo se calculó exactamente igual
que los vectores con los que se entrenó.

### `jetson/manos.py` — normalización compartida

Convierte los 21 landmarks 3D de una mano (`hand_world_landmarks` de MediaPipe: coordenadas en
metros, con profundidad real — necesaria para distinguir letras como M/N/T, donde el pulgar
queda por delante o por detrás de los demás dedos y en una foto 2D se ven casi iguales) en un
vector de 63 números, en tres pasos:

1. Si la mano es izquierda, se espeja (se invierte la coordenada x) — así una misma letra hecha
   con cualquiera de las dos manos cae en el mismo lugar del espacio de vectores.
2. Se traslada el origen a la muñeca — no importa dónde esté la mano en el cuadro.
3. Se divide todo por la distancia muñeca→nudillo del dedo medio — no importa el tamaño de la
   mano ni la distancia a la cámara.

A propósito **no** se normaliza la rotación: en ASL la orientación es parte de la letra (G y Q
son la misma forma de dedos apuntando en distinta dirección).

### `entrenamiento/extraer_landmarks.py`

Recorre las 24 carpetas de letras del dataset de Kaggle, toma una muestra de fotos de cada una
(300 por letra por defecto — un número chico a propósito para el primer intento; subirlo después
es cambiar una constante y volver a correr), les aplica `HandLandmarker` + `manos.py`, y guarda
todos los vectores válidos junto con su letra en `dataset_landmarks.npz`.

### `entrenamiento/entrenar.py`

Carga ese `.npz` y entrena un clasificador de **vecinos más cercanos (KNN)**: compara una mano
nueva contra las muestras guardadas y vota por la letra de las más parecidas — sin "aprendizaje"
opaco de por medio, siempre se puede ver a qué muestra se pareció una predicción. Separa un 20%
de las fotos sin usar para entrenar, para medir qué tan bien generaliza. **Ojo con ese número**:
mide qué tan bien predice sobre más fotos del mismo dataset (mismo estudio, mismo fondo, misma
distancia a cámara) — no dice nada sobre cómo le va con la cámara real del laboratorio. Eso solo
se sabe probándolo en vivo, que es la fase siguiente. Guarda el resultado en
`abecedario_modelo.pkl`.

## Fases

1. **Ver la mano.** [`jetson/probar_manos.py`](jetson/probar_manos.py) — confirmar que
   `HandLandmarker` de MediaPipe detecta una mano en la cámara de la Jetson y que los 21
   landmarks (incluidos los `world_landmarks` en metros, con profundidad) tienen sentido.
   **Hecho y verificado el 03/09**: mano detectada con confianza 0.93-1.00, `landmarks=21` y
   `world=21` en cada frame. Se vio ruido normal frame a frame (una punta de dedo saltando de
   golpe en algún frame suelto) — esperable, es lo que el estabilizador de la fase 3 va a
   filtrar, no bloquea nada.
2. **Extraer y entrenar.** `entrenamiento/extraer_landmarks.py` + `entrenamiento/entrenar.py` —
   **escritos el 07/09, todavía sin correr ninguno de los dos.** Ver "Próximos pasos".
3. Integrar `abecedario_modelo.pkl` en un script de la Jetson: clasificar cada frame en vivo y
   agregar un estabilizador temporal (repetir la misma letra varios frames seguidos antes de
   darla por buena) para que no titile con el ruido del detector — mismo rol que la media móvil
   de `gestos.py` en el espejo facial, pero sobre un valor discreto.
4. Fuente de 5×7 por letra y armado del sprite de 8 bytes.
5. Enviar por UDP a la Pico W y confirmar en la matriz real.

## Próximos pasos (para retomar en la próxima sesión)

**Todo esto se corre en la PC de escritorio (no en la Jetson) — es la que ya tiene el dataset
extraído y el entorno armado, en `proyectos/abecedario_de_senas/`:**

1. Activar el entorno ya creado y correr la extracción (tarda: procesa ~7.200 fotos con
   MediaPipe, una por una):
   ```bash
   cd proyectos/abecedario_de_senas
   source entrenamiento_venv/bin/activate
   python3 entrenamiento/extraer_landmarks.py
   ```
   Mirar que el resumen final no tenga letras en cero ni con muchas "descartadas por escala
   degenerada" — si pasa, revisar antes de seguir.
2. Entrenar con el resultado:
   ```bash
   python3 entrenamiento/entrenar.py
   ```
   Mirar el `classification_report` — si alguna letra sale mal en el 20% de prueba (mismo
   dataset), va a salir peor todavía con la cámara real; son las primeras candidatas a fallar en
   la fase siguiente.
3. Con `abecedario_modelo.pkl` generado, escribir el script de la fase 3 (recién ahí, sobre la
   Jetson): cargar el modelo + `manos.py`, clasificar en vivo con la cámara, y el estabilizador
   temporal.

## Notas del entorno (para no reinstalar de cero)

Todo esto vive dentro de `proyectos/abecedario_de_senas/`, en la PC de escritorio, y está
excluido de git (`.gitignore`) por pesado — si hay que rearmarlo desde cero en otra máquina:

- `entrenamiento_venv/` — venv de Python 3.12 con `mediapipe`, `opencv-python-headless`,
  `numpy`, `scikit-learn`, `joblib`.
- `hand_landmarker.task` — modelo de MediaPipe, bajado con:
  ```bash
  wget -O hand_landmarker.task \
    https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
  ```
- `dataset_kaggle/` — el ZIP de Kaggle "ASL Alphabet" ya extraído acá.

Se intentó correr el entrenamiento en otra PC del laboratorio para no ocupar esta — no anduvo
(no se investigó por qué, no bloqueó nada) y se volvió a hacer todo en esta misma máquina.
