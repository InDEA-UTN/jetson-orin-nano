# 01 — Qué es la Jetson Orin Nano

La **Jetson Orin Nano Developer Kit (8 GB)** es un kit de desarrollo embebido de NVIDIA pensado
para correr inteligencia artificial *en el borde* (*edge AI*): visión por computadora, robótica,
procesamiento de señales. No es una PC de escritorio ni un reemplazo de una — es una placa chica,
de bajo consumo, con una GPU integrada capaz de correr modelos de IA en tiempo real sin depender de
la nube.

El kit son en realidad **dos piezas separadas**: el **módulo** (la computadora en sí) enchufado
sobre la **placa portadora** (la que trae los conectores). La distinción importa para todo lo
demás en esta guía — ver el vocabulario mínimo en
[`00_antes_de_empezar.md`](00_antes_de_empezar.md#1-vocabulario-mínimo).

## El módulo (System-on-Module)

El módulo trae el SoC **Orin Nano 8GB**: CPU, GPU, RAM y firmware en una sola plaqueta.

| | |
|---|---|
| **CPU** | 6 núcleos Arm Cortex-A78AE |
| **GPU** | Arquitectura NVIDIA Ampere, 1024 núcleos CUDA + 32 Tensor Cores |
| **RAM** | 8 GB LPDDR5, **compartida entre CPU y GPU** — no hay VRAM aparte (implicancias en [§3.7 de `00_antes_de_empezar.md`](00_antes_de_empezar.md)) |
| **Rendimiento de IA** | 40 TOPS de base, hasta **67 TOPS** en modo MAXN SUPER (cómo activarlo: [§3.8 de `00_antes_de_empezar.md`](00_antes_de_empezar.md)) |

**Nuestro módulo puntual: `P3767-0005`** — la variante empaquetada con el Developer Kit (distinta
de la `P3767-0003`, que se vende suelta para quien diseña su propia placa portadora). Cómo se
confirma en la placa: [`05_instalacion_en_ssd_nvme.md` §3](05_instalacion_en_ssd_nvme.md).

## La placa portadora (carrier board)

Es la placa de abajo del kit, con todos los conectores: USB, red, DisplayPort, M.2, CSI, jack de
alimentación. La nuestra es la `P3768-0000`. El detalle completo de cada conector ya está tabulado
en [`02_que_hace_falta.md` §4](02_que_hace_falta.md) — acá solo lo que más se nota al venir de una
Raspberry Pi:

- **No tiene HDMI**, solo DisplayPort ([§3.3](00_antes_de_empezar.md)).
- **No tiene botón de encendido**: enchufar la fuente es encender ([§4 de `02_que_hace_falta.md`](02_que_hace_falta.md)).
- Los conectores de cámara son flex CSI de **22 pines**, no los de 15 pines de las cámaras estilo
  Raspberry Pi ([§3.4](00_antes_de_empezar.md)).
- El USB-C **no alimenta la placa**, es solo datos ([§3.2](00_antes_de_empezar.md)).

## Para qué la queremos en el laboratorio

El destino es un **proyecto de visión por computadora + IA embebida**: correr modelos de
clasificación/detección en tiempo real sobre una cámara conectada a la placa, aprovechando la GPU
integrada en vez de depender de un servidor externo. Los próximos documentos de esta guía cubren
esa parte: la cámara CSI en [`07_camara_csi.md`](07_camara_csi.md) y un primer ejemplo de
inferencia de punta a punta en [`08_primer_ejemplo_de_inferencia.md`](08_primer_ejemplo_de_inferencia.md).

## Fuentes oficiales

- [Guía de usuario del Jetson Orin Nano Developer Kit](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/) —
  specs completas del módulo y la placa.
- [Documentación de hardware / layout de conectores](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/hardware_layout.html) —
  la misma fuente que usa [`02_que_hace_falta.md`](02_que_hace_falta.md) para el detalle de puertos.

## Con qué seguir

[`02_que_hace_falta.md`](02_que_hace_falta.md): qué hardware hace falta antes de conectar la
placa por primera vez.
