# 04 — Instalación en microSD

Dejar la placa arrancando desde microSD con JetPack 6.2.x. Al terminar, la placa arranca sola, tiene
CUDA y está lista para la puesta a punto.

> **Estado.** Procedimiento escrito a partir de la documentación oficial, **pendiente de ejecutar en
> la placa**. Cada bloque marcado *(completar)* se llena con la salida real al hacerlo.

**Antes hay que haber hecho [`03_firmware_y_version_de_jetpack.md`](03_firmware_y_version_de_jetpack.md)**,
porque la versión de firmware decide cuál de los dos caminos de acá abajo corresponde.

## Qué camino corresponde

| Firmware leído en UEFI | Camino |
|------------------------|--------|
| **36.x o superior** | **A — Balena Etcher.** Se graba la tarjeta y listo. |
| **Anterior a 36.0** | **B — SDK Manager**, con la placa en force recovery: escribe firmware y sistema juntos. |

**Nuestra placa: firmware `36.4.3` → camino A.** Todo el aparato del flasheo por USB existe para
resolver el firmware viejo; con firmware de generación 6 no aporta nada y solo agrega pasos donde
algo puede salir mal.

SDK Manager se va a usar igual más adelante, pero para el **SSD NVMe**
([`05_instalacion_en_ssd_nvme.md`](05_instalacion_en_ssd_nvme.md)), donde sí es obligatorio.

## Camino A — Balena Etcher (el nuestro)

### 1. Descargar la imagen

De la [página de JetPack 6.2.1](https://developer.nvidia.com/embedded/jetpack-sdk-621):
**`jp62-r1-orin-nano-sd-card-image.zip`**.

Tres cosas que confunden en esa página y conviene tener claras de antemano:

- **La 6.2.2 no tiene imagen de tarjeta propia.** Su página remite a la de 6.2.1 y dice textual:
  *"Use the SD Card image of JetPack 6.2.1 / Jetson Linux 36.4.4 and APT upgrade to JetPack 6.2.2 /
  Jetson Linux 36.5"*. Así que el camino es 6.2.1 por Etcher y 6.2.2 por `apt`.
- **El archivo se llama `jp62`, no `jp621`.** NVIDIA lo numera como "JetPack 6.2 revisión 1". Es el
  correcto: corresponde a L4T 36.4.4.
- La página avisa que las unidades con **firmware de fábrica** tienen que actualizarlo antes
  siguiendo la *Initial Setup Guide*. **A nosotros no nos aplica**: el firmware ya era 36.4.3.

Son varios GB. Verificar la descarga con el checksum que publica NVIDIA al lado del enlace:

```bash
sha256sum jp62-r1-orin-nano-sd-card-image.zip
```

*(completar: checksum verificado)*

### 2. Grabar la tarjeta

Con [Balena Etcher](https://etcher.balena.io/): seleccionar el `.zip` (no hace falta descomprimirlo),
seleccionar la microSD y grabar. Etcher verifica solo al terminar; dejarlo que verifique.

> Revisá dos veces qué unidad elegiste. Etcher no pregunta de nuevo, y una microSD y un pendrive de
> respaldo se parecen bastante en la lista.

*(completar: modelo de la microSD, duración del grabado)*

### 3. Primer arranque

1. La ranura de la microSD está **en el módulo**, no en la placa portadora: se accede por abajo.
   Insertar la tarjeta con la placa desenchufada.
2. Conectar monitor DisplayPort, teclado, mouse y **cable de red**.
3. Enchufar la fuente de 19 V. **La placa enciende sola: no hay botón.**
4. Completar la configuración de Ubuntu: usuario, contraseña, idioma, zona horaria, teclado, red.

Registrar el estado de partida con el script del repositorio, que junta todo de una sola vez:

```bash
bash ejemplos/verificar_entorno.sh | tee estado_$(date +%F)_recien_instalada.txt
```

*(completar: pegar la salida entera)*

Lo que hay que ver en esa salida:

- `/proc/device-tree/model` dice **NVIDIA Jetson Orin Nano**.
- `/etc/nv_tegra_release` dice **R36**.
- `uname -a` dice **aarch64** y kernel **5.15**.
- El medio de arranque es la microSD (`/dev/mmcblk*`).

### 4. Subir a JetPack 6.2.2

Dentro de la misma versión mayor, `apt` es la vía correcta:

```bash
sudo apt update
sudo apt full-upgrade
sudo reboot
```

Y volver a correr el script para comparar:

```bash
bash ejemplos/verificar_entorno.sh | tee estado_$(date +%F)_jetpack_622.txt
apt-cache policy nvidia-jetpack
```

*(completar: salida después de la actualización)*

El contraste entre las dos salidas —antes y después— es lo más útil del documento: muestra qué
cambió realmente y sirve de referencia cuando algo se rompa más adelante.

> **Recordatorio de §3.6 del documento 00.** Actualizar por `apt` dentro de 6.x está bien. Lo que no
> hay que hacer nunca es intentar saltar de 5.x a 6.x así, ni pisar paquetes `nvidia-l4t-*`, ni
> instalar drivers de NVIDIA de escritorio o CUDA "de PC". De eso solo se vuelve reflasheando.

## Camino B — SDK Manager (no lo usamos acá)

Queda documentado porque es lo que corresponde si el firmware es anterior a 36.0, y porque es el
mismo procedimiento que se usa para el SSD NVMe.

1. En la PC con Ubuntu x86_64 **nativo**, instalar SDK Manager desde
   [developer.nvidia.com/sdk-manager](https://developer.nvidia.com/sdk-manager) (cuenta de NVIDIA
   Developer, gratuita) y confirmar ~60 GB libres.
2. **Force recovery**, y el orden importa — el puente va **antes** de la alimentación:
   placa desenchufada → puentear los **pines 9 y 10 del header J14** → enchufar la fuente → quitar
   el puente → conectar el USB-C a la PC.
3. Verificar en la PC:

   ```bash
   lsusb | grep -i nvidia    # tiene que aparecer "NVIDIA Corp. APX"
   ```

   Si no aparece, es el **cable** (de solo carga) o el **modo recovery** (el puente no hizo contacto,
   o se puso después de alimentar). No es el software.
4. En SDK Manager: target *Jetson Orin Nano Developer Kit* módulo **8GB**, JetPack **6.2.1**,
   storage device **microSD** (o **NVMe** para el SSD). Aceptar la actualización de firmware/QSPI
   cuando la pida.

## Problemas conocidos

| Síntoma | Causa probable |
|---------|----------------|
| Pantalla negra al arrancar, sin mensajes | Firmware más viejo que la imagen, o adaptador DisplayPort → HDMI pasivo. |
| Arranca lentísimo, se cuelga o corrompe archivos | La microSD: lenta, falsa o de mala calidad (§3.9). |
| Reinicios espontáneos sin patrón | Alimentación insuficiente. Tiene que ser la fuente de 19 V por el jack DC (§3.2). |
| La placa no aparece como APX en `lsusb` (camino B) | Cable USB-C de solo carga, o el puente J14 se puso después de alimentar. |

## Con qué seguir

[`06_puesta_a_punto.md`](06_puesta_a_punto.md): `jtop`, modo de energía MAXN SUPER, Docker y
verificación de CUDA.
