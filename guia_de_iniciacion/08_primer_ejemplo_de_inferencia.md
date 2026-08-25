# 08 — Primer ejemplo de inferencia

Un primer ejemplo de punta a punta: clasificar una imagen con un modelo de IA corriendo sobre la
GPU de la Jetson, entendiendo qué hace cada parte del camino.

> **Estado.** Verificado en la placa el **2026-08-20**: clasificación sobre una imagen fija
> funcionando de punta a punta (contenedor + TensorRT + GoogLeNet). La inferencia en vivo sobre el
> video de la cámara no entró en esta sesión —se probó solo con imagen fija— y se resolvió después,
> en [`../tutoriales/01_hello_ai_world.md`](../tutoriales/01_hello_ai_world.md).

**Antes hay que haber hecho** [`06_puesta_a_punto.md`](06_puesta_a_punto.md) (Docker con el
runtime `nvidia` activo, §4 de ese documento) y [`07_camara_csi.md`](07_camara_csi.md) — aunque
este primer ejemplo todavía no usa la cámara, solo una imagen de prueba.

## Por qué `jetson-inference` y por qué en Docker

**`jetson-inference`** (también conocido como *Hello AI World*) es el proyecto de NVIDIA/dusty-nv
con ejemplos listos de clasificación, detección y segmentación sobre cámara, ya citado como fuente
en [`00_antes_de_empezar.md` §5](00_antes_de_empezar.md). En vez de compilarlo a mano en la placa,
se corre en un **contenedor Docker** ya armado — es el camino que esta guía eligió como principal
desde el arranque ([§3.5 de `00_antes_de_empezar.md`](00_antes_de_empezar.md)): más robusto, sin
pelear con versiones de CUDA/TensorRT/librerías instaladas a mano.

## 1. Clonar el repositorio

```bash
git clone https://github.com/dusty-nv/jetson-inference ~/primerainferencia/jetson-inference
```

## 2. Correr el contenedor — trampa real de versión

El script `docker/run.sh` del propio repo lee la versión de L4T de la placa y busca en Docker Hub
una imagen con ese tag exacto:

```bash
cd ~/primerainferencia/jetson-inference
./docker/run.sh
```

```
L4T BSP Version:  L4T R36.5.2
CONTAINER_IMAGE:  dustynv/jetson-inference:r36.5.2
Unable to find image 'dustynv/jetson-inference:r36.5.2' locally
docker: Error response from daemon: failed to resolve reference "docker.io/dustynv/jetson-inference:r36.5.2": ... not found
```

**Causa real:** nuestra placa reporta L4T `R36.5.2` (JetPack 6.2.3), pero `dustynv/jetson-inference`
no publica una imagen para cada versión de L4T — la más nueva que existe en Docker Hub para este
proyecto es **`r36.3.0`**. El script busca el tag exacto y no lo encuentra.

**Solución:** forzar el tag más cercano con el flag correcto — es `-c` / `--container`, **no**
`--tag` (ese da un warning y se ignora silenciosamente):

```bash
./docker/run.sh --container dustynv/jetson-inference:r36.3.0
```

Al ser la misma generación L4T 36.x, corre sin problema. Te deja adentro del contenedor, con la
cámara (`/dev/video0`) y las carpetas de datos ya montadas:

```
root@ubuntu:/opt/jetson-inference#
```

## 3. Primera clasificación (`imagenet.py`)

```bash
imagenet.py --headless /jetson-inference/data/images/orange_0.jpg /jetson-inference/data/images/output_0.jpg
```

La primera vez que corre un modelo, **TensorRT** prueba distintas "tácticas" de cómputo para cada
capa de la red y arma un motor optimizado para esta GPU en particular — de ahí la cantidad enorme
de líneas `[TRT] Tactic Name: ...` que tira la primera corrida. Ese motor queda cacheado en un
archivo `.engine`, así que las corridas siguientes son casi instantáneas.

Resultado real:

```
imagenet:  96.61% class #950 (orange)
[image]  saved '/jetson-inference/data/images/output_0.jpg'  (1024x683, 3 channels)
```

Clasificó bien la imagen de prueba (una naranja) con 96.61% de confianza. Todo el pipeline —
CUDA, TensorRT, el contenedor — funciona de punta a punta.

### Trampa menor: ruta relativa

El primer intento fue con rutas relativas (`imagenet.py images/orange_0.jpg output_0.jpg`) y
falló con `failed to find 'images/orange_0.jpg'`: el directorio de trabajo dentro del contenedor
no es donde están las imágenes de ejemplo. Hay que usar la ruta completa,
`/jetson-inference/data/images/...`, como en el comando de arriba.

### Trampa real: segfault al cerrar (uso headless)

Sin el flag `--headless`, el mismo comando termina con:

```
[OpenGL] failed to open X11 server connection.
[OpenGL] failed to create X11 Window.
...
Fatal Python error: Segmentation fault
```

**Causa:** `jetson-utils` intenta crear una ventana de salida por OpenGL/X11 aunque el destino sea
un archivo. Como la Jetson se usa por SSH sin monitor conectado, no hay servidor X — esa creación
falla, y al cerrar el proceso la limpieza de ese contexto gráfico a medio inicializar choca con la
limpieza del contexto de CUDA, lo que dispara el segfault (a veces se ve como
`double free or corruption` en vez de `Segmentation fault`, según el momento exacto).

**Importante:** el crash pasa **después** de calcular y guardar el resultado — nunca afecta la
clasificación en sí, solo ensucia el cierre del proceso (a veces deja la terminal rara, hay que
`Ctrl+C`). El flag `--headless` evita que intente crear la ventana y con eso el problema no ocurre.

## 4. Dónde ver el resultado

El contenedor tiene montada la carpeta `data/` del host, así que `output_0.jpg` (la imagen de
entrada con la clase y el porcentaje dibujados encima) también queda accesible **fuera** del
contenedor, en la Jetson normal:

```
~/primerainferencia/jetson-inference/data/images/output_0.jpg
```

Para verlo, traerlo a la PC (desde una terminal en la PC, no en la sesión SSH a la Jetson):

```bash
scp indea@<ip_de_la_jetson>:~/primerainferencia/jetson-inference/data/images/output_0.jpg ~/Downloads/
```

## Qué queda pendiente

- **Inferencia en vivo sobre la cámara** — **ya resuelto**, pero fuera de este documento: correr
  `imagenet.py` o `detectnet.py` apuntando a `csi://0` en vez de a un archivo, y mandar la salida
  por RTP a la PC. Está en [`../tutoriales/01_hello_ai_world.md`](../tutoriales/01_hello_ai_world.md)
  (clasificación) y [`../tutoriales/02_deteccion_de_objetos.md`](../tutoriales/02_deteccion_de_objetos.md)
  (detección, con tiempos medidos por modo de energía).
- **Control PTZ** de la ArduCam (pan/tilt/zoom): sigue pendiente desde
  [`07_camara_csi.md`](07_camara_csi.md).

## Con qué seguir

Acá termina el recorrido de esta guía de arranque inicial (00 a 08): la placa está instalada,
configurada, con la cámara funcionando y un primer ejemplo de IA corriendo de punta a punta.

Lo que sigue ya no es iniciación. El paso natural son los
[`../tutoriales/`](../tutoriales/), que retoman esto mismo sobre el video en vivo de la cámara; y
después, el PTZ y entrenar modelos propios, que son trabajo de proyecto sobre esta base.
