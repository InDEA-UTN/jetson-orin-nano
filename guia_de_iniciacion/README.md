# Guía de iniciación

El recorrido de arranque con la Jetson Orin Nano 8GB, en orden. Cada punto es un documento de esta
carpeta, numerado para que el orden de lectura sea evidente.

## Recorrido previsto

| # | Documento | Qué cubre | Estado |
|---|-----------|-----------|--------|
| 00 | [`00_antes_de_empezar.md`](00_antes_de_empezar.md) | Cómo arranca esta placa, las trampas conocidas y el vocabulario mínimo (JetPack, L4T, QSPI, modo recovery). Leerlo antes de tocar nada. | Escrito (de documentación, a validar en la placa) |
| 01 | `01_que_es_la_jetson_orin_nano.md` | Qué es el módulo Orin Nano 8GB y qué trae la placa portadora del kit. Para qué la queremos en el laboratorio. | Pendiente |
| 02 | [`02_que_hace_falta.md`](02_que_hace_falta.md) | Fuente, microSD, SSD NVMe, cable USB-C de datos, monitor DisplayPort, red y PC anfitriona. Qué de todo eso ya está en el laboratorio y qué hay que conseguir. | Escrito (falta completar modelos concretos) |
| 03 | [`03_firmware_y_version_de_jetpack.md`](03_firmware_y_version_de_jetpack.md) | Cómo ver qué versión de firmware trae la placa, qué versión de JetPack elegimos y por qué, y cómo actualizar el firmware si hace falta. | **Verificado en la placa** — vino con firmware 36.4.3 |
| 04 | [`04_instalacion_en_microsd.md`](04_instalacion_en_microsd.md) | Grabar la imagen con Etcher, primer arranque, configuración de Ubuntu, subida a 6.2.2 y verificación. Incluye el camino por SDK Manager para firmware viejo. | Escrito (pendiente de ejecutar en la placa) |
| 05 | [`05_instalacion_en_ssd_nvme.md`](05_instalacion_en_ssd_nvme.md) | Montar el SSD M.2, poner la placa en modo *force recovery* y flashear a NVMe desde la PC anfitriona con SDK Manager. Dual boot con la microSD y cómo elegir entre las dos con F11. | **Verificado en la placa** — arranca desde el SSD |
| 06 | `06_puesta_a_punto.md` | Lo que conviene dejar hecho una sola vez: `jtop`, modo de energía, swap, Docker, verificación de CUDA y de la versión instalada. | Pendiente |
| 07 | `07_camara_csi.md` | Conectar la cámara al conector CSI, configurar el conector, verificar que el sensor aparece y hacer la primera captura y la primera vista en vivo. | Pendiente |
| 08 | `08_primer_ejemplo_de_inferencia.md` | Un primer ejemplo de punta a punta: clasificar o detectar sobre el video de la cámara, y entender qué hizo cada parte. | Pendiente |

La numeración puede ajustarse a medida que se escribe; lo que importa es que el orden de lectura
quede claro y que cada documento diga con qué hay que seguir.

## Nota sobre el orden 04 / 05

Los dos caminos de instalación (microSD y SSD) están separados a propósito, y el de microSD va
primero, por dos razones:

- Es el camino más corto para confirmar que la placa, la fuente y el monitor funcionan. Si algo
  del hardware está mal, conviene descubrirlo antes de sumar variables.
- El SSD todavía no está en el laboratorio.

Antes figuraba acá una tercera razón — que el arranque desde microSD es el puente oficial para
actualizar el firmware viejo. **Eso vale solo si no hay PC anfitriona con Ubuntu.** Como sí la
tenemos, el firmware se actualiza con SDK Manager en la misma operación que la instalación, y el
rodeo por JetPack 5.1.3 no hace falta. Está explicado en
[`03_firmware_y_version_de_jetpack.md`](03_firmware_y_version_de_jetpack.md).

Igual el destino final es el SSD: es donde va a correr el proyecto de visión + IA, y es el único
lugar donde se puede poner swap. La microSD queda para proyectos generales y como respaldo de
arranque, que es un lujo que conviene tener.
