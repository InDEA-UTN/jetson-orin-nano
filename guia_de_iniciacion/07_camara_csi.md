# 07 — Cámara CSI

Conectar la cámara al conector CSI, configurar el conector, verificar que el sensor aparece y
hacer la primera captura. La vista en vivo queda para más adelante (ver estado abajo).

> **Estado.** Verificado en la placa el **2026-08-11**: la cámara conecta, el sensor se detecta y
> la primera captura funcionó. **La primera vista en vivo todavía no se hizo** — queda pendiente
> junto con el control PTZ (motor de pan/tilt/zoom), que es una capa aparte.

**Antes hay que haber hecho** [`06_puesta_a_punto.md`](06_puesta_a_punto.md).

## Lo que ya sabíamos antes de conectar

- **Conector de la Jetson**: 2 flex MIPI CSI de **22 posiciones**, paso 0,5mm, **contacto abajo**
  (§3.4 de [`00_antes_de_empezar.md`](00_antes_de_empezar.md#34-los-conectores-de-cámara-son-de-22-pines-no-de-15)).
- **Cámara del laboratorio**: **ArduCam UC-517** — PTZ (pan 360° / tilt 120° / zoom óptico 3x) con
  sensor **IMX477** (el mismo de la Raspberry Pi HQ Camera). Al ser IMX219/IMX477, JetPack trae
  driver de fábrica: se configura con `jetson-io.py`, sin compilar kernel.
- **Conector de la ArduCam**: también es de **22 posiciones** (comprobado a mano: un flex de 15
  pines no entra). Como la Jetson también es de 22, no hizo falta ningún adaptador — alcanzó con
  un cable **derecho de 22 a 22 pines**.
- Fuente puntual usada para confirmar que este modelo anda con el driver de fábrica: hilo del
  foro de NVIDIA Developer sobre esta misma ArduCam UC-517 (IMX477) en un Jetson Orin —
  <https://forums.developer.nvidia.com/t/arducam-imx477-uc-517-rev-d3-b0274-4-lane-configuation-on-cam1-of-orin-nx-16gb-development-kit/362367>.

## 1. Conectar la cámara físicamente

Con la placa **apagada y desenchufada** (mismo criterio que con el SSD y J14 — nunca tocar un
flex con la placa alimentada, el conector CSI no es *hot-plug*):

1. Levantar la traba del conector **CAM1** (el que se usó acá — confirmado mirando el silkscreen
   de la placa, no solo "el que estaba enchufado").
2. Insertar el cable de 22 a 22 pines, derecho y hasta el fondo, en los dos extremos (Jetson y
   ArduCam).
3. Cerrar las dos trabas.

**Foto:** [`imagenes/07_conexion_csi.jpg`](imagenes/07_conexion_csi.jpg) — *(pendiente: agregar
foto del cable conectado entre la Jetson y la ArduCam, mostrando el conector CAM1 y la
orientación del flex)*.

## 2. Configurar el conector (`jetson-io.py`)

```bash
sudo find / -iname "jetson-io.py" 2>/dev/null   # /opt/nvidia/jetson-io/jetson-io.py
sudo python3 /opt/nvidia/jetson-io/jetson-io.py
```

Es un menú de texto. El camino real fue:

```
Configure Jetson 22pin CSI Connector
  → Configure for compatible hardware
    → Camera IMX477-C          (la "C" corresponde a CAM1; "A" sería CAM0)
```

Al confirmar, pregunta si guardar los cambios y reiniciar — hay que aceptar el reinicio para que
tome el *device tree overlay* nuevo. Quedó anotado en `/boot/extlinux/extlinux.conf`:

```
MENU LABEL Custom Header Config: <CSI Camera IMX477-C>
OVERLAYS /boot/tegra234-p3767-camera-p3768-imx477-C.dtbo
```

## 3. Verificar que el sensor aparece

```bash
sudo apt install -y v4l-utils   # ya venía instalado en nuestro caso
v4l2-ctl --list-devices
ls /dev/video* /dev/media*
```

### 3.1 Primer intento: no apareció nada — diagnóstico

La primera vez, `/dev/video*` no existía. El diagnóstico fue por partes:

```bash
sudo dmesg | grep -iE "imx477|vi-output|tegra-camera|csi|camera"
```

```
imx477 9-001a: tegracam sensor driver:imx477_v2.0.6
imx477 9-001a: imx477_board_setup: error during i2c read probe (-121)
imx477: probe of 9-001a failed with error -121
```

El overlay se había cargado bien (el driver intentó bindear en el bus i2c-9, dirección `0x1a`,
que es la dirección estándar del IMX477) — el error `-121` es **"Remote I/O error"**: nadie
contestó por I2C. Confirmado con:

```bash
sudo i2cdetect -y -r 9
```

Fila `10:` sin nada en la columna `a` (debería aparecer `1a`). El sensor no estaba respondiendo.

**Causa real:** uno de los dos extremos del flex de 22 pines había quedado **insertado al
revés** (orientación de contactos invertida) — entraba físicamente porque coincide en cantidad
de pines, pero no hacía contacto eléctrico correcto. No fue un problema de driver ni de overlay.

### 3.2 Solución: reasentar el cable

Con la placa apagada y desenchufada otra vez: se abrió la traba, se sacó el flex, y se volvió a
insertar respetando la orientación correcta de los contactos en las dos puntas.

Después del reinicio, quedó así:

```bash
sudo i2cdetect -y -r 9
```

```
10: -- -- -- -- -- -- -- -- -- -- UU -- -- -- -- --
```

`UU` en la dirección `1a` significa que el **driver del kernel ya está usando ese dispositivo**
(por eso no se puede sondear directo) — confirma que esta vez sí respondió. Y en `dmesg`:

```
imx477 9-001a: tegracam sensor driver:imx477_v2.0.6
tegra-camrtc-capture-vi tegra-capture-vi: subdev imx477 9-001a bound
```

```bash
ls /dev/video* /dev/media*
```

```
/dev/media0  /dev/video0
```

## 4. Primera captura

Con `nvarguscamerasrc` (el pipeline de GStreamer que usa el ISP de la Jetson vía *libargus* — no
necesita monitor conectado, corre bien por SSH):

```bash
gst-launch-1.0 nvarguscamerasrc num-buffers=1 sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=3840,height=2160' ! nvjpegenc ! \
  filesink location=~/primera_captura.jpg
```

Argus reportó los modos de sensor disponibles para este IMX477:

```
3840 x 2160  FR = 29.999999 fps
1920 x 1080  FR = 59.999999 fps
```

La captura terminó con `Done Success` en ambos lados (`CONSUMER` y `GST_ARGUS`). El archivo se
trajo a la PC para verlo, desde una terminal nueva **en la PC** (no dentro de la sesión SSH):

```bash
scp indea@<ip_de_la_jetson>:~/primera_captura.jpg .
```

Confirmado: la imagen se abre bien y muestra lo que ve la cámara.

## Qué queda pendiente

- **Primera vista en vivo** (streaming continuo, no solo una foto) — con `nvarguscamerasrc` sin
  `num-buffers=1`, hacia un `nveglglessink` (necesita monitor/X en la Jetson) o hacia la red para
  verla desde la PC.
- **Control PTZ** (motor de pan/tilt/zoom de la UC-517): es una capa aparte del driver de imagen
  estándar, probablemente necesite software propio de ArduCam. No investigado todavía.
- Reconectarse por SSH después de apagar y prender de nuevo puede requerir revisar la IP a mano
  otra vez — ver §0.1 de [`06_puesta_a_punto.md`](06_puesta_a_punto.md#01-reconectarse-sin-monitor-sin-buscar-la-ip-de-nuevo).

## Con qué seguir

[`08_primer_ejemplo_de_inferencia.md`](08_primer_ejemplo_de_inferencia.md): un primer ejemplo de
punta a punta, clasificando o detectando sobre el video de esta cámara — puede arrancar con
capturas fijas mientras la vista en vivo sigue pendiente.
