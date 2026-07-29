# Guía de iniciación

El recorrido de arranque con la Jetson Orin Nano 8GB, en orden. Cada punto es un documento de esta
carpeta, numerado para que el orden de lectura sea evidente.

## Recorrido previsto

| # | Documento | Qué cubre | Estado |
|---|-----------|-----------|--------|
| 00 | [`00_antes_de_empezar.md`](00_antes_de_empezar.md) | Cómo arranca esta placa, las trampas conocidas y el vocabulario mínimo (JetPack, L4T, QSPI, modo recovery). Leerlo antes de tocar nada. | Escrito (de documentación, a validar en la placa) |
| 01 | `01_que_es_la_jetson_orin_nano.md` | Qué es el módulo Orin Nano 8GB y qué trae la placa portadora del kit. Para qué la queremos en el laboratorio. | Pendiente |
| 02 | `02_que_hace_falta.md` | Fuente, microSD, SSD NVMe, cable USB-C de datos, monitor DisplayPort, red y PC anfitriona. Qué de todo eso ya está en el laboratorio y qué hay que conseguir. | Pendiente |
| 03 | `03_firmware_y_version_de_jetpack.md` | Cómo ver qué versión de firmware trae la placa, qué versión de JetPack elegimos y por qué, y cómo actualizar el firmware si hace falta. | Pendiente |
| 04 | `04_instalacion_en_microsd.md` | Grabar la imagen en la microSD, primer arranque, configuración inicial de Ubuntu y verificación de que quedó bien. | Pendiente |
| 05 | `05_instalacion_en_ssd_nvme.md` | Montar el SSD M.2, poner la placa en modo *force recovery* y flashear a NVMe desde la PC anfitriona con SDK Manager. Verificación del arranque desde SSD. | Pendiente |
| 06 | `06_puesta_a_punto.md` | Lo que conviene dejar hecho una sola vez: `jtop`, modo de energía, swap, Docker, verificación de CUDA y de la versión instalada. | Pendiente |
| 07 | `07_camara_csi.md` | Conectar la cámara al conector CSI, configurar el conector, verificar que el sensor aparece y hacer la primera captura y la primera vista en vivo. | Pendiente |
| 08 | `08_primer_ejemplo_de_inferencia.md` | Un primer ejemplo de punta a punta: clasificar o detectar sobre el video de la cámara, y entender qué hizo cada parte. | Pendiente |

La numeración puede ajustarse a medida que se escribe; lo que importa es que el orden de lectura
quede claro y que cada documento diga con qué hay que seguir.

## Nota sobre el orden 04 / 05

Los dos caminos de instalación (microSD y SSD) están separados a propósito, y el de microSD va
primero, por dos razones:

- Es el camino más corto para confirmar que la placa, la fuente y el monitor funcionan. Si algo
  del hardware está mal, conviene descubrirlo antes de meterse con el flasheo por USB.
- Si el firmware de la placa es viejo, el arranque desde microSD con una imagen soportada es el
  procedimiento que la propia documentación de NVIDIA usa como puente para actualizarlo.

Igual el destino final es el SSD: es donde vamos a trabajar. La microSD queda como respaldo de
arranque, que es un lujo que conviene tener.
