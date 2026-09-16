# Jetson — abecedario de señas

Esta carpeta tiene el código que corre **en la Jetson, con la cámara real**, a diferencia de
`../entrenamiento/`, que corre una sola vez en una PC de escritorio sobre fotos de un dataset.
Ninguno de estos scripts guarda nada en disco (ni imágenes ni video). `probar_manos.py` corre por
SSH sin monitor (solo imprime texto); `reconocer_letra.py` en cambio abre una ventana local con
los landmarks dibujados, así que necesita un monitor conectado a la Jetson (ver su sección más
abajo).

Para el porqué de cada decisión (de dónde salen los 63 números, por qué KNN, la trampa de
versiones entre la PC y la Jetson) ver el **[README principal del proyecto](../README.md)** —
este archivo es solo la guía práctica de esta carpeta.

## Los tres archivos

### `manos.py` — no es un script, es la lógica compartida

No se corre solo. Lo importan tanto `reconocer_letra.py` (acá) como
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

### `reconocer_letra.py` — Fases 4 y 5: clasificar letra en vivo, con ventana y estabilizador

El script real del proyecto. Igual que `jetson_face.py` del espejo facial: abre una ventana local
(`cv2.imshow`) con los landmarks dibujados sobre el video y el estado actual en texto, en vez de
imprimir solo por consola. Por cada frame con mano detectada:

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

Cerrar con `q` (con foco en la ventana) o Ctrl+C en la consola. **Ya probado con éxito**
(clasificación) — el estabilizador y la ventana son la incorporación de esta sesión, falta la
prueba de punta a punta. Ver "Fases" y los resultados en el README principal.

## Cómo correrlo

Necesita, en el venv de la Jetson (el mismo que ya usa `probar_manos.py`, con mediapipe/opencv):

```bash
pip install "scikit-learn==1.7.2" joblib
```

**Importante**: esa versión de scikit-learn tiene que coincidir con la que se usó para generar
`abecedario_modelo.pkl` en la PC de escritorio (ver "Compatibilidad de versiones" en el README
principal) — si no coincide, `joblib.load()` puede no tirar error pero sí un
`InconsistentVersionWarning`, sin garantía de que el resultado sea correcto.

Con `abecedario_modelo.pkl` copiado a esta misma carpeta, **y un monitor conectado a la Jetson**
(sesión gráfica activa, `DISPLAY` seteado — si se corre por SSH sin `-X` y sin monitor físico,
`cv2.imshow` no tiene dónde abrir la ventana y el script corta con error):

```bash
python3 reconocer_letra.py
```

`q` con foco en la ventana, o Ctrl+C en la consola, para cortar. Si la cámara no abre, casi
siempre es otro proceso que la tiene tomada:

```bash
ps aux | grep -E "probar_manos|reconocer_letra" | grep -v grep
```

## Qué falta acá

Según el plan del proyecto (ver "Próximos pasos" en el README principal), a este script todavía
le falta el **envío por UDP a la Pico W** con el sprite de la letra ya confirmada por el
estabilizador (pasos 6 y 7: diseñar la fuente de cada letra y mandarla por el protocolo ya
armado). Hoy `reconocer_letra.py` clasifica y estabiliza la letra y la muestra en pantalla, pero
todavía no manda nada a la matriz de LEDs.
