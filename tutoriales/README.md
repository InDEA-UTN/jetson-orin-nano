# Tutoriales

Recorridos paso a paso sobre un tema concreto, para hacerlos de principio a fin con la placa en la
mano. A diferencia de la [guía de iniciación](../guia_de_iniciacion/), acá cada documento se puede
leer por separado, pero se da por supuesto que la placa ya está andando, con el sistema instalado y
la cámara funcionando.

Cada tutorial nuestro se apoya en un tutorial oficial o de la comunidad. **No lo copiamos.** Lo que
escribimos es el recorrido tal como salió en *nuestra* placa: la versión que usamos, los comandos
exactos, lo que falló y cómo lo resolvimos, y cuánto tardó o cuánto rindió. Eso es lo que no está en
el original y es lo que le va a servir al próximo.

## Índice

| # | Tutorial | Qué resuelve | Base | Estado |
|---|----------|--------------|------|--------|
| 01 | [`01_hello_ai_world.md`](01_hello_ai_world.md) | Poner a andar el primer modelo: clasificar imágenes y después el video de la cámara en vivo. Es el "hola mundo" de la Jetson. | [`jetson-inference`](https://github.com/dusty-nv/jetson-inference) | **Verificado en la placa** |
| 02 | [`02_deteccion_de_objetos.md`](02_deteccion_de_objetos.md) | Detección de objetos en vivo sobre la cámara, con cuadros y etiquetas. Medir los fps reales y compararlos entre modos de energía. | `jetson-inference` (`detectnet`) | **Verificado en la placa** |
| 03 | `03_entrenar_con_datos_propios.md` | Reentrenar un clasificador con imágenes nuestras (*transfer learning*) y correrlo en la placa. Primer ciclo completo de dato a modelo funcionando. | `jetson-inference` (PyTorch) | Pendiente |
| 04 | `04_de_onnx_a_tensorrt.md` | Tomar un modelo propio, exportarlo a ONNX, optimizarlo con TensorRT y medir la diferencia de velocidad con y sin optimizar. | TensorRT | Pendiente |
| 05 | `05_contenedores_en_la_jetson.md` | Usar `jetson-containers` para tener PyTorch y compañía sin romper el sistema: cómo se corre un contenedor con acceso a GPU y a la cámara. | [`jetson-containers`](https://github.com/dusty-nv/jetson-containers) | Pendiente |
| 06 | `06_un_llm_local.md` | Correr un modelo de lenguaje enteramente en la placa y ver hasta dónde llegan 8 GB: qué tamaño de modelo entra, a cuántos tokens por segundo y con qué cuantización. | [Jetson AI Lab](https://www.jetson-ai-lab.com/) | Pendiente |
| 07 | `07_ver_la_camara_desde_la_red.md` | Transmitir el video procesado por la red para verlo desde otra máquina, sin monitor conectado a la placa. | GStreamer / `jetson-inference` | Pendiente |

El orden es de dificultad creciente y cada uno se apoya en el anterior; conviene hacerlos así. Del
01 al 03 se aprende la plataforma; del 04 al 07 se aprende a sacarle provecho.

## Qué debe tener un tutorial

- **Objetivo**: qué se va a lograr al terminarlo, en una o dos oraciones.
- **Requisitos previos**: qué hay que tener hecho o instalado antes de arrancar, con enlace al
  documento correspondiente de la guía de iniciación.
- **Versiones**: JetPack, L4T y versión de lo que se instale. Sin esto el tutorial caduca en
  silencio.
- **Pasos numerados**, con el comando o la acción exacta y lo que se espera ver después de cada uno.
- **Verificación final**: cómo saber que salió bien.
- **Resultados medidos**, cuando aplique: fps, tiempo de inferencia, uso de RAM, modo de energía y
  temperatura. Un número sin el modo de energía al lado no dice nada.
- **Problemas frecuentes**: los errores con los que uno se chocó de verdad, y cómo salió de ellos.
- **Cuánto llevó**: el tiempo real, incluyendo descargas y compilaciones. Es el dato que más se
  agradece cuando alguien planifica su tarde.

Cuando agregues un tutorial, sumá su fila al índice de arriba y actualizá su estado.
