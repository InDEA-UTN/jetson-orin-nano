# Comandos útiles

Los comandos que se usan todo el tiempo con esta Jetson Orin Nano, agrupados por tarea, para
copiar y pegar sin tener que releer la guía narrativa. No explican teoría — para eso está
[`../guia_de_iniciacion/`](../guia_de_iniciacion/), enlazada donde hace falta más contexto.

Escrito el **2026-08-13**, contra el estado real de la placa: módulo **P3767-0005 Developer Kit**,
**JetPack 6.2.3 / L4T 36.5**, arrancando desde **SSD M.2 NVMe 250GB**, usuario del sistema
**`indea`**, cámara **ArduCam UC-517 (sensor IMX477)** en el conector **CAM1**.

## Monitoreo

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `jtop` | Panel en vivo tipo `htop`: CPU, GPU, RAM, temperatura y modo de energía en una sola pantalla. | Para mirar el estado general de un vistazo. Es la herramienta de referencia en esta placa. |
| `jtop --version` | Confirma que `jtop` quedó instalado y qué versión corre. | Después de instalarlo o para verificar tras un reinicio. |
| `sudo apt install -y python3-pip && sudo pip3 install -U jetson-stats && sudo reboot` | Instala `jtop` (no viene de fábrica en esta imagen; tampoco `pip3`). | Una sola vez, apenas se tiene el sistema andando. Ver [`06_puesta_a_punto.md`](../guia_de_iniciacion/06_puesta_a_punto.md#1-jtop). |
| `tegrastats` | Utilitario de NVIDIA (viene de fábrica, sin instalar nada) que imprime por consola una línea por segundo con uso de CPU/GPU/RAM y temperatura. | Alternativa liviana a `jtop` cuando solo hace falta loguear números (por ejemplo redirigiendo la salida a un archivo), sin la interfaz interactiva. |
| `free -h` | RAM y swap usados/libres, en formato legible. | Chequeo rápido de memoria, sobre todo con modelos grandes cargados. |
| `swapon --show` | Qué swap está activo y dónde vive (archivo, partición, zram). | Confirmar que el swap es el swapfile del SSD y no zram. |
| `df -h` | Espacio en disco por partición. | Confirmar desde qué disco arrancó la placa (`/dev/nvme0n1...` = SSD, `/dev/mmcblk0...` = microSD) y cuánto espacio queda. |
| `dpkg -l \| grep cuda` | Lista los paquetes CUDA instalados y su versión. | Verificar qué trae el sistema antes de instalar algo que dependa de CUDA. |
| `nvidia-smi` | **No sirve en Jetson** — la GPU es integrada, no hay tarjeta discreta que liste. | Usar `jtop` o `tegrastats` en su lugar. |

## Energía

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `sudo nvpmodel -q` | Muestra el modo de energía actual y la lista de modos disponibles. | Antes de cambiar de modo, y para anotar en qué modo se corrió cualquier benchmark. |
| `sudo nvpmodel -m 2` | Activa **MAXN SUPER** (sin techo de consumo, hasta 67 TOPS) — confirmar que el número `2` sigue correspondiendo a SUPER con `-q` antes de correrlo. | Para cualquier trabajo real de visión/IA. No viene activo por defecto (arranca en un modo con techo fijo, ej. 25W). Ver [`06_puesta_a_punto.md`](../guia_de_iniciacion/06_puesta_a_punto.md#2-modo-de-energía-maxn-super). |
| `sudo nvpmodel -m 1` / `-m 0` | Vuelve a un modo con techo de consumo (25W / 15W). | Si la placa se recalienta o hace falta consumo predecible. |
| `sudo systemctl set-default multi-user.target` | La placa arranca sin escritorio gráfico (libera RAM). | Antes de correr algo pesado (inferencia, compilar), en una placa con 8GB compartidos entre CPU y GPU. |
| `sudo systemctl set-default graphical.target` | Vuelve a arrancar con escritorio. | Para volver atrás. |

## Cámara

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `sudo python3 /opt/nvidia/jetson-io/jetson-io.py` | Menú de texto para elegir qué sensor está conectado en cada conector CSI (genera el *device tree overlay*). | Una vez por sensor/conector. En esta placa: *Configure for compatible hardware → Camera IMX477-C* (la "C" es CAM1). Pide reiniciar para tomar el overlay. Ver [`07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md#2-configurar-el-conector-jetson-iopy). |
| `sudo apt install -y v4l-utils` | Instala `v4l2-ctl` (no viene instalado de fábrica en esta imagen). | Antes del primer `v4l2-ctl`, si tira `command not found`. |
| `v4l2-ctl --list-devices` | Lista los dispositivos de video que el kernel reconoce. | Para confirmar que la cámara quedó detectada. |
| `ls /dev/video* /dev/media*` | Confirma si existen los nodos de dispositivo de la cámara. | Mismo chequeo, más directo. Si no aparece nada, el sensor no se detectó. |
| `sudo dmesg \| grep -iE "imx477\|vi-output\|tegra-camera\|csi\|camera"` | Filtra el log del kernel por mensajes de cámara. | Primer paso de diagnóstico cuando `/dev/video*` no aparece. |
| `sudo i2cdetect -y -r 9` | Sondea el bus I2C 9 (el que usa el sensor CSI en esta placa) buscando la dirección `0x1a` del IMX477. | Para saber si el sensor responde eléctricamente. `UU` en `1a` = el driver ya lo tiene tomado (bien); nada en `1a` = no hay contacto físico. |
| `gst-launch-1.0 nvarguscamerasrc num-buffers=1 sensor-id=0 ! 'video/x-raw(memory:NVMM),width=3840,height=2160' ! nvjpegenc ! filesink location=~/captura.jpg` | Saca una foto fija usando el ISP de la Jetson. | Primera prueba de que la cámara captura bien. Detalle en [`07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md#4-primera-captura). |
| `gst-inspect-1.0 \| grep -iE "264\|265\|nvv4l2\|nvenc\|nvvidconv"` | Lista los elementos de GStreamer relacionados con codificación de video disponibles. | Para confirmar qué hay instalado — en esta placa **no** aparece `nvv4l2h264enc`: la Orin Nano no tiene NVENC (encoder por hardware), solo decoder. |
| Pipelines de vista en vivo por red (emisor en la Jetson + receptor en la PC, codificando por software con `x264enc`) | Transmite el video de la cámara a otra máquina para verlo sin monitor en la Jetson. | Ver el pipeline completo en [`07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md#53-pipelines-finales-que-funcionaron) — es largo para repetir acá. |

## Red

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `hostname -I` | Muestra la IP actual de la Jetson. | Antes de apagarla, para tenerla anotada — el router suele repetir la misma IP al mismo equipo. |
| `ssh indea@<ip>` | Conecta por SSH usando la IP directa. | El camino que siempre funciona en esta red, cruce o no de subredes/WiFi-Ethernet. |
| `ssh indea@ubuntu.local` | Conecta por el nombre mDNS (`avahi`), sin necesidad de conocer la IP. | Solo funciona si la PC y la Jetson están en el **mismo segmento** de red. En la red de la facultad, WiFi y Ethernet están en subredes separadas y esto **no anduvo** — ver `problemas_frecuentes.md`. |
| `systemctl status avahi-daemon` | Confirma que el servicio de mDNS está activo (viene de fábrica). | Para descartar que el problema sea el servicio y no la red. |
| `nc -u -l 5000` (en el receptor) / `echo "hola" \| nc -u -w1 <ip> 5000` (en el emisor) | Manda/escucha datos crudos por UDP, sin protocolo de aplicación. | Probar que dos máquinas se hablan en un puerto/protocolo antes de armar un pipeline de GStreamer más complejo. |
| `sudo ufw status verbose` | Muestra el estado del firewall y las reglas activas. | Diagnóstico cuando algo no llega por red y ya se descartó routing/DNS. |
| `sudo ufw allow 5000/udp` | Abre un puerto UDP puntual. | Cuando `ufw` (política *deny incoming* por defecto) bloquea el puerto que se necesita usar (streaming, netcat). |
| `sudo ufw disable` / `sudo ufw enable` | Apaga/prende el firewall entero. | Solo temporalmente para procedimientos que lo requieren (por ejemplo NFS durante un flasheo a SSD) — **reactivar apenas termina**. |
| `nmcli connection show` | Lista las conexiones de red configuradas. | Para saber el nombre exacto de la conexión antes de tocarla (ej. `"Wired connection 1"`). |
| `sudo nmcli connection modify "Wired connection 1" ipv4.dns "8.8.8.8 1.1.1.1"` seguido de `ipv4.ignore-auto-dns yes` y `connection up` | Fija DNS público a mano en una interfaz. | Cuando el DNS que da la red (por DHCP) resuelve solo dominios internos y no internet público — pasó con la red de la facultad. |
| `scp indea@<ip>:~/archivo.jpg .` | Copia un archivo desde la Jetson a la PC (correrlo **en la PC**, no por SSH adentro de la Jetson). | Traer capturas o logs para revisar fuera de la placa. |

## Contenedores (Docker)

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `docker info 2>/dev/null \| grep -i "runtime\|Default"` | Muestra los runtimes disponibles y cuál es el default. | Confirmar que `nvidia` quedó como runtime por defecto (necesario para que los contenedores vean la GPU). |
| `docker run --rm hello-world` | Contenedor mínimo de prueba. | Verificar que Docker corre bien después de la instalación/configuración. |
| `sudo usermod -aG docker $USER` | Agrega el usuario actual al grupo `docker` (correr sin `sudo`). | Una vez, en la puesta a punto. Hace falta reiniciar sesión (o `sudo reboot`) para que tome efecto. |
| `git clone --recursive --depth=1 https://github.com/dusty-nv/jetson-inference` | Trae el repo de *Hello AI World* (clasificación/detección con modelos pre-entrenados). | Primer ejemplo de inferencia. |
| `docker/run.sh` (parado dentro de `jetson-inference/`) | Detecta la versión de JetPack/L4T, baja el contenedor `dustynv/jetson-inference:<tag>` correspondiente y lo arranca con la GPU y `/dev/video0` montados. | Para entrar a un entorno con CUDA/TensorRT/PyTorch/OpenCV ya compilados, sin instalar nada a mano. Si el tag automático no existe, ver `problemas_frecuentes.md`. |
| `docker/run.sh --container dustynv/jetson-inference:r36.3.0` | Misma idea, forzando un tag concreto. | Cuando el tag que detecta solo (ej. `r36.5.2`) no está publicado — un tag menor dentro de la misma rama `r36.x` sirve igual. |

## Disco y swap

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `lsblk` | Lista los discos y particiones del sistema. | Ver si el SSD (`nvme0n1`) y la microSD (`mmcblk0`) están presentes y cómo están particionados. |
| `df -h /` | De qué disco está montada la raíz. | Confirmar desde qué medio arrancó (ver tabla de Monitoreo). |
| `sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' \| sudo tee -a /etc/fstab` | Crea un swapfile de 8GB en el disco actual y lo deja activo entre reinicios. | Una vez, **solo en el SSD** — en microSD el swap la destruye escribiendo sin parar. Detalle en [`06_puesta_a_punto.md`](../guia_de_iniciacion/06_puesta_a_punto.md#3-swap-en-el-ssd). |
| `sudo swapoff /dev/zram0 /dev/zram1 /dev/zram2 /dev/zram3 /dev/zram4 /dev/zram5 && sudo systemctl disable --now nvzramconfig` | Apaga el swap en zram (RAM comprimida) que trae la imagen por defecto. | Antes de crear el swapfile en SSD — zram compite por la misma RAM que se quiere liberar. |

## Firmware e identificación de la placa

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `cat /etc/nv_tegra_release` | Versión de Jetson Linux (L4T) instalada. | Chequeo de versión al empezar cualquier documento o al reportar un problema. |
| `apt-cache show nvidia-jetpack \| head` | Versión de JetPack instalada. | Idem. |
| `uname -a` | Kernel y arquitectura. | Idem — confirma `aarch64`. |
| `cat /proc/device-tree/nvidia,dtsfilename` | Identifica el módulo exacto (en esta placa: `P3767-0005`, variante Developer Kit). | Para saber con certeza qué hardware es, útil antes de pedir ayuda en foros. |
| `lsusb \| grep -i nvidia` | Confirma que la Jetson está en modo *force recovery* y la PC la detecta. | Antes de correr `sdkmanager` — tiene que aparecer `NVIDIA Corp. APX`. Si no aparece, es el cable/puente J14, no el software. |

## Compilador CUDA (`nvcc`)

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `sudo apt install -y cuda-nvcc-12-6` | Instala el compilador de CUDA (no viene con los componentes *Runtime* del flasheo). | Solo si hace falta compilar código CUDA propio o una librería que lo pida (ej. OpenCV con soporte CUDA) — para *correr* modelos ya compilados no hace falta. |
| `/usr/local/cuda/bin/nvcc --version` | Confirma la instalación y versión. | Después de instalarlo. |
