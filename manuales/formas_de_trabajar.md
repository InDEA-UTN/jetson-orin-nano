# Formas de trabajar con la placa

Las distintas maneras de llegar a la Jetson y de correr código en ella, con un ejemplo mínimo de
cada una — el que se pega en una terminal y anda. Dos ejes, independientes entre sí: **cómo se
llega** a la placa y **dónde corre** el código. Cada fila dice si ya se probó en esta placa o si
todavía está pendiente.

**Escrito el 2026-08-20**, contra JetPack 6.2.3 / L4T 36.5.2, usuario del sistema `indea`.

## Cómo se llega a la placa

### Monitor, teclado y mouse

**Probado.** Es lo que se usó para el primer arranque, para leer la versión de firmware en el
menú UEFI (hay que estar tocando **Esc** desde el instante en que se enchufa la fuente, la placa
no tiene botón de encendido) y para completar la configuración inicial de Ubuntu. Después de eso
no hizo falta de nuevo.

Ver [`03_firmware_y_version_de_jetpack.md`](../guia_de_iniciacion/03_firmware_y_version_de_jetpack.md)
y [`04_instalacion_en_microsd.md`](../guia_de_iniciacion/04_instalacion_en_microsd.md).

### SSH desde otra máquina

**Probado — el uso diario real.** Por IP directa:

```bash
ssh indea@<ip_de_la_jetson>
```

Por nombre mDNS (`ssh indea@ubuntu.local`) **no anduvo** en la red del laboratorio: WiFi y
Ethernet quedan en subredes separadas y el multicast de mDNS no cruza entre ellas, aunque el
tráfico unicast (la IP directa) sí. Conviene anotar la IP con `hostname -I` antes de apagar la
placa. Detalle completo en [`06_puesta_a_punto.md` §0](../guia_de_iniciacion/06_puesta_a_punto.md#0-conectarse-por-ssh)
y en [`problemas_frecuentes.md`](problemas_frecuentes.md#red).

Como caso puntual, también se usó SSH sobre la **red virtual que crea SDK Manager por USB**
durante el flasheo (`ssh indea@192.168.55.1`), para diagnosticar una falla de DNS mientras el
flasheo estaba en curso — ver
[`05_instalacion_en_ssd_nvme.md` §6.4](../guia_de_iniciacion/05_instalacion_en_ssd_nvme.md#64-falla-de-dns-al-verificar-conectividad-paso-install-sdk-components).
Esa IP es temporal, solo existe durante el flasheo, y no sirve para el uso diario.

### VS Code por *Remote SSH*

**Pendiente.** No se probó todavía en esta placa.

### Jupyter en la placa, navegador en la PC

**Pendiente.** No se probó todavía.

### Consola serie por USB / red por USB-C

**Pendiente como salvavidas real.** El header J14 tiene los pines de consola serie (RXD/TXD/GND
en 3, 4 y 7) documentados en [`00_antes_de_empezar.md`](../guia_de_iniciacion/00_antes_de_empezar.md#1-vocabulario-mínimo)
como alternativa para leer el firmware sin monitor, pero no hizo falta usarla: siempre hubo
monitor disponible. Sigue como plan B sin probar todavía.

## Dónde corre el código

### Directo sobre el sistema (nativo)

**Probado.** Es como se hizo toda la parte de cámara: configuración del conector CSI, captura y
streaming con GStreamer.

```bash
gst-launch-1.0 nvarguscamerasrc num-buffers=1 sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=3840,height=2160' ! nvjpegenc ! \
  filesink location=~/captura.jpg
```

Ver [`camara_referencia.md`](camara_referencia.md) para el resto de los pipelines que ya
funcionan.

### Entorno virtual de Python

**Probado.** Es el camino usado para MediaPipe + OpenCV en el proyecto del espejo facial. Dos
detalles que costaron y conviene no volver a descubrir: hace falta `sudo apt install
python3.10-venv`, y si el código necesita que OpenCV lea la cámara CSI hay que usar el
`python3-opencv` **del sistema** (el único compilado con GStreamer) creando el venv con
`--system-site-packages`:

```bash
sudo apt install python3.10-venv python3-opencv
python3 -m venv --system-site-packages ~/mi_entorno
source ~/mi_entorno/bin/activate
```

La cadena completa de trampas (el `opencv-contrib-python` que se cuela como dependencia y tapa al
del sistema, y el choque de `numpy` 2.x con el `matplotlib` del sistema) está documentada en
[`../proyectos/espejo_facial_led/lado_jetson.md`](../proyectos/espejo_facial_led/lado_jetson.md).
Para lo que necesita CUDA/TensorRT, en cambio, el camino sigue siendo el contenedor.

### Contenedores de NVIDIA (`jetson-containers` / imágenes `dustynv/*`)

**Probado.** Es el camino usado para el primer ejemplo de inferencia, con el repo
`dusty-nv/jetson-inference`:

```bash
cd ~/primerainferencia/jetson-inference
./docker/run.sh --container dustynv/jetson-inference:r36.3.0
# ya adentro del contenedor:
imagenet.py --headless /jetson-inference/data/images/orange_0.jpg /jetson-inference/data/images/output_0.jpg
```

El tag que el script detecta solo (a partir del L4T exacto de la placa, acá `r36.5.2`) puede no
existir publicado — hay que forzar uno cercano de la misma rama `r36.x` con `--container`, no con
`--tag`. Detalle completo en
[`08_primer_ejemplo_de_inferencia.md`](../guia_de_iniciacion/08_primer_ejemplo_de_inferencia.md).

### Contenedor propio a partir de uno de NVIDIA

**Pendiente.** Todavía no hubo un proyecto propio que necesitara empaquetar su propio `Dockerfile`
sobre una imagen base de NVIDIA.

## Con qué seguir

Esta tabla se completa a medida que se prueba cada forma pendiente — cuando eso pase, actualizar
la fila correspondiente acá mismo en vez de duplicarlo en otro lado. Para el detalle paso a paso de
lo ya probado, seguir los enlaces a [`../guia_de_iniciacion/`](../guia_de_iniciacion/).
