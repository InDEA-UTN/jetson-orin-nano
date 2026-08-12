# 06 — Puesta a punto

Lo que conviene dejar hecho **una sola vez**, corriendo ya desde el SSD: un panel de estado
(`jtop`), el modo de energía a fondo, el swap donde corresponde, Docker con acceso a la GPU y el
compilador de CUDA.

> **Estado.** Verificado en la placa el **2026-08-11**, por SSH, con la placa ya arrancando desde
> el SSD.

**Antes hay que haber hecho** [`05_instalacion_en_ssd_nvme.md`](05_instalacion_en_ssd_nvme.md) —
todo esto se hace con la placa corriendo desde el SSD, no desde la microSD.

## 0. Conectarse por SSH

Para no depender de teclado y monitor conectados a la Jetson, conviene trabajar por SSH desde la
PC anfitriona. En la Jetson (por última vez con teclado propio):

```bash
hostname -I
```

Y desde la PC:

```bash
ssh <usuario>@<esa_ip>
```

Ojo: la IP `192.168.55.1` que aparece en el §6.4 de
[`05_instalacion_en_ssd_nvme.md`](05_instalacion_en_ssd_nvme.md#64-falla-de-dns-al-verificar-conectividad-paso-install-sdk-components)
era la red virtual **temporal** que usa SDK Manager por USB durante el flasheo — no sirve para
esto. Acá hace falta la IP real de la Jetson en la red de la facultad (Ethernet).

### 0.1 Reconectarse sin monitor, sin buscar la IP de nuevo

El router puede darle una IP distinta a la Jetson en cada reinicio, así que conviene no depender
de `hostname -I` cada vez. Ubuntu trae activado de fábrica `avahi-daemon`, la implementación en
Linux de **mDNS** (a veces llamado Zeroconf; en productos Apple es lo mismo pero le dicen
*Bonjour*): un protocolo por el cual los equipos de una misma red local se anuncian por nombre
sin depender de ningún servidor DNS central. Gracias a eso, la Jetson ya se anuncia sola como
`<hostname>.local` (acá, `ubuntu.local`) y se puede entrar directo por ese nombre, sin usar la IP:

```bash
ssh indea@ubuntu.local
```

Confirmar que el servicio está activo (viene de fábrica, no hace falta instalar nada):

```bash
systemctl status avahi-daemon
```

> **Probado y no anduvo en esta red** (2026-08-11): con la Jetson por **Ethernet** y la PC
> anfitriona por **WiFi**, `ssh <usuario>@ubuntu.local` dio `Could not resolve hostname`, aunque
> `avahi-daemon` estaba corriendo bien de los dos lados (`libnss-mdns` y `nsswitch.conf`
> correctos en la PC). La causa no es de configuración: en la red de la facultad, WiFi y
> Ethernet parecen estar en **subredes/VLANs separadas**, y el multicast que usa mDNS no cruza
> entre subredes salvo que haya un "reflector" configurado a propósito — algo que no depende de
> nosotros. El SSH por **IP directa sí funciona** entre las dos (el router rutea tráfico normal
> sin problema, solo el multicast queda atado a cada segmento).
>
> **Plan real, mientras la PC anfitriona no tenga puerto Ethernet:** anotar la IP con
> `hostname -I` antes de apagar la placa. La mayoría de los DHCP le devuelven la **misma IP** al
> mismo equipo (mismo MAC) si no pasa mucho tiempo desconectado, así que conviene probar primero
> con esa. Si cambió, hace falta el monitor una vez más para volver a correr `hostname -I`. Un
> adaptador USB → Ethernet en la PC anfitriona resolvería esto de raíz (misma subred que la
> Jetson), pero no es imprescindible.

## 1. jtop

`jtop` es un panel de estado en vivo para Jetson — el equivalente a `htop`, pero mostrando además
uso de GPU, temperatura y el modo de energía actual. Es una herramienta de la comunidad
([`rbonghi/jetson_stats`](https://github.com/rbonghi/jetson_stats)), no de NVIDIA, pero es el
estándar de facto para mirar el estado de la placa de un vistazo.

Se instala con `pip`, el gestor de paquetes de **Python** (el lenguaje en el que está escrito
`jtop`, y en el que están escritas la mayoría de las herramientas de IA que se van a usar más
adelante): del mismo modo que `apt` instala paquetes de Ubuntu, `pip` instala paquetes de Python
publicados en PyPI. Esta imagen de JetPack no traía `pip` instalado de fábrica, así que hubo que
agregarlo primero:

```bash
sudo apt update
sudo apt install -y python3-pip
sudo pip3 install -U jetson-stats
sudo reboot
```

Después del reinicio (hace falta para que arranque el servicio `jtop.service`):

```
$ jtop --version
jtop 7.2.1
```

## 2. Modo de energía: MAXN SUPER

Por defecto la placa arranca en un modo de energía con techo de consumo fijo (acá, `25W`), que
limita a propósito el reloj de CPU y GPU. El modo **MAXN SUPER** saca ese techo y es el que
corresponde para un proyecto de visión + IA — ya estaba anotado como pendiente en el §3.8 de
[`00_antes_de_empezar.md`](00_antes_de_empezar.md#38-el-modo-super-hay-que-habilitarlo).

No es una decisión definitiva: el modo de energía se puede cambiar en cualquier momento con el
mismo comando (`-m 0` = 15W, `-m 1` = 25W, `-m 2` = MAXN SUPER), sin reinstalar nada. Queda
guardado entre reinicios hasta que se lo vuelva a cambiar.

```bash
sudo nvpmodel -m 2
sudo nvpmodel -q
```

```
NV Power Mode: MAXN_SUPER
2
```

Advertencia real (ya estaba en 00): es un modo **sin techo de consumo**, así que exige que la
fuente y el ventilador estén a la altura. Si se pasa del presupuesto térmico, la placa baja la
frecuencia sola — no se rompe, pero conviene mirar la temperatura en `jtop` de vez en cuando,
sobre todo la primera vez que se corre algo pesado.

## 3. Swap en el SSD

El swap es espacio de disco que el sistema usa como memoria extra cuando la RAM se llena — más
lento que la RAM, pero evita que un proceso se mate por falta de memoria. En una placa con 8GB de
RAM compartidos entre CPU y GPU (§3.7 de [`00_antes_de_empezar.md`](00_antes_de_empezar.md#37-8-gb-de-ram-son-compartidos-entre-cpu-y-gpu)),
importa tenerlo bien configurado, y **solo en el SSD** — en la microSD el swap la destruye
escribiendo sin parar.

Antes de este paso ya había swap, pero en **zram** (RAM comprimida, ~3.7GB): compite por la misma
RAM que se supone que libera. Se lo reemplazó por un swapfile real de 8GB en el SSD, que no
compite por RAM y es rápido por estar en NVMe:

```bash
sudo swapoff /dev/zram0 /dev/zram1 /dev/zram2 /dev/zram3 /dev/zram4 /dev/zram5
sudo systemctl disable --now nvzramconfig

sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verificado después del reinicio:

```
$ free -h; swapon --show
               total        used        free      shared  buff/cache   available
Mem:           7.4Gi       1.4Gi       4.7Gi        22Mi       1.4Gi       5.8Gi
Swap:          8.0Gi          0B       8.0Gi
NAME      TYPE SIZE USED PRIO
/swapfile file   8G   0B   -2
```

*(8GB = el tamaño de la RAM; ajustar más adelante si al cargar modelos grandes no alcanza.)*

## 4. Docker con GPU

Docker empaqueta software con sus dependencias en contenedores aislados, que corren igual en
cualquier máquina — en Jetson se usa mucho para bajar modelos de IA ya armados (ver
[`dusty-nv/jetson-containers`](https://github.com/dusty-nv/jetson-containers), ya citado en 00) sin
instalar a mano decenas de librerías. JetPack lo instala junto con el *runtime* `nvidia` (necesario
para que un contenedor vea la GPU), pero no lo deja activado por defecto ni habilita al usuario
para correrlo sin `sudo`.

```bash
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
sudo python3 -c "
import json
with open('/etc/docker/daemon.json') as f:
    d = json.load(f)
d['default-runtime'] = 'nvidia'
with open('/etc/docker/daemon.json', 'w') as f:
    json.dump(d, f, indent=4)
"
sudo usermod -aG docker $USER
sudo systemctl restart docker
sudo reboot
```

*(el `reboot` hace falta para que el usuario quede efectivamente en el grupo `docker`; un
`newgrp docker` o cerrar sesión y volver a entrar por SSH también alcanza.)*

Verificado después del reinicio, sin `sudo`:

```
$ docker info 2>/dev/null | grep -i "runtime\|Default"
 Runtimes: runc io.containerd.runc.v2 nvidia
 Default Runtime: nvidia
$ docker run --rm hello-world
Hello from Docker!
```

## 5. CUDA: falta el compilador (`nvcc`)

CUDA es la plataforma de NVIDIA para programar la GPU. Lo que la instalación en el SSD ya trae
(componentes *Runtime*, ver §5 de
[`05_instalacion_en_ssd_nvme.md`](05_instalacion_en_ssd_nvme.md)) alcanza para **correr** modelos
ya compilados (PyTorch, TensorRT) — que es lo que hace falta para
[`08_primer_ejemplo_de_inferencia.md`](08_primer_ejemplo_de_inferencia.md). Lo que faltaba es
`nvcc`, el **compilador**: hace falta recién si en algún momento se necesita compilar código CUDA
propio o una librería que lo pida en su instalación (por ejemplo, OpenCV con soporte CUDA).

Se instaló igual, para no toparse con esto a mitad de otra tarea más adelante:

```bash
sudo apt install -y cuda-nvcc-12-6
```

```
$ /usr/local/cuda/bin/nvcc --version
nvcc: NVIDIA (R) Cuda compiler driver
Cuda compilation tools, release 12.6, V12.6.68
```

## Con qué seguir

[`07_camara_csi.md`](07_camara_csi.md): conectar la cámara al conector CSI y verificar que el
sensor aparece — pendiente de resolver primero qué sensor exacto compró el laboratorio (§3.4 de
[`00_antes_de_empezar.md`](00_antes_de_empezar.md), §3 de
[`02_que_hace_falta.md`](02_que_hace_falta.md)).
