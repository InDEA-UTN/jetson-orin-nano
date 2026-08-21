# 02 — Detección de objetos

## Objetivo

Detectar objetos en vivo sobre el video de la cámara con **`detectnet`** — a diferencia de la
clasificación de [`01_hello_ai_world.md`](01_hello_ai_world.md), que le pone una sola etiqueta a
todo el cuadro, acá se reconocen varios objetos a la vez, cada uno con su recuadro (*bounding
box*) y su clase. Además, medir el rendimiento real y compararlo entre dos modos de energía.

**Base:** [`dusty-nv/jetson-inference`](https://github.com/dusty-nv/jetson-inference) (`detectnet`).

## Requisitos previos

- [`01_hello_ai_world.md`](01_hello_ai_world.md): ahí se resolvió todo el "andamiaje" que este
  tutorial reusa tal cual — el contenedor con el tag correcto, el flag `--headless`, el puerto
  UDP abierto en el firewall de la PC. Acá no se repite nada de eso.
- [`06_puesta_a_punto.md`](../guia_de_iniciacion/06_puesta_a_punto.md#2-modo-de-energía-maxn-super)
  de la guía de iniciación: modos de energía con `nvpmodel`.

## Versiones

- Placa: L4T `R36.5.2` (JetPack 6.2.3). Mismo contenedor que en 01: `dustynv/jetson-inference:r36.3.0`.
- Modelo: **SSD-Mobilenet-v2**, entrenado sobre **COCO** (90 clases de objetos comunes) — el que
  trae `detectnet.py` por defecto, sin pedir ninguno en particular.

## Pasos

### 1. Entrar al contenedor

Igual que en 01 (mismo contenedor, no hace falta descargar nada de nuevo):

```bash
cd ~/primerainferencia/jetson-inference
./docker/run.sh --container dustynv/jetson-inference:r36.3.0
```

### 2. Detección en vivo por cámara

Mismo esquema que la clasificación en vivo de 01 — `detectnet.py` en vez de `imagenet.py`,
transmitido por RTP a la PC porque la Jetson no tiene monitor:

**Jetson** (dentro del contenedor):
```bash
detectnet.py --headless csi://0 rtp://<ip_de_la_PC>:1234
```

**PC** (arrancar primero):
```bash
gst-launch-1.0 -v udpsrc port=1234 \
  caps="application/x-rtp, media=(string)video, encoding-name=(string)H264, payload=(int)96" ! \
  rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

**Resultado real:** detectó una persona (parado frente a la cámara) con confianza entre **60% y
84%** según el cuadro, `ClassID 1` (`person` en COCO), con el recuadro dibujado y actualizándose
en vivo cuadro a cuadro.

**Foto:** [`imagenes/02_deteccion_en_vivo.jpg`](imagenes/02_deteccion_en_vivo.jpg) — captura de la
ventana de video con el recuadro y la etiqueta de persona detectada.

### 3. Comparar rendimiento entre modos de energía

Sin reiniciar nada — `nvpmodel` cambia de modo al instante.

```bash
sudo nvpmodel -q                # ver modo actual y modos disponibles
sudo nvpmodel -m 0               # modo 0 = 15W en nuestra placa
detectnet.py --headless csi://0 rtp://<ip_de_la_PC>:1234   # dejar unos segundos, Ctrl+C, anotar el Timing Report

sudo nvpmodel -m 2               # MAXN SUPER
detectnet.py --headless csi://0 rtp://<ip_de_la_PC>:1234   # repetir
```

## Verificación final

La ventana de video en la PC muestra el recuadro y la etiqueta sobre el objeto detectado,
actualizándose en tiempo real cuadro a cuadro.

## Resultados medidos

Promedio de 4-5 cuadros por modo, del `[TRT] Timing Report` de `detectnet.py` (SSD-Mobilenet-v2):

| Modo de energía | Network (solo inferencia) CUDA | Total (pre+red+post+dibujo) CUDA | Total CPU |
|---|---|---|---|
| **15W** (modo 0) | 10.78 ms | 12.14 ms | 11.82 ms |
| **MAXN SUPER** (modo 2) | 10.59 ms | 11.77 ms | 11.61 ms |

**MAXN SUPER es apenas ~3% más rápido** en este caso — mucho menos diferencia de la que
esperábamos después de ver el salto enorme en 01 (185ms en frío vs 4ms en régimen). La explicación:
acá se está comparando manzanas con manzanas (los dos modos con la cámara ya corriendo en
régimen, no una corrida única en frío), y **SSD-Mobilenet-v2 es un modelo liviano** — ni siquiera
el modo de 15W deja a la GPU sin margen. La ventaja de MAXN SUPER se va a notar mucho más con
modelos pesados (por ejemplo, algo tipo YOLO grande o un LLM), no con este.

De esos ~11-12 ms de cómputo por cuadro sale un **límite teórico de ~85-90 FPS** (1000 / ms), solo
contando el cómputo de IA — no es el FPS real de la transmisión completa (eso depende también de
la captura de la cámara y la codificación de video, que no se midieron por separado acá).

## Problemas frecuentes

Ninguno nuevo. Los tres que aparecieron en 01 (tag de la imagen Docker, `--headless` contra el
segfault al cerrar, y el puerto UDP bloqueado por el firewall) ya estaban resueltos de esa sesión
y siguieron funcionando sin tocar nada.

## Cuánto llevó

*(completar — bastante más rápido que 01: no hubo que descargar nada nuevo, se reusó el mismo
contenedor)*.

## Con qué seguir

[`03_entrenar_con_datos_propios.md`](03_entrenar_con_datos_propios.md): reentrenar un clasificador
con imágenes propias (*transfer learning*) y correrlo en la placa.
