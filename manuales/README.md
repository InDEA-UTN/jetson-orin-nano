# Manuales

Material de consulta sobre la Jetson Orin Nano y las herramientas que la rodean: la guía de uso,
referencias, procedimientos y notas para volver a mirar cuando ya se sabe lo que se busca. No están
pensados para leerse de corrido.

## Índice

| Manual | Contenido | Estado |
|--------|-----------|--------|
| `formas_de_trabajar.md` | **La guía de uso.** Las distintas maneras de trabajar con la placa y cuándo conviene cada una, con un ejemplo mínimo de cada una. Ver el detalle abajo. | Pendiente |
| `versiones_de_nuestra_placa.md` | Qué tiene instalado *esta* placa: JetPack, L4T, firmware, medio de arranque, tamaño del SSD, modelo de cámara. Con fecha e historial de cambios. | Pendiente |
| `comandos_utiles.md` | Los comandos que se usan todo el tiempo, agrupados por tarea: monitoreo, energía, cámara, red, contenedores, espacio en disco. | Pendiente |
| `camara_referencia.md` | Referencia de la cámara: modelo de sensor, resoluciones y fps disponibles, tuberías de GStreamer que funcionan, cómo se elige el sensor en el conector CSI. | Pendiente |
| `problemas_frecuentes.md` | Tabla de síntoma → causa probable → solución, alimentada con los problemas reales que nos fueron pasando. | Pendiente |
| `reinstalar_desde_cero.md` | El procedimiento de reflasheo completo, para cuando algo quedó irrecuperable. Incluye qué respaldar antes. | Pendiente |

## El manual de formas de trabajar

Es el documento más pedido de todo el repositorio y conviene que quede bien, porque es lo primero
que necesita alguien que ya tiene la placa andando y no sabe por dónde empezar a usarla. Dos ejes,
que son independientes entre sí:

**Cómo se llega a la placa:**

| Forma | Cuándo conviene |
|-------|-----------------|
| Monitor, teclado y mouse | Configuración inicial, cuando hay que ver el arranque o entrar al menú de firmware. |
| SSH desde otra máquina | El uso diario. Libera la RAM del escritorio gráfico y permite trabajar desde el propio equipo. |
| VS Code por *Remote SSH* | Desarrollar de verdad: editar en la placa con el editor de siempre. |
| Jupyter en la placa, navegador en la PC | Explorar, probar modelos y mostrar resultados con imágenes. |
| Consola serie por USB / red por USB-C | El salvavidas: cuando la placa no da video ni responde por red. |

**Dónde corre el código:**

| Forma | Cuándo conviene |
|-------|-----------------|
| Directo sobre el sistema (nativo) | Scripts, GStreamer, pruebas de cámara, cosas chicas. |
| Entorno virtual de Python | Proyectos propios en Python, para no ensuciar el sistema. Ojo: los paquetes con CUDA no salen de PyPI genérico. |
| Contenedores de NVIDIA (`jetson-containers`) | Todo lo que involucre PyTorch, TensorRT, LLMs o modelos de terceros. Es el camino recomendado y el que menos rompe. |
| Contenedor propio a partir de uno de NVIDIA | Cuando el proyecto ya tiene forma y hay que poder reproducirlo en otra placa. |

Para cada casilla, el manual debería tener **el ejemplo mínimo que se pega en una terminal y anda**:
el comando de SSH, el de lanzar un contenedor con GPU y cámara, el de abrir Jupyter, el de capturar
un frame. Los ejemplos que sean más que una línea van en [`../ejemplos/`](../ejemplos/) y se
referencian desde acá.

## Qué debe tener un manual

- Un título y un primer párrafo que digan de qué trata y a quién le sirve.
- Secciones cortas y con encabezados claros, para poder saltar directo a lo que se busca.
- Los datos concretos que uno va a venir a buscar: comandos, rutas, pines, versiones, valores.
- La fecha o versión sobre la que está escrito, cuando el contenido dependa de eso — en Jetson,
  casi siempre depende.

Cuando agregues un manual, sumá su fila al índice de arriba.
