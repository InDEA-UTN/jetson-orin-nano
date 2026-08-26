# Cámara — referencia rápida

Ficha técnica de la cámara CSI conectada a la Jetson: qué sensor es, qué resoluciones/fps tiene
disponibles, y los comandos exactos (configuración del conector, captura, streaming) que ya se
probaron y funcionan en esta placa. No es un tutorial paso a paso — para eso, con el diagnóstico
de cada trampa encontrada, ver [`../guia_de_iniciacion/07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md).

**Escrito sobre lo verificado en la placa el 2026-08-11.**

## Modelo

- **Cámara**: ArduCam UC-517 — PTZ (pan 360° / tilt 120° / zoom óptico 3x).
- **Sensor**: IMX477 (el mismo de la Raspberry Pi HQ Camera). Al ser IMX219/IMX477, JetPack trae
  driver de fábrica: se configura con `jetson-io.py`, sin compilar kernel.
- **Conector de la cámara**: 22 posiciones (igual que el de la Jetson) — cable **derecho de 22 a
  22 pines**, sin adaptador de por medio.
- **Conector usado en la Jetson**: **CAM1**.
- Fuente puntual que confirma este sensor con driver de fábrica en un Jetson Orin: hilo del foro
  de NVIDIA Developer sobre esta misma ArduCam UC-517 (IMX477) —
  <https://forums.developer.nvidia.com/t/arducam-imx477-uc-517-rev-d3-b0274-4-lane-configuation-on-cam1-of-orin-nx-16gb-development-kit/362367>.

## Elegir el sensor en el conector CSI (`jetson-io.py`)

```bash
sudo find / -iname "jetson-io.py" 2>/dev/null   # /opt/nvidia/jetson-io/jetson-io.py
sudo python3 /opt/nvidia/jetson-io/jetson-io.py
```

Camino de menú (texto) para esta cámara en CAM1:

```
Configure Jetson 22pin CSI Connector
  → Configure for compatible hardware
    → Camera IMX477-C          (la "C" es CAM1; "A" sería CAM0)
```

Al confirmar, acepta reiniciar — hace falta para que tome el *device tree overlay* nuevo. Queda
anotado en `/boot/extlinux/extlinux.conf`:

```
MENU LABEL Custom Header Config: <CSI Camera IMX477-C>
OVERLAYS /boot/tegra234-p3767-camera-p3768-imx477-C.dtbo
```

## Verificar que el sensor aparece

```bash
v4l2-ctl --list-devices
ls /dev/video* /dev/media*
```

Con el cable bien insertado, en esta placa: `/dev/media0` y `/dev/video0`.

Diagnóstico si no aparece nada (típicamente el flex mal insertado — ver el detalle completo, con
`dmesg` e `i2cdetect`, en 07 §3.1):

```bash
sudo dmesg | grep -iE "imx477|vi-output|tegra-camera|csi|camera"
sudo i2cdetect -y -r 9   # el IMX477 responde en 0x1a; "UU" significa que el driver ya lo tomó
```

## Resoluciones y fps disponibles (reportado por Argus en esta placa)

```
3840 x 2160  FR = 29.999999 fps
1920 x 1080  FR = 59.999999 fps
```

## Pipelines de GStreamer que funcionan

### Captura fija (JPEG)

```bash
gst-launch-1.0 nvarguscamerasrc num-buffers=1 sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=3840,height=2160' ! nvjpegenc ! \
  filesink location=~/primera_captura.jpg
```

Corre por SSH sin necesitar monitor ni X en la Jetson (`nvjpegenc` + `filesink`, nada que dibuje
en pantalla).

### Vista en vivo por streaming RTP/UDP hacia la PC

La Orin Nano **no tiene encoder de video por hardware (NVENC)** — solo decoder
(`nvv4l2decoder`). Por eso la codificación va por software con `x264enc`, siguiendo la
recomendación oficial de NVIDIA:
<https://docs.nvidia.com/jetson/archives/r36.2/DeveloperGuide/SD/Multimedia/SoftwareEncodeInOrinNano.html>.

Paquetes que hicieron falta instalar además de lo que trae JetPack:

```bash
# en la Jetson: h264parse vive en el paquete "bad"
sudo apt install -y gstreamer1.0-plugins-bad

# en la PC: el decodificador avdec_h264 vive en el paquete "libav"
sudo apt install -y gstreamer1.0-libav
```

**Emisor, en la Jetson** (captura, codifica por software y manda por UDP):

```bash
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=1920,height=1080,format=NV12,framerate=30/1' ! \
  nvvidconv ! video/x-raw,format=I420 ! \
  x264enc speed-preset=ultrafast tune=zerolatency ! \
  h264parse ! rtph264pay config-interval=1 pt=96 ! \
  udpsink host=<ip_de_la_PC> port=5000
```

**Receptor, en la PC** (arrancar primero, antes que el de la Jetson, para que quede esperando):

```bash
gst-launch-1.0 -v udpsrc port=5000 \
  caps="application/x-rtp, media=(string)video, encoding-name=(string)H264, payload=(int)96" ! \
  rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

Si no llega nada, antes de sospechar del pipeline probar conectividad simple con `nc` y revisar
el firewall de la PC (en este laboratorio, `ufw` bloqueaba el puerto UDP hasta abrirlo con
`sudo ufw allow 5000/udp`) — el detalle completo de este diagnóstico está en 07 §5.1.

## Pendiente: control PTZ

El control del motor de pan/tilt/zoom de la ArduCam UC-517 todavía no se investigó ni se probó en
la placa. Es una capa aparte del driver de imagen estándar (que solo expone el sensor como
`/dev/video0`) — probablemente haga falta software propio de ArduCam. No hay ningún comando
confirmado para anotar acá todavía.

## Con qué seguir

Para el diagnóstico completo de las dos trampas reales que aparecieron (el flex insertado al
revés, y por qué no llegaba el streaming) ver
[`../guia_de_iniciacion/07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md).
