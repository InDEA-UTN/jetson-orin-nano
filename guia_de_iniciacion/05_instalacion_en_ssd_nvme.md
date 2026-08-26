# 05 — Instalación en SSD NVMe

Dejar el sistema también instalado y arrancando desde el SSD NVMe, en paralelo a la microSD (dual
boot elegible en cada arranque). Es el medio de trabajo definitivo: más rápido, más espacio, y el
único lugar donde va swap (§3.7 de [`00_antes_de_empezar.md`](00_antes_de_empezar.md)).

> **Estado.** Verificado en la placa el **2026-08-06**. La placa arranca por defecto desde el
> SSD; la microSD sigue intacta y se elige a mano cuando hace falta (§9).

**Antes hay que haber hecho** [`02_que_hace_falta.md`](02_que_hace_falta.md) (el SSD tiene que
estar comprado y a mano) y [`04_instalacion_en_microsd.md`](04_instalacion_en_microsd.md) (la
placa ya tiene que estar andando desde la microSD — sirve como respaldo si algo sale mal acá).

## Por qué no sirve Balena Etcher acá

El SSD NVMe queda **dentro** de la Jetson, atornillado al slot M.2 — no hay forma de sacarlo y
ponerlo en el lector de la PC como se hace con la microSD. La única forma de escribirle el sistema
es que la propia Jetson, conectada por USB en modo *force recovery*, lo reciba de una herramienta
que la programa activamente: **SDK Manager**, de NVIDIA.

## 1. Instalar el SSD físico

1. Apagar y **desenchufar** la fuente de la Jetson.
2. Ubicar el slot M.2 Key M **2280** (el bueno; el otro slot, 2230, es para el módulo WiFi).
3. Insertar el SSD en ángulo (~30°), presionarlo hacia el conector y atornillarlo.

**Nuestro disco:** M.2 2280 NVMe Gen4x4 de 250 GB, modelo **MG43** (detalle y aclaración de que
corre a Gen3 por el slot en [`02_que_hace_falta.md`](02_que_hace_falta.md)).

## 2. Instalar SDK Manager en la PC anfitriona

Descargar desde <https://developer.nvidia.com/sdk-manager> (requiere cuenta NVIDIA Developer
gratuita) e instalar:

```bash
cd ~/Downloads
sudo apt install ./sdkmanager_*.deb
```

*(usada la versión 2.4.1-13536)*. El aviso final de `apt` sobre "Download is performed
unsandboxed..." es un mensaje menor, no un error — la instalación queda completa igual.

## 3. Identificar el módulo exacto

Con la placa ya arrancada (desde la microSD), correr:

```bash
cat /proc/device-tree/nvidia,dtsfilename
```

Nuestro resultado confirma el módulo **P3767-0005** — la variante de **Developer Kit** del Orin
Nano 8GB (P3767-0003 es la versión standalone, para quien diseña su propia carrier board).

## 4. Poner la Jetson en *force recovery*

1. Apagar y desenchufar la fuente.
2. Puentear los **pines 9-10 del header J14** (debajo del módulo) con un jumper o un clip.
3. Enchufar la fuente con el puente puesto.
4. Esperar 2-3 segundos y sacar el jumper.
5. Conectar el **cable USB-C de datos** entre la Jetson y la PC.
6. Confirmar detección:
   ```bash
   lsusb | grep -i nvidia
   ```
   Tiene que aparecer `NVIDIA Corp. APX`.

## 5. Configurar y correr el flasheo en SDK Manager

```bash
sdkmanager
```

- **Step 01 — target**: la placa se detecta sola por USB. Versión elegida: **JetPack 6.2.3**
  (aparece 7.2 seleccionada por defecto; hay que cambiarla). Con Ubuntu 24.04 en la PC, la
  instalación de *host* no está soportada para JetPack 6.2.x — usar el link **"Deselect Host"**
  que ofrece la propia pantalla y dejar solo el **Target install**, que es lo único que hace
  falta para flashear la Jetson.
- **Step 02 — componentes**: quedaron marcados los *Jetson Runtime Components* (CUDA Runtime,
  CUDA-X AI Runtime, Computer Vision, **NVIDIA Container Runtime** — necesario para Docker con
  GPU, el camino de `jetson-containers`) y también los ***Jetson SDK Components*** completos
  (CUDA, CUDA-X AI, Computer Vision y Developer Tools): quedaron **instalados** nativos en el
  SSD, no solo el runtime. Se dejaron sin marcar los SDKs adicionales (**DeepStream**, **GXF
  Runtime**, **Holoscan**), que no hacen falta para el uso previsto de la placa.
- Se usó primero la opción **"Download now. Install later"** para bajar los paquetes (~6-10 GB)
  sin tener la Jetson conectada todavía.
- **Pantalla de flasheo**:
  - **Selected device**: confirmar que dice *"Jetson Orin Nano [8GB developer kit version]"*.
  - **OEM Configuration → Pre-Config**: se cargó usuario y contraseña de antemano, para que el
    SSD arranque directo al login sin pedir completar el asistente de Ubuntu — no hace falta
    monitor conectado en el primer arranque del SSD.
  - **Storage Device → NVMe**. El aviso de "mínimo 256GB recomendado" no es bloqueante: con
    250GB anduvo sin problema.
- Dar **Flash**.

## 6. Problemas reales y cómo se resolvieron

Documentados porque son justo el tipo de trampa que esta guía existe para dejar anotada.

### 6.1 Espacio en disco de la PC anfitriona

```
There is not enough space on required partitions (1GB disk usage threshold on is needed).
Need additional ~21 GB on /dev/nvme0n1p4.
```

La partición raíz de la PC (Linux, no la de la Jetson) estaba al 99%. La imagen de la microSD
(`jetson-orin-nano-devkit-super-SD-image_JP6.2.1`, carpeta + `.zip`, **34 GB** en total) seguía en
`~/Downloads` sin hacer falta — ya estaba grabada y la microSD andando. Borrarla liberó espacio de
sobra:

```bash
rm -rf ~/Downloads/jetson-orin-nano-devkit-super-SD-image_JP6.2.1
rm -f ~/Downloads/jetson-orin-nano-devkit-super-SD-image_JP6.2.1.zip
```

### 6.2 "Jetson device is not ready for flash" (USB)

Error de detección USB al arrancar el flasheo. Se resolvió reconectando en el orden correcto:

1. Desconectar el USB-C de la PC.
2. Desenchufar la fuente de la Jetson.
3. Volver a puentear J14, enchufar la fuente, sacar el jumper.
4. Recién ahí reconectar el USB-C — **directo a un puerto de la PC, sin hub**.
5. Confirmar con `lsusb` antes de reintentar el flasheo.

### 6.3 UFW bloqueando NFS

Flashear a un disco externo (el SSD, vía NVMe) usa NFS entre la PC y la Jetson. El firewall de la
PC lo estaba bloqueando:

```bash
sudo ufw disable   # antes de reintentar el flash
# ... flashear ...
sudo ufw enable    # apenas termina — no dejarlo desactivado
```

### 6.4 Falla de DNS al verificar conectividad (paso "Install SDK components")

Después de flashear el sistema base, SDK Manager se conecta a la Jetson por una red virtual USB
(`192.168.55.1`) para instalar el resto de los componentes, y ahí verifica que la Jetson tenga
internet real. Con solo el USB conectado no lo tiene — hace falta además un **cable de red
Ethernet**, en paralelo al USB (son dos conexiones independientes, no se pisan).

Con el cable puesto, seguía fallando con:

```
Resolving www.nvidia.com... failed: Connection timed out.
wget: unable to resolve host address 'www.nvidia.com'
```

Diagnóstico por SSH a la Jetson (`ssh <usuario>@192.168.55.1`, con el usuario/contraseña del
Pre-Config):

```bash
ip a                   # la interfaz Ethernet (enP8p1s0) sí tenía IP por DHCP
ip route                # sí había ruta por defecto
ping -c 3 8.8.8.8       # respondía bien — hay internet real por IP
cat /etc/resolv.conf    # nameserver 127.0.0.53, search frm-intranet23
```

La conectividad por IP andaba perfecto; el problema era puntualmente **DNS**: la red de la
facultad (`frm-intranet23`) da internet real pero su DNS no resuelve dominios públicos. Se
resolvió fijando un DNS público a mano en esa interfaz:

```bash
nmcli connection show
sudo nmcli connection modify "Wired connection 1" ipv4.dns "8.8.8.8 1.1.1.1"
sudo nmcli connection modify "Wired connection 1" ipv4.ignore-auto-dns yes
sudo nmcli connection up "Wired connection 1"
```

Con eso, `wget` a `www.nvidia.com` y la verificación de repositorios `apt` en SDK Manager pasaron
sin problema, y se pudo reintentar la instalación de los componentes.

## 7. Cierre

- **Finish and Exit** en SDK Manager.
- Reactivar el firewall si quedó desactivado (`sudo ufw enable`).
- Desconectar el cable USB-C (ya no hace falta).
- Reiniciar la Jetson.

## 8. Primer arranque desde el SSD

Al reiniciar, el firmware quedó en **`36.5.2`** (subió solo desde `36.4.3`, como parte del mismo
flasheo — es esperable, SDK Manager actualiza QSPI y sistema en la misma operación).

Por defecto, ahora la placa **arranca sola desde el SSD**, sin pedir nada.

Verificar desde qué disco arrancó:

```bash
df -h /
lsblk
```

- `/dev/nvme0n1p...` montado en `/` → arrancó del **SSD**.
- `/dev/mmcblk0p...` montado en `/` → arrancó de la **microSD**.

*(completar: salida de `verificar_entorno.sh` corrida desde el SSD)*

## 9. Elegir entre SSD y microSD en cada arranque

En la pantalla del logo de NVIDIA aparece el menú de teclas disponibles:

```
ESC   to enter Setup.
F11   to enter Boot Manager Menu.
s     to enter Shell.
Enter to continue boot.
```

- **No tocar nada** → arranca del dispositivo por defecto (el SSD).
- **Apretar F11** en esa pantalla → abre el **Boot Manager Menu**, con la lista de dispositivos
  booteables (SSD / microSD) para elegir **para ese arranque puntual**. Es más simple que entrar
  al Setup completo (`ESC`) a buscar un timeout de arranque automático: no hace falta configurar
  nada de antemano, solo apretar F11 cuando se lo necesite.

## Con qué seguir

[`06_puesta_a_punto.md`](06_puesta_a_punto.md): `jtop`, modo de energía, swap (ahora sí, en el
SSD), Docker y verificación de CUDA — corriendo ya desde el SSD.
