# 02 — Qué hace falta

Lista de lo que tiene que estar sobre la mesa antes de conectar la placa, con la justificación de
cada cosa. Casi todo sale de las trampas del documento
[`00_antes_de_empezar.md`](00_antes_de_empezar.md); acá se concreta en objetos.

> **Estado.** Escrito antes del primer arranque, a partir de la documentación oficial y del
> inventario del laboratorio. Las columnas de modelo concreto se completan con lo que se usó de
> verdad, a medida que se usa.

## 1. Lo imprescindible para el primer arranque

| Qué | Por qué | Estado |
|-----|---------|--------|
| Jetson Orin Nano Developer Kit 8GB | La placa. | Disponible |
| Fuente del kit, **19 V**, jack DC **5,5 × 2,5 mm** | El USB-C **no alimenta** la placa (§3.2). Alimentar de menos causa reinicios que parecen fallas de software. | Disponible — *anotar los watts de la etiqueta: (completar)* |
| **microSD A2, 64 GB o más**, de marca conocida | Es el medio de arranque inicial. Una tarjeta lenta o falsa se manifiesta como "la placa no anda" (§3.9). | Disponible — **128 GB**, marca/clase A2: *(completar)* |
| **Monitor con DisplayPort**, o adaptador **DisplayPort → HDMI activo** | La placa **no tiene HDMI** (§3.3). El adaptador conviene que sea activo. | Disponible — *modelo del adaptador: (completar)* |
| Teclado y mouse USB | Configuración inicial de Ubuntu y, sobre todo, entrar al menú UEFI con **Esc**. | Disponible |
| Cable de red Ethernet | La actualización de firmware y la de JetPack necesitan Internet. Más confiable que el WiFi para el primer arranque. | *(completar)* |

## 2. Lo que hace falta para flashear

| Qué | Por qué | Estado |
|-----|---------|--------|
| **PC con Ubuntu x86_64 nativo** | SDK Manager solo corre ahí. En máquina virtual el *passthrough* del USB falla durante el reinicio de la placa (§3.10). | Disponible |
| ~60 GB libres en esa PC | SDK Manager descarga y descomprime la imagen completa. | *(verificar)* |
| **Cable USB-C que transporte datos** | Sin datos no hay modo *force recovery*, y por lo tanto no hay flasheo. Un cable de solo carga no sirve y cuesta una tarde descubrirlo. | Disponible — *probado con `lsusb`: (completar)* |
| Jumper de 2,54 mm, o un clip | Para puentear los pines del header J14 y entrar en *force recovery*. | *(completar)* |
| Cuenta de NVIDIA Developer | Gratuita, pero obligatoria para descargar SDK Manager y las imágenes. | *(completar)* |

## 3. Lo que se suma después

| Qué | Especificación exacta | Para qué |
|-----|----------------------|----------|
| **SSD NVMe M.2** | **Key M, tipo 2280, PCIe 3.0 x4.** La placa tiene además un slot Key M tipo **2230** a PCIe 3.0 x2 — más lento y más chico; el bueno es el 2280. | El medio de trabajo definitivo: más rápido, más espacio y el único lugar donde se puede poner **swap** (en la microSD el swap la destruye, §3.7). Acá va el proyecto de visión + IA. |
| **Cámara CSI** | Conector de **22 posiciones**, paso 0,5 mm. Las cámaras estilo Raspberry Pi traen flex de **15 pines**: hace falta el adaptador 15 → 22. | Documento [`07_camara_csi.md`](07_camara_csi.md). |
| Webcam USB | Cualquiera compatible con V4L2. | Plan B: anda sin configurar nada y permite avanzar con la inferencia aunque la CSI se complique. |

> **La nuestra:** SSD M.2 2280 NVMe **Gen4x4** de **250 GB**, modelo **MG43**. El slot de la placa es
> **PCIe 3.0 (Gen3) x4**, así que el disco va a andar a velocidad Gen3 y no a la Gen4 que soporta:
> es una limitación del slot, no una falla del disco. Falta confirmar acá: marca completa del
> disco, si trae disipador propio (el kit no incluye uno para el M.2, y a velocidad NVMe conviene
> ponerle uno o al menos un termopad) y el TBW/endurance si se va a usar para swap.

> **Pendiente que conviene resolver ya:** el **modelo exacto de sensor** de la cámara del
> laboratorio. Con **IMX219** o **IMX477** alcanza con `jetson-io.py` porque JetPack ya trae los
> drivers. Con un **IMX708** (Raspberry Pi Camera Module 3) hay que compilar kernel, y eso no es
> tarea de iniciación.

## 4. Los conectores de la placa, para saber qué se enchufa dónde

Según la [documentación de hardware oficial](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/hardware_layout.html):

- **1 × DisplayPort**. No hay HDMI y el USB-C tampoco da video.
- **4 × USB 3.2 Type-A**.
- **1 × USB-C**: host, device y **recovery**. Solo datos.
- **2 × conectores flex CSI de 22 posiciones** (CAM0 de 2 carriles, CAM1 de 2 o 4).
- **M.2 Key M 2280** (PCIe 3.0 x4) y **M.2 Key M 2230** (PCIe 3.0 x2).
- **M.2 Key E 2230**, ya ocupado por el módulo inalámbrico.
- **Jack DC 5,5 × 2,5 mm**.
- **Ranura microSD**: está en el **módulo**, no en la placa portadora — se accede por abajo.
- **Header J14** (1×12, paso 2,54 mm), debajo del módulo. No trae ningún botón puesto:

  | Pines | Función |
  |-------|---------|
  | 1 – 2 | Botón de encendido (sin poblar; se le puede conectar un pulsador NA) |
  | 3, 4, 7 | Consola serie: RXD, TXD y GND |
  | 7 – 8 | Puenteados, deshabilitan el auto-encendido |
  | 9 – 10 | **Force recovery** |

> **La placa no tiene botón de encendido y no hace falta.** De fábrica arranca sola apenas se le
> enchufa la fuente al jack DC: **enchufar es encender**. Para apagar, `sudo poweroff`.

## 5. Verificación antes de empezar

Dos comprobaciones de un minuto que evitan horas de diagnóstico equivocado:

```bash
# En la PC anfitriona: ¿el cable USB-C transporta datos?
# Enchufar cualquier dispositivo de datos con ese cable y ver si aparece.
lsusb

# ¿Hay espacio para SDK Manager?
df -h ~
```

## Con qué seguir

[`03_firmware_y_version_de_jetpack.md`](03_firmware_y_version_de_jetpack.md): leer qué firmware trae
la placa y decidir la versión de JetPack destino.
