# Espejo Facial en Matriz LED

Réplica de expresiones faciales en tiempo real sobre una matriz LED 8×8.
Plataforma: NVIDIA Jetson Orin Nano + Raspberry Pi Pico W.

- **Responsable:** Lisandro Elmelaj ([@lisandroelmelaj](https://github.com/lisandroelmelaj))
- **Revisor:** Javier Velez ([@javovelez](https://github.com/javovelez))
- **Estado:** En curso — fase 0
- **Requisitos previos:** la placa andando con JetPack 6 y la cámara funcionando; ver la
  [guía de iniciación](../../guia_de_iniciacion/).

El código de ambos lados va en esta misma carpeta a medida que se escribe.

---

## 1. Objetivo

Construir un sistema que capture el rostro de una persona por cámara, detecte sus gestos (ojos,
cejas y boca) mediante visión por computador, y los reproduzca en vivo sobre una matriz de LEDs de
8×8 píxeles.

El resultado es una "carita" digital que parpadea, abre la boca y levanta las cejas imitando al
usuario, con una latencia inferior a 100 ms.

---

## 2. Arquitectura del sistema

```
┌─────────────────────┐                    ┌──────────────────┐
│  JETSON ORIN NANO   │                    │   PICO W         │
│                     │                    │                  │
│  Cámara USB/CSI     │                    │  WiFi (rx UDP)   │
│        ↓            │      WiFi          │       ↓          │
│  OpenCV (captura)   │  ─────────────▶    │  SPI             │
│        ↓            │   8 bytes/frame    │       ↓          │
│  MediaPipe FaceMesh │   ~30 veces/seg    │  MAX7219         │
│        ↓            │                    │       ↓          │
│  Cálculo EAR/MAR    │                    │  Matriz 8×8      │
│        ↓            │                    │                  │
│  Sprite 8×8         │                    │                  │
└─────────────────────┘                    └──────────────────┘
      "EL CEREBRO"                            "LA CARA"
   Ve y decide qué expresión               Dibuja lo que le mandan
```

**Regla de oro del diseño:** la Jetson nunca toca un LED. El Pico nunca ve una imagen.

---

## 3. Justificación: ¿por qué dos procesadores?

La pregunta legítima es: *la Jetson tiene pines SPI, podría manejar el MAX7219 directamente. ¿Para
qué agregar un microcontrolador?*

Se puede hacer, pero la separación es superior por seis razones:

### 3.1. Tiempo real duro vs. tiempo real blando

Es el argumento más importante.

La Jetson corre Ubuntu, un sistema operativo de propósito general con un planificador **no
determinista**. Cuando el kernel decide atender una interrupción de red, o el garbage collector de
Python se activa, tu proceso se pausa unos milisegundos. En una tarea de visión eso es invisible.
En el refresco de una matriz LED, produce un **parpadeo visible**.

El RP2040 corre el código *bare-metal*: no hay sistema operativo, no hay otro proceso compitiendo.
El timing del SPI es perfectamente estable. Es la herramienta correcta para la tarea.

### 3.2. Protección del hardware caro

Los pines GPIO de la Jetson son delicados: 3.3 V, poca capacidad de corriente, y **sin protección
contra sobretensión**. Un error de cableado o un pico inductivo de los LEDs puede dañar el módulo.

- Orin Nano dañada: ~250 USD y semanas de espera
- Pico W quemado: ~6 USD y otro en el cajón

Poner un microcontrolador barato como "sacrificio" entre el mundo analógico ruidoso y el procesador
caro es práctica estándar en la industria.

### 3.3. Aislamiento eléctrico y de ruido

Una matriz de 64 LEDs multiplexada genera transitorios de corriente en cada cambio de dígito. Ese
ruido, acoplado a la línea de alimentación de la Jetson, puede provocar desde artefactos en la
captura hasta reinicios espontáneos. Con fuentes separadas, el problema desaparece por
construcción.

### 3.4. Desacople del desarrollo

Al definir un contrato claro (8 bytes por UDP), los dos lados se desarrollan y depuran **de forma
independiente**:

- El lado Pico se prueba con un script de 5 líneas que manda sprites fijos, sin cámara ni
  MediaPipe.
- El lado Jetson se prueba imprimiendo el sprite en consola como ASCII art, sin hardware.

Si el proyecto lo hicieran dos personas, pueden trabajar en paralelo desde el día uno.

### 3.5. Modularidad física

La cámara tiene que estar donde está la cara del usuario. La matriz LED puede estar donde uno
quiera: en otra mesa, dentro de una escultura, en la otra punta del taller. Con WiFi, la distancia
es irrelevante. Con SPI directo, estás atado a 20 cm de cable.

### 3.6. Valor pedagógico

El proyecto atraviesa tres dominios completos:

| Dominio | Qué aprende |
|---|---|
| Visión por computador | Landmarks faciales, métricas geométricas (EAR/MAR), suavizado temporal |
| Sistemas embebidos | SPI, drivers de display, MicroPython |
| Redes / protocolos | Diseño de un protocolo binario, UDP vs. TCP, latencia |

Si todo corriera en la Jetson, el tercer dominio desaparece y el segundo se reduce a llamar una
librería.

### Contrapartida honesta

La separación agrega **latencia de red** (típicamente 5–15 ms en WiFi local) y un punto de fallo
adicional. Para este caso de uso es despreciable: el ojo humano no percibe el retardo por debajo de
~100 ms, y tenemos margen de sobra.

---

## 4. Justificación de la plataforma: ¿por qué Orin Nano?

Vale aclararlo, porque el proyecto original que inspira este trabajo corre en una PC común con un
ESP32.

**Lo que aporta la Orin Nano:**

1. **Autonomía.** El sistema completo funciona sin una laptop conectada. Es un dispositivo, no una
   demo.
2. **Ecosistema moderno.** JetPack 6 trae Ubuntu 22.04 y Python 3.10, con lo cual las librerías de
   ML instalan sin fricción (ver sección 6).
3. **Techo alto.** Tiene 1024 núcleos CUDA y Tensor Cores que este proyecto **no usa**. Eso es
   deliberado: la versión 1 no los necesita, pero habilita una versión 2 que sería imposible en
   otra plataforma.

**Advertencia importante para no confundirse:** existe una Jetson **Nano** (2019) que es un
producto completamente distinto y mucho más limitado. Casi todos los tutoriales de internet sobre
"MediaPipe en Jetson" se refieren a esa placa vieja y describen procesos de compilación manual con
Bazel que **no aplican acá**. Ignorarlos.

**Extensiones posibles para la versión 2** (todas requieren la GPU):

- Reconocimiento de emociones con una CNN propia acelerada por TensorRT
- Múltiples caras simultáneas, cada una controlando su propia matriz
- Estimación de mirada precisa con seguimiento de iris
- Modelo entrenado por el propio alumno con TAO Toolkit

---

## 5. Lista de materiales

| Componente | Cantidad | Notas |
|---|---|---|
| Jetson Orin Nano | 1 | Con JetPack 6.x flasheado |
| Raspberry Pi Pico 2040**W** | 1 | La "W" es obligatoria: necesita WiFi |
| Módulo MAX7219 + matriz 8×8 | 1 | El módulo **integrado**, no la matriz suelta |
| Cámara USB (webcam) o CSI IMX219 | 1 | Cualquiera de 720p sirve |
| Fuente 5 V / 2 A | 1 | Para el Pico + matriz, separada de la Jetson |
| Cables Dupont hembra-hembra | 5 | |
| Protoboard | 1 | Opcional |

**Costo aproximado del lado Pico:** 12–15 USD.

Antes de comprar, revisá el inventario del laboratorio: la Jetson y un par de Picos ya están. Del
Pico hay que confirmar que sea la variante **W**; sin WiFi no sirve para este proyecto.

---

## 6. Preparación del entorno

En la Orin Nano con JetPack 6 (Ubuntu 22.04, Python 3.10):

```bash
pip install mediapipe opencv-python
```

Eso debería ser todo. MediaPipe publica wheels oficiales para aarch64 compatibles con Python 3.10,
así que no hace falta compilar nada.

**Verificar esto en los primeros 15 minutos del proyecto**, antes de comprar o soldar nada:

```python
import mediapipe as mp
import cv2
print(mp.__version__)   # si esto imprime una versión, el camino está despejado
```

*Plan B si algo falla:* usar **dlib** con su predictor de 68 puntos. Compila sin problemas y 68
puntos son de sobra para una salida de 8×8 píxeles. No es un downgrade significativo para este
proyecto.

---

## 7. Conexionado

### MAX7219 → Pico W

| MAX7219 | Pico W | Pin físico |
|---|---|---|
| VCC | VBUS (5 V) | 40 |
| GND | GND | 38 |
| DIN | GP3 (SPI0 TX) | 5 |
| CS | GP5 | 7 |
| CLK | GP2 (SPI0 SCK) | 4 |

**Nota sobre niveles lógicos:** el Pico emite 3.3 V y el MAX7219 alimentado a 5 V especifica un
umbral de "HIGH" de ~3.5 V. En la práctica funciona sin problemas. Si aparece parpadeo o píxeles
fantasma, la solución es intercalar un buffer 74HCT125 en las líneas DIN/CLK/CS.

---

## 8. Pipeline técnico

### Lado Jetson (Python)

1. **Captura**: OpenCV lee frames de la cámara a 30 FPS.
2. **Detección**: MediaPipe Face Mesh devuelve 468 landmarks 3D normalizados.
3. **Extracción de métricas**, usando solo un puñado de puntos:

   | Gesto | Landmarks clave | Métrica |
   |---|---|---|
   | Parpadeo ojo izq. | 33, 133, 159, 145 | EAR (Eye Aspect Ratio) |
   | Parpadeo ojo der. | 362, 263, 386, 374 | EAR |
   | Cejas | 70, 105, 107 / 336, 334, 300 | Altura relativa al ojo |
   | Boca | 13, 14, 61, 291 | MAR (Mouth Aspect Ratio) |

4. **Suavizado**: media móvil de 3–5 frames sobre cada métrica, para eliminar el temblor del
   detector.
5. **Cuantización a estados discretos**: en lugar de mapear valores continuos a píxeles (queda
   ruidoso y feo), se definen estados:
   - Ojos: 3 niveles (abierto / entrecerrado / cerrado)
   - Cejas: 3 posiciones (normal / levantadas / fruncidas)
   - Boca: 4 formas (neutra / sonrisa / abierta / triste)
6. **Composición del sprite**: se combina el estado de cada rasgo en una matriz de 8×8 bits → 8
   bytes.
7. **Envío**: socket UDP al Pico, ~30 paquetes por segundo.

### Lado Pico W (MicroPython)

1. Conecta a la red WiFi.
2. Abre un socket UDP escuchando en un puerto fijo.
3. Por cada paquete de 8 bytes recibido, escribe el framebuffer al MAX7219 vía SPI.
4. Si no llega nada en 2 segundos, muestra una animación de "idle" (parpadeo lento).

**Complejidad total del lado Pico: unas 40 líneas de código.** El grueso del trabajo está en la
Jetson.

---

## 9. Protocolo de comunicación

Contrato mínimo y explícito:

```
Paquete UDP = 8 bytes
  byte[0] = fila 0 de la matriz (bit 7 = píxel izquierdo)
  byte[1] = fila 1
  ...
  byte[7] = fila 7

Bit en 1 = LED encendido
```

Se eligió **UDP sobre TCP** deliberadamente: si un frame se pierde, el siguiente llega 33 ms
después. No vale la pena pagar el costo de retransmisión y handshake para datos que caducan de
inmediato. Es el mismo criterio que usan los protocolos de video en vivo.

**Extensión futura:** si se agregan más matrices (ojos y boca por separado), basta anteponer un
byte de dirección. El resto del sistema no cambia.

---

## 10. Fases de ejecución sugeridas

| Fase | Objetivo | Criterio de éxito |
|---|---|---|
| **0** | Validar el entorno | `import mediapipe` funciona en la Orin Nano |
| **1** | Pico W enciende la matriz | Muestra una carita fija hardcodeada |
| **2** | Pico W recibe por WiFi | Un script manda sprites y se ven en la matriz |
| **3** | Jetson detecta landmarks | Ventana OpenCV con los 468 puntos sobre la cara |
| **4** | Jetson calcula métricas | EAR/MAR impresos en consola, reaccionan al parpadear |
| **5** | Jetson genera sprites | Sprite impreso en consola como ASCII art |
| **6** | Integración completa | La matriz imita la cara en tiempo real |
| **7** | Refinamiento | Ajuste de umbrales, suavizado, diseño de sprites |

Cada fase es verificable de forma aislada. Si algo falla en la fase 6, ya se sabe que 0–5
funcionan.

La fase 0 va primero **a propósito**: es la única con riesgo real de entorno, y se resuelve en
minutos. Conviene despejarla antes de invertir tiempo en el resto.

Como en el resto del repositorio, al documentar cada fase anotá las **versiones** con las que se
hizo (JetPack, L4T, MediaPipe, MicroPython) y los comandos y salidas reales, no reconstruidos.

---

## 11. Riesgos conocidos y mitigaciones

**Entorno de MediaPipe.** Riesgo bajo en JetPack 6, pero conviene validarlo en la fase 0. Plan B:
dlib con 68 puntos.

**Orientación de la matriz.** Es habitual que el sprite aparezca rotado 90° o espejado según el
módulo. **No se resuelve por hardware** — se agrega una transformación de la matriz en software
antes de enviarla. Presupuestar 15 minutos.

**Diseño de los sprites.** Este es el riesgo subestimado del proyecto. Hacer que 64 píxeles
monocromáticos transmitan una emoción reconocible es un problema de **diseño**, no de programación.
Conviene dibujar los sprites en papel cuadriculado antes de codificarlos, y presupuestar tiempo
real para iterar.

**Calibración de umbrales.** Los valores de EAR/MAR varían entre personas. El sistema necesita una
rutina simple de calibración (o umbrales relativos a un promedio de los primeros segundos) para no
funcionar solo con una cara.

**Rendimiento.** No es un riesgo en esta plataforma. Face Mesh corre holgado; el cuello de botella
será la cámara.

---

## 12. Referencias

- **MediaPipe Face Landmarker** — documentación oficial de los 468 puntos:
  https://developers.google.com/mediapipe/solutions/vision/face_landmarker
- **Proyecto de referencia (ESP32 + matriz 8×8)** — "Face to Pixels", el concepto original:
  https://www.youtube.com/watch?v=RTeqVTJCQNI
- **LumiFur Controller** — código abierto de expresiones faciales sobre matriz LED:
  https://github.com/stef1949/LumiFur_Controller
- **Detección de ojos, nariz y boca con MediaPipe** — tutorial con los índices de landmarks:
  https://medium.com/@Mert.A/detect-eyes-nose-and-mouth-with-mediapipe-bbfdf7a61f21
- **MicroPython MAX7219** — driver para el Pico: buscar `micropython-max7219` en GitHub

---

## 13. Entregables

1. Código fuente comentado de ambos lados (`jetson_face.py` y `main.py`).
2. Documento breve con el mapa de landmarks utilizados y los umbrales calibrados.
3. Video de 30 segundos mostrando el sistema funcionando.
4. Diagrama de conexionado final.

El código y la documentación van en esta misma carpeta. **El video no**: subilo al Drive del
laboratorio y dejá acá el enlace, para no meter binarios pesados en el repositorio.

El seguimiento del trabajo (bitácora, horas, objetivos) no va acá, como en todo este repositorio:
vive en el repositorio privado de gestión del laboratorio.
