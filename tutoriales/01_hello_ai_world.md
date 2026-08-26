# 01 — Hello AI World

## Objetivo

Poner a andar el primer modelo de IA en la Jetson con **jetson-inference**: clasificar una imagen
fija y después el video en vivo de la cámara, entendiendo qué hace cada pieza (Docker, la GPU vía
TensorRT, y cómo ver el resultado sin tener un monitor conectado a la placa).

**Base:** [`dusty-nv/jetson-inference`](https://github.com/dusty-nv/jetson-inference) — *Hello AI
World*. No es un resumen del tutorial oficial: es lo que salió al hacerlo en esta placa puntual.

## Requisitos previos

- [`06_puesta_a_punto.md`](../guia_de_iniciacion/06_puesta_a_punto.md) de la guía de iniciación:
  Docker con el runtime `nvidia` activo (§4 de ese documento).
- [`07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md): la cámara conectada y detectada.
- La clasificación sobre imagen fija ya se había probado en
  [`08_primer_ejemplo_de_inferencia.md`](../guia_de_iniciacion/08_primer_ejemplo_de_inferencia.md)
  de la guía de iniciación — acá se retoma ese resultado y se suma lo que faltaba: la cámara en
  vivo.

## Versiones

- Placa: L4T `R36.5.2` (JetPack 6.2.3).
- Imagen de contenedor usada: `dustynv/jetson-inference:r36.3.0` — no existe una imagen publicada
  para `r36.5.2` exacto (ver "Problemas frecuentes").
- Modo de energía: **MAXN SUPER** (ver [`06_puesta_a_punto.md`](../guia_de_iniciacion/06_puesta_a_punto.md#2-modo-de-energía-maxn-super)).

## Pasos

### 1. Clonar el repo y entrar al contenedor

```bash
git clone https://github.com/dusty-nv/jetson-inference ~/primerainferencia/jetson-inference
cd ~/primerainferencia/jetson-inference
./docker/run.sh --container dustynv/jetson-inference:r36.3.0
```

Deja una shell dentro del contenedor (`root@ubuntu:/opt/jetson-inference#`), con la cámara
(`/dev/video0`) y las carpetas de datos del host ya montadas.

### 2. Clasificar una imagen fija

```bash
imagenet.py --headless /jetson-inference/data/images/orange_0.jpg /jetson-inference/data/images/output_0.jpg
```

Resultado: `imagenet: 96.61% class #950 (orange)`. El detalle completo de este paso (la trampa del
tag de la imagen Docker, la del `--headless`) ya está documentado en
[`08_primer_ejemplo_de_inferencia.md`](../guia_de_iniciacion/08_primer_ejemplo_de_inferencia.md) —
no se repite acá.

### 3. Clasificar el video en vivo de la cámara

Mismo programa, apuntado a la cámara (`csi://0`) en vez de a un archivo. Como la Jetson no tiene
monitor, el resultado se transmite por la red hacia la PC en vez de mostrarse en una pantalla
local — mismo mecanismo de streaming que se armó a mano en
[`07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md#5-vista-en-vivo-transmitida-por-red),
pero acá `imagenet.py` arma el pipeline de captura + IA + codificación + envío internamente.

**En la Jetson** (dentro del contenedor):

```bash
imagenet.py --headless --log-level=warning csi://0 rtp://<ip_de_la_PC>:1234
```

**En la PC** (terminal nueva, no la sesión SSH — arrancar esto primero, antes que el comando de
la Jetson):

```bash
gst-launch-1.0 -v udpsrc port=1234 \
  caps="application/x-rtp, media=(string)video, encoding-name=(string)H264, payload=(int)96" ! \
  rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

Se abre una ventana en la PC con el video en vivo de la cámara, con la clase y el porcentaje de
confianza dibujados encima de cada cuadro, actualizándose en tiempo real.

**Foto:** [`imagenes/01_clasificacion_en_vivo.jpg`](imagenes/01_clasificacion_en_vivo.jpg) —
captura de la ventana de video mostrando el porcentaje de confianza al apuntar la cámara a un
teclado.

## Verificación final

La ventana de video en la PC muestra el feed de la cámara en vivo, con una etiqueta de clase y
porcentaje que cambia cuadro a cuadro según lo que la cámara está viendo.

## Resultados medidos

- **Tiempo de inferencia por cuadro** (GoogLeNet, FP16, modo **MAXN SUPER**): con la cámara en
  vivo y la GPU ya en régimen (varios cuadros seguidos), el reporte de TensorRT dio
  **~4.1 ms de CUDA / ~5.05 ms de CPU total** por cuadro. Muy por debajo de los ~185 ms que había
  tardado la primera corrida en frío sobre una imagen fija en el paso 2 — la diferencia es el
  reloj de la GPU: en una corrida única y aislada, el chip todavía no subió de frecuencia (DVFS),
  algo que la propia TensorRT avisa en su log (*"run 'sudo jetson_clocks' before, for more
  accurate profiling"*). En uso sostenido, el rendimiento real es el que se ve acá.
- **FPS, uso de RAM y temperatura**: *(completar — no se registraron en esta sesión; se pueden
  sacar con `jtop` corriendo en paralelo la próxima vez)*.

## Problemas frecuentes

| Problema | Causa | Solución |
|----------|-------|----------|
| `docker: ... dustynv/jetson-inference:r36.5.2: not found` | `docker/run.sh` arma el tag de la imagen a partir de la versión exacta de L4T de la placa (`R36.5.2`), pero el proyecto no publica una imagen por cada versión de L4T — la más nueva es `r36.3.0`. | Forzar el tag con `-c` / `--container` (no `--tag`, ese flag no existe y se ignora con un warning): `./docker/run.sh --container dustynv/jetson-inference:r36.3.0`. |
| `Fatal Python error: Segmentation fault` al terminar `imagenet.py` | La librería intenta crear una ventana OpenGL/X11 aunque no haga falta (por ejemplo, al escribir a un archivo); sin servidor X (SSH sin monitor), falla, y la limpieza de ese contexto choca con la de CUDA al cerrar. Pasa **después** de guardar el resultado, no lo afecta. | Agregar el flag `--headless` a cualquier comando de `jetson-inference`. |
| No llega nada a la ventana de la PC al probar la cámara en vivo por RTP | El firewall de la PC (`ufw`), con política por defecto "deny incoming", bloquea el puerto UDP usado para el streaming. Mismo problema que ya había aparecido en 07 con otro puerto. | `sudo ufw allow 1234/udp` en la PC receptora, antes de reintentar. |

## Cuánto llevó

*(completar — no se cronometró esta sesión de punta a punta; a ojo, la parte más lenta fue la
descarga de la imagen de Docker, ~7 GB)*.

## Con qué seguir

[`02_deteccion_de_objetos.md`](02_deteccion_de_objetos.md): el mismo tipo de recorrido, pero con
`detectnet` — detección de varios objetos con recuadro y etiqueta, y comparando fps entre modos de
energía.
