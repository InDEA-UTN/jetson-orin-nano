# Ejemplos

Código mínimo y funcional que acompaña a los documentos de este repositorio. La regla es una sola:
**acá solo entra lo que se ejecutó en la placa y funcionó**, con un comentario arriba que diga con
qué versión de JetPack se probó y en qué fecha. Un ejemplo que no se corrió no es un ejemplo, es una
suposición: esos van dentro del documento correspondiente, marcados como pendientes de verificar.

## Índice

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| [`verificar_entorno.sh`](verificar_entorno.sh) | Junta en una sola salida el estado de la placa: versión de L4T y JetPack, kernel, modo de energía, medio de arranque, espacio libre, cámaras detectadas y presencia de CUDA. Útil para pegar al principio de cualquier documento o al reportar un problema. | Escrito (pendiente de correr en la placa) |
| `camara_csi_vista_en_vivo.sh` | Abrir la cámara CSI y mostrarla en pantalla con GStreamer. | Pendiente |
| `camara_captura_frame.py` | Capturar un frame de la cámara y guardarlo, con OpenCV. | Pendiente |
| `verificar_cuda.py` | Confirmar desde Python que PyTorch ve la GPU. | Pendiente |
| `medir_fps.py` | Medir fps de un modelo, para poder comparar entre modos de energía. | Pendiente |

Cuando agregues un ejemplo, sumá su fila y enlazalo desde el documento que lo usa.
