# Jetson — abecedario de señas

Esta carpeta tiene el código que corre **en la Jetson, con la cámara real**, a diferencia de
`../entrenamiento/`, que corre una sola vez en una PC de escritorio sobre fotos de un dataset.
Ninguno de estos scripts guarda nada en disco (ni imágenes ni video). `probar_manos.py` corre por
SSH sin monitor (solo imprime texto); `reconocer_letra.py` abre una ventana local con los
landmarks dibujados y necesita sesión gráfica; `reconocer_letra_stream.py` hace lo mismo sin
necesitar monitor ni sesión gráfica (ver sus secciones más abajo).

Para el porqué de cada decisión (de dónde salen los 63 números, por qué KNN, la fuente de letras,
la trampa de versiones entre la PC y la Jetson) ver el **[README principal del
proyecto](../README.md)** — este archivo es solo la guía práctica de esta carpeta.

## Los archivos

### `manos.py` — no es un script, es la lógica compartida

No se corre solo. Lo importan tanto los scripts de reconocimiento (acá) como
`../entrenamiento/extraer_landmarks.py` (en la PC), y **tiene que ser el mismo código de los dos
lados**: define `vector_normalizado()`, la función que convierte los 21 landmarks 3D de una mano
(`hand_world_landmarks` de MediaPipe) en el vector de 63 números que entiende el clasificador —
espejando la mano izquierda, centrando en la muñeca y escalando por el tamaño de la mano. Si esta
función se calculara distinto en la Jetson que durante el entrenamiento, el modelo recibiría
vectores en otro "idioma" numérico y clasificaría mal sin tirar ningún error. También tiene la
lista de las 28 etiquetas reconocidas (`LETRAS`: las 26 letras más `del` y `space`, los dos
comandos de edición) y las funciones para guardar/cargar el dataset de
vectores (`guardar_dataset`/`cargar_dataset`), usadas del lado de la PC.

### `probar_manos.py` — Fase 1: ver la mano

El primer script del proyecto, sin nada de clasificación todavía. Abre la cámara, le corre
`HandLandmarker` a cada frame, e imprime por consola si detectó una mano y las coordenadas de las
puntas de los dedos. Su único objetivo es confirmar que MediaPipe funciona bien en esta placa
puntual y que los landmarks (incluida la profundidad de `hand_world_landmarks`) tienen sentido,
antes de meter un clasificador en el medio. **Ya verificado** — ver "Fases" en el README
principal.

### `letras_matriz.py` — no es un script, es la fuente de letras

No se corre solo, lo importan `reconocer_letra.py`/`reconocer_letra_stream.py` (para mandar el
sprite a la Pico) y `ver_letras_matriz.py` (para previsualizar). Tiene el diseño de las 26 letras
en una grilla de puntos (5 columnas × 7 filas, 7 para W/X/Y) y dos funciones: `sprite_de_letra()`
centra ese diseño en el canvas real de 8×8, y `sprite_a_bytes()` lo convierte a los 8 bytes del
protocolo UDP (mismo formato que ya usa el espejo facial). Ver el README principal para el
porqué de los anchos distintos por letra y por qué `del`/`space`/sin-mano quedan sin sprite.

### `ver_letras_matriz.py` — previsualizar la fuente sin hardware

```bash
python3 ver_letras_matriz.py          # las 26 letras
python3 ver_letras_matriz.py W X Y    # solo esas, para iterar rapido una en particular
```

Imprime cada sprite como bloques `█`/`·` en la consola. No usa cámara, mediapipe, ni red —
corre en cualquier máquina con Python, incluida la PC de escritorio. Se usó para ajustar el
diseño de las letras antes de gastar tiempo probándolas contra la matriz física.

### `probar_matriz.py` — probar el envío UDP sin cámara

```bash
python3 probar_matriz.py A
```

Manda el sprite de una letra fija por UDP a la Pico, repetido cada 0.5s hasta Ctrl+C (no una vez
sola, para no confundir "se perdió el paquete" con "el sprite está mal"). Aísla el camino de
red/protocolo del reconocimiento — si la letra no aparece bien en la matriz acá, el problema es
la IP, el protocolo o el sprite, no el modelo ni mediapipe. Necesita el hotspot de la Jetson
levantado y la Pico corriendo `main.py` (ver "Antes de correr" más abajo).

### `reconocer_letra.py` — clasificar en vivo, con ventana, estabilizador y salida a la matriz

El script completo, con ventana local. Igual que `jetson_face.py` del espejo facial: abre una
ventana (`cv2.imshow`) con los landmarks dibujados sobre el video y el estado actual en texto, en
vez de imprimir solo por consola. Por cada frame con mano detectada:

1. El modelo se carga una sola vez, antes de abrir la cámara: `joblib.load('abecedario_modelo.pkl')`.
2. Calcula el vector normalizado con `manos.vector_normalizado()` (la misma función que usó el
   entrenamiento) a partir de `hand_world_landmarks` y la lateralidad de la mano, y le pregunta la
   letra al modelo (`modelo.predict([vector])`) — esta es la **letra cruda**, la que dio ese
   frame puntual.
3. Le pasa esa letra cruda a `EstabilizadorLetra` (definida en este mismo archivo): no confirma
   una letra nueva hasta que la misma letra cruda se repite `UMBRAL_ESTABLE` frames seguidos
   (8 por defecto). Esto filtra el ruido frame a frame del detector (ya visto en `probar_manos.py`)
   para que la letra reconocida no titile — mismo rol que la media móvil de `gestos.py` en el
   espejo facial, pero contando repeticiones de un valor discreto en vez de promediar uno
   continuo.
4. Dibuja los 21 puntos sobre el video y escribe en pantalla tanto la letra cruda de ese frame
   como la letra ya confirmada (con el contador de repeticiones, para ajustar `UMBRAL_ESTABLE` a
   ojo).
5. Va armando un **texto de corrido** con las letras confirmadas: una sola línea de consola que
   se reescribe con `\r` (no una línea nueva por letra), más el mismo texto en la ventana. Las
   etiquetas `space` y `del` se aplican como lo que son: escribir un espacio y borrar el último
   carácter (`aplicar_al_texto`).
6. `enviar_a_matriz()` manda por UDP a la Pico el sprite de la letra **confirmada** (nunca la
   cruda), en cada frame, incluso cuando no cambió — ver el README principal para el porqué de
   mandar siempre y no solo al cambiar.

Para **repetir** una letra ("CALLE") o borrar varios caracteres hay dos caminos, y el
estabilizador soporta los dos:

- **Sostener la letra**, igual que mantener una tecla apretada: cada `UMBRAL_REPETICION` frames
  extra (16 por defecto) la vuelve a escribir. Es lo cómodo para `del`: se mantiene y borra
  varios seguidos.
- **Sacar la mano** un instante y volver a hacerla: tras `UMBRAL_SIN_MANO` frames sin mano se
  suelta la letra sostenida, así la siguiente se escribe a los `UMBRAL_ESTABLE` frames en vez de
  esperar el auto-repeat. Es el camino rápido.

Un parpadeo del detector mientras se sostiene una letra (la letra salta unos frames y vuelve)
**no** la reescribe — si no, cualquier salto de ruido ensuciaría el texto con duplicados. La
ventana muestra en cuántos frames va a escribir la próxima, para ver venir el auto-repeat.

Cerrar con `q` (con foco en la ventana) o Ctrl+C en la consola. **Probado de punta a punta con
éxito el 16/09**: mano real → letra → matriz LED, con los umbrales por defecto.

### `reconocer_letra_stream.py` — lo mismo, pero sin monitor en la Jetson

Misma clasificación, mismo `EstabilizadorLetra` y el mismo `enviar_a_matriz()` que
`reconocer_letra.py`, pero sin `cv2.imshow`: en vez de abrir una ventana local, codifica cada
frame ya anotado como JPEG y lo sirve por HTTP en `127.0.0.1:8000` (solo alcanzable desde la
propia Jetson, no expuesto a la red). Para verlo desde la PC hace falta un **túnel SSH**, que
"estira" ese puerto hasta la PC:

```bash
ssh -L 8000:localhost:8000 <usuario>@<ip-jetson>
```

y con ese túnel abierto (puede ser una segunda sesión SSH, no hace falta usar esa para nada más),
abrir `http://localhost:8000/` en un navegador de la PC. El video viaja adentro del túnel ya
cifrado por SSH, así que no hace falta abrir ningún puerto en la red del laboratorio. Esta es la
opción a usar si estás por SSH y no querés (o no podés) sentarte físicamente en la Jetson — ver
la trampa del `DISPLAY` más abajo.

Se corta con Ctrl+C en la consola donde corre el script (no hay ventana con foco ni tecla `q`).

## Antes de correr cualquiera de los dos reconocedores

Además del venv con mediapipe/opencv/scikit-learn (ver "Cómo correrlo" abajo), la salida a la
matriz necesita la red Jetson-Pico levantada:

1. **Hotspot de la Jetson arriba**: `sudo nmcli connection up Hotspot`. Si falla con "No suitable
   device found... mismatching interface name", el problema real suele ser que la placa WiFi está
   `unavailable` (radio apagada por software) — chequear con `nmcli device status` y prender la
   radio con `sudo nmcli radio wifi on` antes de reintentar.
2. **La Pico corriendo `main.py`** (por ahora vía Thonny, apretando "Run" — no está grabado en su
   memoria interna para arrancar solo). Al conectar imprime la IP que le asignó el DHCP del
   hotspot; confirmarla contra `IP_PICO` en `reconocer_letra.py`/`reconocer_letra_stream.py`/
   `probar_matriz.py` si dejó de andar (puede cambiar entre sesiones).

Conviene probar la red aislada con `probar_matriz.py` antes de correr el reconocedor completo, si
es la primera vez en la sesión o algo del hardware cambió.

## Cómo correrlo

Necesita, en el venv de la Jetson (el mismo que ya usa `probar_manos.py`, con mediapipe/opencv):

```bash
pip install "scikit-learn==1.7.2" joblib
```

**Importante**: esa versión de scikit-learn tiene que coincidir con la que se usó para generar
`abecedario_modelo.pkl` en la PC de escritorio (ver "Compatibilidad de versiones" en el README
principal) — si no coincide, `joblib.load()` puede no tirar error pero sí un
`InconsistentVersionWarning`, sin garantía de que el resultado sea correcto.

Con `abecedario_modelo.pkl` y `letras_matriz.py` copiados a esta misma carpeta:

```bash
python3 reconocer_letra.py          # con ventana: hace falta estar sentado en la Jetson
python3 reconocer_letra_stream.py   # sin ventana: sirve por SSH con el tunel de arriba
```

**`reconocer_letra.py` necesita sesión gráfica local (`DISPLAY` seteado).** Ojo con esta trampa:
**conectar un monitor por cable a la Jetson no alcanza si lo corrés por SSH** — una sesión SSH es
un canal aparte, no hereda el `DISPLAY` de la sesión gráfica que arrancó en ese monitor. Hace
falta estar sentado físicamente en la Jetson (con su propio teclado) para que abra sin error
`Can't initialize GTK backend`. Por SSH, usar `reconocer_letra_stream.py` en cambio.

`q` con foco en la ventana, o Ctrl+C en la consola, para cortar. Si la cámara no abre, casi
siempre es otro proceso que la tiene tomada:

```bash
ps aux | grep -E "probar_manos|reconocer_letra" | grep -v grep
```

Y si corriste algo y no ves el cambio esperado (por ejemplo, la matriz no reacciona), confirmá
que el archivo que corriste es el que creés que es — un `scp` viejo sin repetir después de un
cambio es un clásico:

```bash
grep -n "enviar_a_matriz" reconocer_letra.py
```
