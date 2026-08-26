# Versiones de nuestra placa

Qué tiene instalado *esta* placa en particular, con fecha, para poder responder rápido "¿qué
versión corre?" sin ir a buscarlo en la guía narrativa. El detalle de cómo se llegó a cada versión
y las trampas encontradas en el camino están en
[`../guia_de_iniciacion/`](../guia_de_iniciacion/), enlazada en cada fila.

**Escrito el 2026-08-20**, contra el estado real de la placa a esa fecha.

## Estado actual

| | Valor |
|---|---|
| **Módulo** | Orin Nano 8GB, variante **P3767-0005** (Developer Kit) |
| **Placa portadora** | P3768-0000 |
| **Firmware / QSPI** | `36.5.2` (subió sola de `36.4.3` al flashear el SSD — SDK Manager actualiza QSPI y sistema en la misma operación) |
| **JetPack** | 6.2.3 |
| **Jetson Linux (L4T)** | R36.5.2 |
| **Kernel** | 5.15, `aarch64` |
| **Medio de arranque por defecto** | SSD NVMe M.2 (`/dev/nvme0n1...`). La microSD (`/dev/mmcblk0...`) sigue intacta como respaldo — se elige a mano con **F11** en el arranque. |
| **SSD** | M.2 2280 NVMe **Gen4x4**, 250GB, modelo **MG43**. Corre a velocidad **Gen3** porque el slot de la placa es PCIe 3.0 x4, no por una limitación del disco. |
| **Modo de energía** | MAXN SUPER (`nvpmodel -m 2`), hasta 67 TOPS |
| **Swap** | Swapfile de 8GB en el SSD (reemplazó al zram de fábrica) |
| **Docker** | Runtime `nvidia` como default |
| **CUDA** | Runtime de la instalación + compilador `nvcc` 12.6 (`cuda-nvcc-12-6`) |
| **`jtop`** | 7.2.1 |
| **Cámara** | ArduCam UC-517 (sensor **IMX477**), conectada en **CAM1** |
| **Usuario del sistema** | `indea` |

## Historial de cambios

| Fecha | Qué cambió | Documento |
|---|---|---|
| 2026-07-30 | Firmware de fábrica leído en el menú UEFI: `36.4.3` (= generación JetPack 6.2). No hizo falta actualizarlo antes de instalar. | [`03_firmware_y_version_de_jetpack.md`](../guia_de_iniciacion/03_firmware_y_version_de_jetpack.md) |
| — | microSD grabada con la imagen de **JetPack 6.2.1** (L4T 36.4.4, con Balena Etcher) y subida a **JetPack 6.2.2** (L4T 36.5) con `apt full-upgrade`. NVIDIA no publica imagen de microSD para 6.2.2. | [`04_instalacion_en_microsd.md`](../guia_de_iniciacion/04_instalacion_en_microsd.md) |
| 2026-08-06 | SSD flasheado con **SDK Manager** (JetPack 6.2.3). El firmware subió de `36.4.3` a `36.5.2` en la misma operación. La placa pasa a arrancar por defecto desde el SSD. | [`05_instalacion_en_ssd_nvme.md`](../guia_de_iniciacion/05_instalacion_en_ssd_nvme.md) |
| 2026-08-11 | Puesta a punto sobre el SSD: `jtop` 7.2.1, modo MAXN SUPER, swapfile de 8GB (reemplazando zram), Docker con runtime `nvidia`, `cuda-nvcc-12-6`. Cámara ArduCam UC-517 (IMX477) configurada en CAM1: captura fija y vista en vivo por streaming UDP/RTP verificadas. | [`06_puesta_a_punto.md`](../guia_de_iniciacion/06_puesta_a_punto.md), [`07_camara_csi.md`](../guia_de_iniciacion/07_camara_csi.md) |
| 2026-08-20 | Primer ejemplo de inferencia verificado: contenedor `dustynv/jetson-inference:r36.3.0` (el tag exacto `r36.5.2` no existe publicado), TensorRT, clasificación con GoogLeNet sobre imagen fija. | [`08_primer_ejemplo_de_inferencia.md`](../guia_de_iniciacion/08_primer_ejemplo_de_inferencia.md) |

## Pendiente de completar acá

- Modelo/marca completa del disco SSD más allá de "MG43", si trae disipador propio y su TBW/endurance (anotado como pendiente también en [`02_que_hace_falta.md`](../guia_de_iniciacion/02_que_hace_falta.md)).
- Marca y clase exacta de la microSD.
- Watts de la fuente de 19V del kit.

## Con qué seguir

Para el detalle de cómo se llegó a cada versión, y las trampas reales encontradas en el camino, ver
el documento de la guía de iniciación enlazado en cada fila de arriba. Para comandos de
diagnóstico (`cat /etc/nv_tegra_release`, `apt-cache policy nvidia-jetpack`, etc.), ver
[`comandos_utiles.md`](comandos_utiles.md#firmware-e-identificación-de-la-placa).
