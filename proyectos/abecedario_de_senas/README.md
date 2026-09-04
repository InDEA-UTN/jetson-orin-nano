# Abecedario de Señas LED

**Estado.** Recién arrancando (03/09/2026): decisiones de alcance tomadas, un script de la
fase 1 escrito pero **todavía no corrido en la placa**. Nada de esto está verificado en
hardware real todavía — ver "Próximos pasos" al final.

## Objetivo

Traducir el abecedario dactilológico (lenguaje de señas) a letras normales, mostrando cada
letra reconocida en la matriz LED 8×8, con el mismo equipo del proyecto
[`espejo_facial_led/`](../espejo_facial_led/): Jetson Orin Nano (cámara + MediaPipe), Raspberry
Pi Pico W (WiFi + matriz MAX7219), y el mismo protocolo UDP de 8 bytes entre las dos.

Es un proyecto separado del espejo facial (repos... o en este caso carpetas de proyecto
distintas dentro del mismo repo) porque el problema de fondo es otro: ahí se cuantizaban gestos
de cara con reglas simples sobre 1-2 métricas (EAR, MAR); acá hay que clasificar 24 poses de
mano distintas a partir de 21 puntos cada una, que es un problema de clasificación, no de
umbrales a mano — ver la sección "Por qué un clasificador y no reglas" más abajo.

## Decisiones de alcance ya tomadas

- **Abecedario: ASL (americano), no LSA.** 26 letras, con solo J y Z hechas con movimiento (las
  otras 24 son poses estáticas). Es el alfabeto con más documentación y modelos ya entrenados
  disponibles — más fácil de hacer andar bien en una primera versión que LSA, que tiene más
  letras con movimiento y menos material de referencia.
- **V1: solo letras estáticas.** Un solo frame de la mano, sin ventana temporal. J y Z quedan
  afuera, anotadas como fase futura si se agrega reconocimiento de movimiento.
- **Clasificador: se va a usar un modelo pre-entrenado, no grabar dataset propio.** Se evaluó la
  alternativa de grabar muestras propias (como el espejo facial calibra la cara neutra en vivo),
  pero se decidió partir de un modelo ya entrenado por otro proyecto para no tener que grabar 24
  letras × varias decenas de muestras antes de tener algo funcionando. Candidatos encontrados
  (todos MediaPipe landmarks + clasificador clásico, no red pesada sobre imágenes):
  - **[VivanRajath/ASL](https://github.com/VivanRajath/ASL)** — Random Forest sobre landmarks,
    trae los `.pkl` de modelo + scaler + label encoder ya entrenados, MIT, A-Z sin J/Z. El más
    directo de los encontrados.
  - Alternativas si el anterior no anda bien en la cámara/luz real del laboratorio:
    [ts42a/asl-landmark-classifier](https://github.com/ts42a/asl-landmark-classifier),
    [laplaces42/sign-language-interpreter](https://github.com/laplaces42/sign-language-interpreter),
    [Thishithasai406/signSpeak](https://github.com/Thishithasai406/signSpeak) (este último es
    CNN sobre imágenes, más pesado).
  - **Riesgo conocido:** un modelo pre-entrenado aprendió con la mano/cámara/luz de otra persona
    — puede andar peor que uno propio en este setup real. Si al probarlo no clasifica bien, la
    alternativa de grabar dataset propio (con el mismo patrón de calibración en vivo del espejo
    facial) sigue disponible sin tener que rehacer nada de las fases 1-2.
  - Todavía no se descargó ningún modelo ni se lo probó.

## Por qué un clasificador y no reglas escritas a mano

En el espejo facial cada gesto era una regla simple ("boca abierta si MAR > umbral"), viable con
4-5 gestos. Acá son 24 poses definidas por la posición relativa de 21 puntos (63 números);
escribir 24 reglas que no se pisen entre sí es inviable, y una regla a mano no generaliza bien a
manos de distinto tamaño o ángulo. Un clasificador (sea entrenado por otro o con dataset propio)
resuelve eso comparando contra ejemplos en vez de contra umbrales fijos.

## Arquitectura (plan, sin verificar todavía)

Mismo protocolo que el espejo facial: la Jetson procesa la cámara y manda un sprite de 8 bytes
por UDP a la Pico W, que lo dibuja en la matriz MAX7219. **La Pico W no necesita ningún cambio**
— [`../espejo_facial_led/pico/main.py`](../espejo_facial_led/pico/main.py) y
[`max7219.py`](../espejo_facial_led/pico/max7219.py) sirven tal cual, con el mismo formato de
byte por fila / bit 7 = píxel izquierdo (ver
[`../espejo_facial_led/README.md`](../espejo_facial_led/README.md) sección 9). Del lado Jetson
cambia todo: detector de manos en vez de cara, clasificador en vez de reglas, y una fuente de
5×7 para dibujar letras en vez de sprites de expresión facial.

## Fases

1. **Ver la mano.** [`jetson/probar_manos.py`](jetson/probar_manos.py) — confirmar que
   `HandLandmarker` de MediaPipe detecta una mano en la cámara de la Jetson y que los 21
   landmarks (incluidos los `world_landmarks` en metros, con profundidad) tienen sentido.
   **Escrito, no corrido todavía** — ver "Próximos pasos".
2. Convertir la mano en un vector normalizado (independiente de posición/tamaño de la mano),
   comparable con lo que espera el modelo pre-entrenado elegido.
3. Integrar el modelo pre-entrenado: cargarlo, clasificar cada frame, y un estabilizador
   temporal (repetir la misma letra varios frames seguidos antes de darla por buena) para que
   no titile con el ruido del detector — mismo rol que la media móvil de `gestos.py` en el
   espejo facial, pero sobre un valor discreto.
4. Fuente de 5×7 por letra y armado del sprite de 8 bytes.
5. Enviar por UDP a la Pico W y confirmar en la matriz real.

## Próximos pasos (para retomar en la próxima sesión)

1. **Descargar el modelo `hand_landmarker.task` en la Jetson** (con el venv del espejo facial
   activado, `~/espejo_facial_venv`):
   ```bash
   wget -O ~/hand_landmarker.task \
     https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
   ```
2. Copiar [`jetson/probar_manos.py`](jetson/probar_manos.py) a la Jetson y correrlo — es la
   fase 1, ver arriba.
3. Elegir y descargar uno de los modelos pre-entrenados candidatos (sección de arriba),
   probarlo contra los landmarks reales antes de integrarlo.
