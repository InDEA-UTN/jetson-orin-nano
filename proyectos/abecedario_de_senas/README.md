# Abecedario de Señas LED

**Estado.** Al 16/09/2026: **el pipeline completo funciona de punta a punta contra el hardware
real** — cámara de la Jetson → clasificador (**95.92%** de precisión sobre el 20% de prueba, 28
etiquetas) → estabilizador temporal → matriz LED 8×8 mostrando la letra. Las 8 fases del plan
original están hechas. `jetson/reconocer_letra.py` (con ventana local) y
`jetson/reconocer_letra_stream.py` (sin monitor, video por túnel SSH) clasifican en vivo,
estabilizan la letra, arman texto de corrido con `space`/`del`, y mandan la letra confirmada por
UDP a la Pico W usando la fuente propia de `jetson/letras_matriz.py`. **El alcance se amplió a 28
etiquetas** — se sumaron J y Z (como poses estáticas) y `space`/`del` como comandos de edición —
sin degradar la precisión respecto de las 24 anteriores. El plan original de usar un modelo
pre-entrenado por otra persona se abandonó (motivo abajo, sección "Decisiones") y se pivotó a
entrenar un modelo propio con un dataset público de fotos. Lo que queda es ajuste fino, no
funcionalidad nueva — ver "Qué queda por mejorar".

## Objetivo

Traducir el abecedario dactilológico (lenguaje de señas) a letras normales, mostrando cada letra
reconocida en la matriz LED 8×8, con el mismo equipo del proyecto
[`espejo_facial_led/`](../espejo_facial_led/): Jetson Orin Nano (cámara + MediaPipe), Raspberry
Pi Pico W (WiFi + matriz MAX7219), y el mismo protocolo UDP de 8 bytes entre las dos.

Es un proyecto separado del espejo facial porque el problema de fondo es otro: ahí se
cuantizaban gestos de cara con reglas simples sobre 1-2 métricas (EAR, MAR); acá hay que
clasificar 28 poses de mano distintas a partir de 21 puntos cada una, que es un problema de
clasificación, no de umbrales a mano — ver "Por qué un clasificador y no reglas" más abajo.

## Decisiones de alcance ya tomadas

- **Abecedario: ASL (americano), no LSA.** 26 letras. Es el alfabeto con más documentación y
  material de referencia disponible — más fácil de hacer andar bien en una primera versión que
  LSA.
- **28 etiquetas: las 26 letras + `space` y `del`.** Un solo frame de la mano por vez, sin
  ventana temporal. `space` y `del` son dos carpetas más que trae el dataset de Kaggle y no son
  letras sino **comandos de edición**: escribir un espacio y borrar el último carácter. Con esos
  dos, el reconocimiento deja de ser "letras sueltas" y se puede escribir texto de corrido.
  `nothing` (fondo sin mano) sí queda afuera: no hay mano que detectar, MediaPipe no devuelve
  landmarks y no habría vector que guardar — ese caso ya se resuelve en vivo mirando si el
  detector encontró algo o no.
- **J y Z entran, pero bajo sospecha.** En ASL las dos se hacen dibujando la letra en el aire
  (movimiento), y este sistema clasifica un frame quieto por vez. Se incluyen igual porque el
  dataset trae fotos fijas de ellas y el costo de probarlas es bajo (dos etiquetas más en la
  lista, nada de código nuevo), pero una foto fija solo captura un instante del gesto — la J
  arranca con la misma forma de mano que la I — así que **hay que mirar J, Z e I en el
  `classification_report` antes de darlas por buenas**. Si meten ruido a la I, que hoy anda bien,
  conviene sacarlas de `manos.LETRAS` y volver a las 26 etiquetas.

## Por qué un clasificador y no reglas escritas a mano

En el espejo facial cada gesto era una regla simple sobre 1-2 números ("boca abierta si MAR >
umbral"): una sola frontera en una línea numérica, viable a ojo con 4-5 gestos.

Acá el problema es distinto en tamaño, no solo en cantidad de letras. Cada letra es una pose
definida por la posición relativa de 21 puntos (63 números: x, y, z de cada uno), y hay que
repartir ese espacio de 63 números en 28 zonas —una por etiqueta— sin que ninguna se pise con otra
(que una misma mano cumpla la regla de dos letras a la vez) ni queden huecos sin cubrir. Con 1
número y 2 categorías eso es un solo corte trivial; con 63 números y 28 categorías, las fronteras
entre letras parecidas cruzan varias de esas dimensiones a la vez y ya no se pueden imaginar ni
calcular a mano.

Ejemplos reales del propio dataset: **M, N y T se distinguen solo por si el pulgar queda apenas
adelante o apenas atrás de los demás dedos** —una sola de las 63 coordenadas, en un rango
angosto— y **U y V solo por el ángulo entre dos dedos extendidos**. Encontrar a mano el umbral
exacto que separe cada uno de esos pares, sin pisar la zona de otra letra, ya es durísimo para un
solo par; son 28 etiquetas. Y aunque se encontrara ese umbral mirando una mano puntual, no
generalizaría: una mano más grande, o la misma mano rotada un poco, corre el valor de esa
coordenada, así que un número fijo calibrado a una sola mano falla con otra.

Un clasificador resuelve esto sin que un humano tenga que inventar esas 28 fronteras: guarda
muchos ejemplos ya etiquetados (mano → letra correcta) y, ante una mano nueva, mide a cuáles se
parece más, en vez de compararla contra un umbral fijo que alguien adivinó. La frontera entre M y
N queda definida implícitamente por dónde caen los ejemplos reales de cada una en ese espacio de
63 números, no por una fórmula. Para eso hace falta un **dataset**: un conjunto de esos ejemplos
del que "aprender" comparando.

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
   `grassknoted`) — 29 carpetas (26 letras + `del`/`space`, que se usan como comandos de
   edición, y `nothing`, que no), 3000 fotos
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

### `jetson/letras_matriz.py` — la fuente de letras y por qué no todas miden lo mismo

La Pico W **no se toca para nada**: sigue siendo la misma pantalla tonta que ya usaba el espejo
facial, recibe 8 bytes por UDP y prende los píxeles que le llegan, sin saber si eso es una cara o
una letra. Toda la decisión de "qué dibujar" vive de este lado, en `letras_matriz.py`.

Cada letra se diseñó a mano en una grilla clásica de matrices de puntos, 5 columnas × 7 filas
(deja margen dentro del canvas real de 8×8). Pero **W, X e Y usan 7 columnas en vez de 5** — son
las tres letras con trazos diagonales, y una diagonal necesita más columnas de por medio para
verse suave en vez de comprimida. Esto se puede hacer sin romper nada porque la matriz muestra
**una sola letra fija a la vez, no texto corriendo**: si fuera scroll, todas las letras
necesitarían el mismo ancho para que el espaciado se vea parejo (fuente monoespaciada); acá cada
letra se centra en su propio ancho (`sprite_de_letra()` calcula el margen según el ancho de esa
letra en particular), así que no hay ningún costo en dejar que las que lo necesitan usen más
espacio. Las letras se revisaron primero en consola con
[`jetson/ver_letras_matriz.py`](jetson/ver_letras_matriz.py) (imprime cada sprite como bloques
`█`/`·`) antes de gastar tiempo probándolas contra el hardware — iterar en la consola es gratis,
iterar contra la matriz física es lento.

`del`, `space` y la ausencia de mano **no tienen sprite a propósito**: la decisión fue que la
matriz se apague en esos tres casos en vez de mostrar un símbolo propio para cada uno.

### El envío por UDP: siempre, no solo cuando cambia

`enviar_a_matriz()` (en `reconocer_letra.py` y `reconocer_letra_stream.py`) manda un paquete **en
cada frame**, con la letra que dice `estabilizador.confirmada` — nunca la letra cruda, porque eso
haría titilar la matriz 30 veces por segundo entre letras parecidas. Y se manda siempre, aunque la
letra no haya cambiado desde el frame anterior: UDP puede perder un paquete en silencio, y si solo
se mandaran los cambios, un paquete perdido dejaría la matriz mostrando la letra vieja **para
siempre**. Mandando siempre, el sistema se auto-corrige solo en el próximo frame (33 ms después) —
mismo criterio que ya usa `jetson_face.py` del espejo facial.

Antes de enchufar esto al reconocedor completo, se probó el camino de red aislado con
[`jetson/probar_matriz.py`](jetson/probar_matriz.py) (manda una letra fija por UDP en loop, sin
cámara ni modelo de por medio) — mismo criterio que aislar `joblib.load()` antes de la prueba en
vivo del clasificador: si la matriz no muestra bien la letra, hay que saber si es un problema de
red/protocolo o de reconocimiento, no adivinar.

### `entrenamiento/extraer_landmarks.py`

Recorre las 28 carpetas del dataset de Kaggle listadas en `manos.LETRAS`, toma una muestra de
fotos de cada una (300 por etiqueta por defecto — un número chico a propósito para el primer
intento; subirlo después es cambiar una constante y volver a correr), les aplica
`HandLandmarker` + `manos.py`, y guarda todos los vectores válidos junto con su etiqueta en
`dataset_landmarks.npz`.

### `entrenamiento/entrenar.py`

Carga ese `.npz` y entrena un clasificador de **vecinos más cercanos (KNN, K=5, `weights="distance"`)**:
para clasificar una mano nueva mide la distancia contra las miles de muestras guardadas y vota
por la etiqueta de las más parecidas (dándole más peso a las más cercanas) — sin "aprendizaje" opaco de
por medio, siempre se puede ver a qué muestra se pareció una predicción, mismo espíritu que
`gestos.py` del espejo facial. Con `train_test_split(..., stratify=y)` separa al azar un 20% de
los vectores que el modelo **nunca ve** durante el entrenamiento (manteniendo la proporción de
cada letra), entrena solo con el 80% restante, y mide la precisión preguntando ese 20% que quedó
afuera — la única forma honesta de saber si generaliza en vez de haber memorizado las respuestas.
Guarda el resultado en `abecedario_modelo.pkl`.

**Resultado real (15/09, 28 etiquetas): 95.92% de precisión** sobre las 1.275 muestras del 20%
de prueba. La corrida anterior, con 24 letras, había dado 95.87% sobre 1.115 — o sea que **sumar
4 clases nuevas no degradó nada**. Del `classification_report` completo, lo que vale la pena
anotar:

- **J (1.00/0.96) y Z (1.00/1.00) quedaron entre las mejores**, y la I —la que se temía que
  sufriera, porque la J arranca con su misma forma de mano— apenas se movió (0.98/1.00, antes
  1.00/1.00). La sospecha no se confirmó *dentro del dataset*. Pero cuidado con leer de más ese
  1.00: las fotos de Kaggle para J y Z capturan siempre el mismo instante del gesto, así que el
  número prueba que esas fotos son separables entre sí, no que la letra se reconozca al hacerla
  de verdad (al ser movimiento, la mano recorre varias poses y el clasificador dispara letras en
  el camino).
- **`del` (0.93/1.00) y `space` (0.94/0.97)** entraron sin problema, aunque `space` fue la
  etiqueta con menos fotos válidas de todas (152 de 300).
- **U (0.83/0.86), V (0.88/0.88) y R (0.91/0.86)** siguen siendo las más flojas, igual que en la
  corrida anterior — hipótesis: se confunden entre sí, porque en ASL son geométricamente
  parecidas (mismos dos dedos extendidos — índice y medio —, difieren en el ángulo entre ellos y
  en si se cruzan). **M y N** rondan 0.89, esperable por venir con menos muestras desde la
  extracción. Entre corridas M y N intercambiaron precision y recall: es ruido de muestreo (el
  20% de prueba es otro), no una señal.
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
   — **hecho** (rehecho con 28 etiquetas). De las 8.400 fotos elegidas (300 por etiqueta),
   quedaron **6.375 vectores válidos** guardados en `dataset_landmarks.npz` (no se versiona, se
   regenera corriendo el script):

   ```
       A:217      B:221      C:198      D:252      E:232      F:286      G:234      H:235
       I:230      J:267      K:271      L:261      M:164      N:137      O:227      P:213
       Q:211      R:248      S:251      T:233      U:248      V:252      W:236      X:222
       Y:264      Z:230    del:183  space:152
   ```

   **M, N y `space` quedaron bastante por debajo del resto** (164, 137 y 152, contra un promedio
   de ~230). En M y N es por el pulgar escondido detrás de los demás dedos: esa oclusión también
   le cuesta al detector en la foto 2D del dataset, no solo a la cámara real.

3. **Entrenar.** [`entrenamiento/entrenar.py`](entrenamiento/entrenar.py) — **hecho, 95.92% de
   precisión** con las 28 etiquetas (antes: 95.87% con 24). Agregar 4 clases nuevas no degradó
   nada. Lo llamativo: **J y Z quedaron entre las mejores** (1.00/0.96 y 1.00/1.00) y la I casi
   no se movió (0.98/1.00, antes 1.00/1.00), así que la sospecha de que la J le robara muestras a
   la I no se confirmó — **en el dataset**. Ojo con leer de más ese 1.00: mide que las fotos de J
   de Kaggle (siempre el mismo instante del gesto) son separables de las otras fotos de Kaggle.
   No dice nada de qué pasa cuando alguien hace la J de verdad frente a la cámara: al ser un
   movimiento, la mano pasa por varias poses en el camino y el clasificador va a disparar letras
   en esa transición. `del` (0.93/1.00) y `space` (0.94/0.97) también entraron bien. Las flojas
   siguen siendo las mismas de antes: **U (0.83/0.86), V (0.88/0.88), R (0.91/0.86) y M/N (~0.89)**.

4. **Llevar el modelo a la Jetson y probarlo en vivo.** [`jetson/reconocer_letra.py`](jetson/reconocer_letra.py)
   — **hecho y probado con éxito.** Carga `manos.py` + `abecedario_modelo.pkl` y clasifica cada
   frame de la cámara real. En la prueba real, **U, V y R —las candidatas sospechosas del
   `classification_report`— se reconocieron bien**; el riesgo grande de esta fase (que el modelo,
   entrenado sobre fotos de estudio, no generalizara a mano/luz/fondo reales de laboratorio) no
   se confirmó tan grave como se temía. En el camino se encontró y resolvió un desfasaje de
   versión de scikit-learn entre la PC y la Jetson — ver la sección de arriba.

5. **Estabilizador temporal, con ventana de landmarks.** [`jetson/reconocer_letra.py`](jetson/reconocer_letra.py)
   — **hecho y probado en vivo.** Mismo script de la fase anterior, ampliado con dos cosas: una
   ventana local (`cv2.imshow`, mismo patrón que `jetson_face.py` del espejo facial) que dibuja
   los 21 landmarks sobre el video y muestra en texto tanto la letra cruda del frame como la ya
   confirmada — necesita sesión gráfica local, ver la trampa del `DISPLAY` más abajo — y la clase
   `EstabilizadorLetra`, que exige que la misma letra cruda se repita `UMBRAL_ESTABLE` frames
   seguidos (8 por defecto) antes de escribirla, para que el ruido frame a frame del detector (ya
   visto en el paso 1) no haga titilar la letra ni llene la consola de letras fantasma. Mismo rol
   que la media móvil de `gestos.py` en el espejo facial, pero sobre un valor discreto (contar
   repeticiones) en vez de un promedio continuo. Sostener la misma letra `UMBRAL_REPETICION`
   frames más la vuelve a escribir (auto-repeat, como mantener una tecla), que es lo que permite
   escribir "CALLE" o borrar varios caracteres con `del`. **Probado con los valores por defecto
   (8/16/10) sin tocar nada y anduvo bien** — queda como posible ajuste fino más adelante, no
   como pendiente bloqueante.

6. **Fuente de 5×7 (7 para W/X/Y) y sprite por letra.** [`jetson/letras_matriz.py`](jetson/letras_matriz.py)
   — **hecho**. Las 26 letras diseñadas a mano y revisadas en consola antes de tocar hardware con
   [`jetson/ver_letras_matriz.py`](jetson/ver_letras_matriz.py) — ver la sección de arriba para el
   porqué de los anchos distintos. `del`, `space` y sin mano dejan la matriz apagada a propósito.

7. **Enviar por UDP a la Pico W.** — **hecho, y la Pico no se tocó**: el protocolo de 8 bytes ya
   armado y probado en el espejo facial se reusa tal cual
   ([`../espejo_facial_led/pico/main.py`](../espejo_facial_led/pico/main.py) y
   [`max7219.py`](../espejo_facial_led/pico/max7219.py)). Se probó primero aislado con
   `probar_matriz.py` (sin cámara) y recién después enchufado al reconocedor real — ver la sección
   de arriba para el porqué de mandar el paquete siempre, no solo al cambiar.

8. **Prueba de punta a punta.** — **hecho el 16/09**: letra hecha con la mano real → clasificada
   → estabilizada → mostrada en la matriz LED, sin nada simulado de por medio. En el camino
   aparecieron dos trampas de infraestructura (no del reconocimiento en sí) — ver la sección de
   trampas más abajo. El ajuste fino que pueda hacer falta (`MUESTRAS_POR_LETRA`, umbrales del
   estabilizador, J/Z en movimiento real) queda para seguir puliendo, no para destrabar nada.

## Trampas de infraestructura encontradas en la prueba de punta a punta (16/09)

Ninguna de estas es un problema del reconocimiento ni del modelo — las tres son de "cablear" la
Jetson, la Pico y la PC entre sí:

- **El hotspot de la Jetson no levantaba** (`nmcli connection up Hotspot` fallaba con "No
  suitable device found... mismatching interface name"). La causa real no era esa: la placa WiFi
  (`wlP1p1s0`) estaba en estado `unavailable` (radio apagada por software), así que NetworkManager
  intentaba poner el perfil en la única interfaz que le quedaba libre (la de Ethernet) y fallaba
  ahí. Se resolvió con `sudo nmcli radio wifi on`. Si vuelve a pasar, primero chequear
  `nmcli device status` y `nmcli radio wifi` antes de sospechar del perfil del hotspot en sí.
- **`cv2.imshow` no abre por SSH aunque haya un monitor físico conectado a la Jetson.** Conectar
  el cable no alcanza: una sesión SSH es un canal aparte que no hereda la variable `DISPLAY` de la
  sesión gráfica que arrancó en ese monitor. Hace falta estar sentado físicamente en la Jetson
  (con su propio teclado/mouse) para que `reconocer_letra.py` (la versión con ventana) abra sin
  error — por SSH conviene usar `reconocer_letra_stream.py` en cambio, que no depende de
  `DISPLAY` para nada (ver su sección en `jetson/README.md`).
- **Un `scp` viejo hizo perder tiempo:** después de agregar `enviar_a_matriz()` a
  `reconocer_letra.py`, la matriz no reaccionaba a nada — pero el script corría sin errores. La
  causa: el archivo en la Jetson era una copia de antes de ese cambio (nunca se volvió a copiar).
  Se detectó comparando el número de línea de un error de una corrida anterior contra el número de
  línea de esa misma instrucción en el archivo actual — si no coinciden, el archivo que corriste
  no es el que creés. **Lección: después de todo `scp` a la Jetson, si algo no cambia de
  comportamiento, confirmar con `grep -n <algo del cambio nuevo> archivo.py` antes de seguir
  debuggeando el código en sí.**

## Qué queda por mejorar

- **M y N** son las primeras candidatas a fallar en el uso real (menos muestras desde la
  extracción). Primer remedio a probar: subir `MUESTRAS_POR_LETRA` en `extraer_landmarks.py`
  (hoy en 300) para esas letras, o para todas.
- **U, V y R** salieron algo flojas en el `classification_report` por ser geométricamente
  parecidas entre sí — en pruebas en vivo anteriores anduvieron bien, pero falta una prueba más
  sistemática (mostrar cada una varias veces seguidas y contar aciertos) antes de darlas por
  confirmadas del todo.
- **J y Z** pasaron el examen del dataset con nota alta (1.00/0.96 y 1.00/1.00) sin arruinar la
  I, pero eso solo prueba que las fotos de Kaggle son separables entre sí. **Falta la prueba en
  vivo haciendo el gesto real** (con movimiento), que es la que puede fallar: al hacerlas de
  verdad la mano recorre varias poses y el clasificador va a ir disparando letras durante el
  movimiento. Reconocerlas *bien* sigue siendo otro problema — habría que clasificar una ventana
  de varios frames en vez de uno quieto.
- Los umbrales del estabilizador (`UMBRAL_ESTABLE=8`, `UMBRAL_REPETICION=16`,
  `UMBRAL_SIN_MANO=10`) anduvieron bien tal cual en la primera prueba de punta a punta, sin
  tocar nada — quedan como candidatos a afinar más adelante si con el uso se sienten muy rápidos
  o muy lentos, no como algo pendiente de resolver.
- La Pico sigue arrancando `main.py` apretando "Run" en Thonny cada sesión, no quedó grabado en
  la memoria interna para arrancar solo con darle alimentación. No es un problema — solo significa
  acordarse de abrir Thonny y correrlo antes de probar el reconocedor.

## Próximos pasos

El pipeline completo ya funciona de punta a punta. Lo que sigue es afinar, no destrabar nada
nuevo:

1. Probar **J y Z haciendo el gesto real** (con movimiento) frente a la cámara, no solo fotos
   fijas del dataset — es la prueba que falta de la fase 3/8.
2. Si M, N, `space`, U, V o R fallan seguido en el uso real, subir `MUESTRAS_POR_LETRA` en
   `extraer_landmarks.py` para esas letras y reentrenar.
3. Si el auto-repeat o el tiempo de confirmación se sienten mal calibrados con el uso, ajustar
   `UMBRAL_ESTABLE` / `UMBRAL_REPETICION` / `UMBRAL_SIN_MANO` en `reconocer_letra.py` **y**
   `reconocer_letra_stream.py` (están duplicados a propósito, hay que tocar los dos).
4. Opcional: grabar `main.py` en la memoria interna de la Pico para que arranque sola con la
   alimentación, sin depender de Thonny.

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

**Antes de correr el reconocedor con salida a la matriz**, hace falta el hotspot de la Jetson
levantado y la Pico corriendo `main.py` y conectada a él — ver
[`../espejo_facial_led/integracion.md`](../espejo_facial_led/integracion.md) sección 11 para el
detalle completo. Si `nmcli connection up Hotspot` falla, chequear primero
`nmcli device status`: si la placa WiFi aparece `unavailable`, la radio está apagada por software
y se prende con `sudo nmcli radio wifi on` (no es un problema del perfil del hotspot en sí).

**Trampa real encontrada (11/09):** al mover/copiar archivos del proyecto apareció una carpeta
duplicada `proyectos/abecedario_de_senas (2)/`, con una copia vieja del dataset de Kaggle sin
`.gitignore` que la cubriera — casi termina commiteada entera (~2 GB) con un `git add .` sin
revisar antes qué iba a entrar. Se encontró y se borró a tiempo. **Antes de cualquier `git add`
en este proyecto, correr `git status` y revisar que no haya rutas raras o pesadas en la lista**
— con datasets de por medio, un `git add .` a ciegas es peligroso.
