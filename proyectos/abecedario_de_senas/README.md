# Abecedario de Señas LED

**Estado.** Al 11/09/2026: el modelo ya está entrenado (**95.87%** de precisión sobre el 20% de
prueba) y probado con éxito en vivo, con la cámara real de la Jetson (`jetson/reconocer_letra.py`).
El plan original de usar un modelo pre-entrenado por otra persona se abandonó (motivo abajo,
sección "Decisiones") y se pivotó a entrenar un modelo propio con un dataset público de fotos.
**Falta la parte de salida**: estabilizador temporal, fuente para la matriz LED y el envío por
UDP — ver "Fases" y "Próximos pasos" más abajo.

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

### `jetson/manos.py` — normalización compartida, y de dónde salen los 63 números

MediaPipe `HandLandmarker` devuelve, por cada mano que detecta, **21 puntos** fijos (0 = muñeca;
1-4 pulgar, 5-8 índice, 9-12 medio, 13-16 anular, 17-20 meñique, cada dedo de la base a la
punta). De cada punto usamos `hand_world_landmarks`, no los landmarks "normales" — la diferencia
importa:

- `hand_landmarks` da coordenadas 0..1 relativas a la imagen (sirven para dibujar sobre el
  cuadro, pero no traen profundidad real).
- `hand_world_landmarks` da coordenadas en **metros reales**, con origen en el centro de la
  mano — sí traen profundidad. Hace falta esa profundidad porque hay letras (M, N, T) que solo
  se distinguen por dónde queda el pulgar en el eje que "entra" a la pantalla: en una foto 2D
  esas tres letras se ven casi idénticas.

21 puntos × 3 coordenadas (x, y, z) = **63 números** — ese es el vector crudo. `manos.py` lo
normaliza en tres pasos antes de que sirva para comparar manos entre sí:

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

Carga ese `.npz` y entrena un clasificador de **vecinos más cercanos (KNN, K=5, `weights="distance"`)**:
para clasificar una mano nueva mide la distancia contra las 5.575 muestras guardadas y vota por
la letra de las más parecidas (dándole más peso a las más cercanas) — sin "aprendizaje" opaco de
por medio, siempre se puede ver a qué muestra se pareció una predicción, mismo espíritu que
`gestos.py` del espejo facial. Con `train_test_split(..., stratify=y)` separa al azar un 20% de
los vectores que el modelo **nunca ve** durante el entrenamiento (manteniendo la proporción de
cada letra), entrena solo con el 80% restante, y mide la precisión preguntando ese 20% que quedó
afuera — la única forma honesta de saber si generaliza en vez de haber memorizado las respuestas.
Guarda el resultado en `abecedario_modelo.pkl`.

**Resultado real (11/09): 95.87% de precisión** sobre las 1.115 muestras del 20% de prueba. Del
`classification_report` completo, lo que vale la pena anotar:

- **M y N** salen algo bajas (recall 0.87 y 0.92) — esperable, ya venían con menos muestras desde
  la extracción (ver arriba).
- **U (recall 0.81) y V (recall 0.90)**, con soporte normal (52 y 50 muestras), salieron más
  bajas que el resto — hipótesis: se confunden entre sí, porque en ASL son geométricamente
  parecidas (mismos dos dedos extendidos — índice y medio —, difieren solo en el ángulo entre
  ellos). R (0.91) también quedó algo por debajo del promedio, misma familia de forma de mano.
- **Ojo con este número igual**: mide qué tan bien predice sobre más fotos del *mismo* dataset
  (mismo estudio, mismo fondo, misma distancia a cámara) — no dice nada por sí solo de cómo le va
  con la cámara real del laboratorio. Eso se probó en la fase siguiente (ver "Fases").

## Compatibilidad de versiones entre la PC y la Jetson (trampa real, ya resuelta)

El modelo se entrena en la PC de escritorio pero se usa en la Jetson — dos máquinas con dos
entornos de Python instalados por separado. `joblib.dump()`/`joblib.load()` no serializan el
`KNeighborsClassifier` como datos puros: guardan su representación interna de scikit-learn, que
no es parte de la API pública y puede cambiar entre versiones (lo dice la propia documentación
de scikit-learn). En la práctica: se entrenó primero con `scikit-learn 1.9.0` en la PC, pero la
Jetson tenía `1.7.2` instalado — al cargar el `.pkl` ahí, `joblib.load()` no tiraba error, pero sí
un `InconsistentVersionWarning` ("this might lead to breaking code or invalid results").

Se resolvió **bajando `scikit-learn` a 1.7.2 en el venv de la PC y volviendo a entrenar**, en vez
de actualizar la Jetson — reentrenar es rápido (segundos) y no toca nada; el venv de la Jetson en
cambio ya tenía mediapipe/opencv funcionando y arrastra cierta tensión de versiones numpy/scipy
preexistente, más arriesgado de tocar. Después de igualar la versión, `joblib.load()` en la
Jetson cargó limpio, sin el warning.

**Antes de copiar un `.pkl` nuevo a la Jetson**, conviene chequear que las versiones coincidan:

```bash
# en los dos lados, con el venv correspondiente activado
python3 -c "import sklearn, joblib; print(sklearn.__version__, joblib.__version__)"
```

Y antes de escribir o correr un script de reconocimiento completo, probar la carga sola, sin
cámara — aísla "¿el modelo carga bien?" de "¿anda la cámara?", así cualquier falla en la prueba
en vivo se puede atribuir al problema real que se está investigando (cámara/dominio) y no a esto:

```bash
python3 -c "import joblib; m = joblib.load('abecedario_modelo.pkl'); print(m)"
```

## Fases

1. **Ver la mano.** [`jetson/probar_manos.py`](jetson/probar_manos.py) — confirmar que
   `HandLandmarker` de MediaPipe detecta una mano en la cámara de la Jetson y que los 21
   landmarks (incluidos los `world_landmarks` en metros, con profundidad) tienen sentido.
   **Hecho y verificado el 03/09**: mano detectada con confianza 0.93-1.00, `landmarks=21` y
   `world=21` en cada frame. Se vio ruido normal frame a frame (una punta de dedo saltando de
   golpe en algún frame suelto) — esperable, es lo que el estabilizador del paso 5 va a filtrar.

2. **Extraer landmarks.** [`entrenamiento/extraer_landmarks.py`](entrenamiento/extraer_landmarks.py)
   — **hecho**. De las 7.200 fotos elegidas (300 por letra), quedaron **5.575 vectores válidos**
   guardados en `dataset_landmarks.npz` (no se versiona, se regenera corriendo el script):

   ```
   A:217  B:221  C:198  D:252  E:232  F:286  G:234  H:235
   I:230  K:276  L:250  M:155  N:129  O:231  P:205  Q:221
   R:263  S:260  T:242  U:259  V:248  W:245  X:225  Y:261
   ```

   **M y N quedaron bastante por debajo del resto** (155 y 129, contra un promedio de ~232) —
   son justo las letras donde el pulgar queda escondido detrás de los demás dedos, y esa
   oclusión también le cuesta al detector en la foto 2D del dataset, no solo a la cámara real.

3. **Entrenar.** [`entrenamiento/entrenar.py`](entrenamiento/entrenar.py) — **hecho, 95.87% de
   precisión.** Ver el detalle completo y las letras que salieron más flojas (M, N, U, V, R) en
   la sección de arriba.

4. **Llevar el modelo a la Jetson y probarlo en vivo.** [`jetson/reconocer_letra.py`](jetson/reconocer_letra.py)
   — **hecho y probado con éxito.** Carga `manos.py` + `abecedario_modelo.pkl` y clasifica cada
   frame de la cámara real (por SSH, sin guardar nada en disco: ni imágenes ni video, solo
   imprime la letra por consola). En la prueba real, **U, V y R —las candidatas sospechosas del
   `classification_report`— se reconocieron bien**; el riesgo grande de esta fase (que el modelo,
   entrenado sobre fotos de estudio, no generalizara a mano/luz/fondo reales de laboratorio) no
   se confirmó tan grave como se temía. En el camino se encontró y resolvió un desfasaje de
   versión de scikit-learn entre la PC y la Jetson — ver la sección de arriba.

5. **Estabilizador temporal.** *Pendiente.* Exigir que la misma letra se repita varios frames
   seguidos antes de darla por "confirmada", para que el ruido frame a frame del detector (ya
   visto en el paso 1) no haga titilar la matriz entre letras ni llene el texto de letras
   fantasma. Mismo rol que la media móvil de `gestos.py` en el espejo facial, pero sobre un valor
   discreto (contar repeticiones) en vez de un promedio continuo.

6. **Fuente de 5×7 y sprite por letra.** *Pendiente.* Un dibujo de cada letra en una grilla de 5
   columnas × 7 filas (con 1 columna libre para centrar en la matriz de 8×8) — igual a como
   `gestos.py` del espejo facial dibuja cejas/ojos/boca con puntos. Es trabajo de diseño visual,
   no de machine learning: elegir, para cada letra, la representación más legible a un tamaño tan
   chico.

7. **Enviar por UDP a la Pico W.** *Pendiente, pero sin nada nuevo que programar de ese lado*:
   el protocolo de 8 bytes (un byte por fila, bit 7 = píxel izquierdo) ya está armado y probado
   en el espejo facial — se reusan [`../espejo_facial_led/pico/main.py`](../espejo_facial_led/pico/main.py)
   y [`max7219.py`](../espejo_facial_led/pico/max7219.py) tal cual.

8. **Prueba de punta a punta y ajuste fino.** *Pendiente.* Mostrar letras reales frente a la
   Jetson y ver qué aparece en la matriz; ajustar lo que falle (subir `MUESTRAS_POR_LETRA` si una
   letra anda mal, tocar el número de frames del estabilizador, etc.) — recién ahí, iterando
   sobre datos reales de la placa completa, no sobre suposiciones.

## Qué queda por mejorar

- **M y N** son las primeras candidatas a fallar en el uso real (menos muestras desde la
  extracción). Primer remedio a probar: subir `MUESTRAS_POR_LETRA` en `extraer_landmarks.py`
  (hoy en 300) para esas letras, o para todas.
- **U, V y R** salieron algo flojas en el `classification_report` por ser geométricamente
  parecidas entre sí — en la prueba en vivo anduvieron bien, pero falta una prueba más
  sistemática (mostrar cada una varias veces seguidas y contar aciertos) antes de darlas por
  confirmadas del todo.
- El estabilizador temporal (paso 5) todavía no existe — sin él, la matriz de LEDs va a titilar
  con el ruido normal del detector en cuanto se conecte esa parte.
- Si en algún momento se agrega reconocimiento de **J y Z** (las dos letras con movimiento que
  quedaron afuera de esta v1), hace falta repensar el pipeline: ya no alcanza con clasificar un
  frame quieto, hay que clasificar una ventana de varios frames.

## Próximos pasos (para retomar la próxima sesión)

En este orden, todo del lado de la Jetson (el entrenamiento en la PC de escritorio ya no hace
falta repetirlo, salvo que se decida subir `MUESTRAS_POR_LETRA` para M/N):

1. Paso 5 — estabilizador temporal en `jetson/reconocer_letra.py` (o un script nuevo que lo
   envuelva).
2. Paso 6 — diseñar la fuente 5×7 de las 24 letras.
3. Paso 7 — armar el sprite de 8 bytes por letra y enviarlo por UDP a la Pico W (reusando el
   protocolo del espejo facial).
4. Paso 8 — prueba de punta a punta con la matriz real y ajuste fino.

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

**Del lado de la Jetson**, además de lo que ya usaba `probar_manos.py` (mediapipe, opencv,
`hand_landmarker.task` en `/home/indea/hand_landmarker.task`), `reconocer_letra.py` necesita en
el mismo venv (`espejo_facial_venv`, según se armó en la práctica):

```bash
pip install "scikit-learn==1.7.2" joblib
```

**Importante**: esa versión de scikit-learn tiene que coincidir con la que se usó para generar
`abecedario_modelo.pkl` en la PC de escritorio — ver la sección "Compatibilidad de versiones"
más arriba antes de reentrenar con una versión distinta.

**Trampa real encontrada (11/09):** al mover/copiar archivos del proyecto apareció una carpeta
duplicada `proyectos/abecedario_de_senas (2)/`, con una copia vieja del dataset de Kaggle sin
`.gitignore` que la cubriera — casi termina commiteada entera (~2 GB) con un `git add .` sin
revisar antes qué iba a entrar. Se encontró y se borró a tiempo. **Antes de cualquier `git add`
en este proyecto, correr `git status` y revisar que no haya rutas raras o pesadas en la lista**
— con datasets de por medio, un `git add .` a ciegas es peligroso.
