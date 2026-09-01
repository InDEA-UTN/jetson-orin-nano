# Proyectos

Desarrollos propios hechos con la placa. A diferencia de los [tutoriales](../tutoriales/), que
recorren un camino ya trazado por otro, acá el problema y la solución son nuestros: cada proyecto
arranca de un objetivo, se divide en fases verificables y termina en algo que funciona.

Cada proyecto vive en su carpeta, con su README de especificación, su código y su documentación
adentro.

## Índice

| Proyecto | Qué hace | Responsable | Estado |
|----------|----------|-------------|--------|
| [`espejo_facial_led/`](espejo_facial_led/) | Réplica de expresiones faciales en tiempo real sobre una matriz LED 8×8. La Jetson ve la cara con MediaPipe y manda un sprite de 8 bytes por UDP a un Pico W que maneja la matriz. | Lisandro Elmelaj | Funcionando de punta a punta desde el 31/08; pendientes: ajuste fino de umbrales, IP reservada para la Pico y video de demostración |

## Qué debe tener un proyecto

- **Objetivo**: qué se construye y para qué, en un párrafo.
- **Arquitectura**: qué parte hace qué, y por qué se dividió así.
- **Lista de materiales** y **conexionado**, si hay hardware de por medio.
- **Fases de ejecución** con su criterio de éxito, para poder verificar de a partes en vez de
  depurar todo junto al final.
- **Riesgos conocidos** y cómo se mitigan.
- **Versiones** de todo lo que se instale, como en el resto del repositorio.
- **Entregables**: qué queda cuando el proyecto se da por terminado.

Cuando agregues un proyecto, sumá su fila al índice de arriba y mantené su estado al día.
