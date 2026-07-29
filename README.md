# Jetson Orin Nano 8GB — Guía de iniciación

Documentación de puesta en marcha y uso de la **NVIDIA Jetson Orin Nano Developer Kit (8 GB)**,
escrita en el laboratorio **InDEA** (Investigación y Desarrollo en Electrónica Aplicada) de la
Universidad Tecnológica Nacional, Facultad Regional Mendoza (**UTN FRM**).

El objetivo es que alguien que nunca tocó la placa pueda, siguiendo estos documentos en orden,
llegar a tener el sistema operativo instalado, la cámara andando y un primer ejemplo de inferencia
corriendo, sin depender de que haya otra persona al lado explicándole.

Esta placa la compramos justamente **para aprender**: nadie acá es experto en Jetson. Por eso el
repositorio se escribe desde cero y con una regla firme: *se documenta lo que se hizo y se
verificó en esta placa*, anotando siempre la versión de software con la que se hizo. Lo que se
copió de la documentación oficial pero todavía no se probó, se marca como tal.

## Qué cubre

1. **Instalación del sistema operativo en microSD** — el camino corto para tener la placa andando.
2. **Instalación del sistema operativo en SSD NVMe** — el camino recomendado para trabajar de
   verdad: más rápido, más espacio y menos desgaste que la microSD.
3. **Cámara CSI** — conexión, configuración del conector y primera captura.
4. **Proyectos tutoriales** — recorridos de NVIDIA y de la comunidad, hechos de punta a punta.
5. **Guía de uso** — las distintas maneras de trabajar con la placa (nativo, contenedores, remoto)
   con ejemplos mínimos de cada una.

## Cómo está organizado

| Ruta | Contenido |
|------|-----------|
| [`guia_de_iniciacion/`](guia_de_iniciacion/) | El recorrido de arranque, en orden: qué es la placa, qué hace falta, firmware, instalación en microSD y en SSD, puesta a punto y cámara. Es por acá por donde se empieza. |
| [`tutoriales/`](tutoriales/) | Recorridos paso a paso sobre un tema concreto, pensados para hacerlos de principio a fin con la placa en la mano. Acá van los proyectos tutoriales. |
| [`manuales/`](manuales/) | Material de consulta: las formas de trabajar con la placa, referencias de comandos, procedimientos y notas para volver a mirar cuando ya se sabe lo que se busca. |
| [`ejemplos/`](ejemplos/) | Código mínimo y funcional que acompaña a los documentos: scripts de captura, de inferencia y de verificación. |

Si es la primera vez que abrís este repositorio, empezá por
[`guia_de_iniciacion/00_antes_de_empezar.md`](guia_de_iniciacion/00_antes_de_empezar.md). Está
escrito antes que el resto a propósito: explica cómo arranca esta placa (que **no** es como una
Raspberry Pi ni como la Jetson Nano vieja) y cuáles son las cuatro o cinco trampas en las que se
traba todo el mundo. Leerlo primero ahorra días.

## Estado

En construcción. El contenido se va cargando a medida que se escribe; si una carpeta todavía no
tiene documentos, es porque esa parte está pendiente. El estado de cada documento está en el
índice de su carpeta.

## Quiénes lo mantienen

- **Responsable:** Lisandro Elmelaj ([@lisandroelmelaj](https://github.com/lisandroelmelaj))
- **Revisor:** Javier Velez ([@javovelez](https://github.com/javovelez)), director del laboratorio

El seguimiento del trabajo (bitácora, horas, objetivos) no va acá: vive en el repositorio privado
de gestión del laboratorio. Este repositorio es **solo documentación técnica**, y es público.

## Cómo contribuir

1. Trabajá en una rama aparte (por ejemplo `guia-camara-csi`), nunca directo sobre `main`.
2. Escribí en español, en Markdown, con oraciones cortas y sin dar por sabido lo que un lector
   nuevo no tiene por qué saber.
3. **Anotá siempre la versión.** JetPack, Jetson Linux (L4T), versión de firmware y modelo exacto
   del hardware. Un procedimiento de Jetson sin número de versión no sirve: en la versión
   siguiente puede no andar.
4. Pegá los comandos tal como se ejecutaron y la salida real que devolvieron, no una reconstrucción
   de memoria.
5. Si el documento tiene imágenes, guardalas en una carpeta `imagenes/` al lado del documento.
6. Abrí un *pull request* hacia `main`. La revisión queda a cargo del revisor del repositorio.
7. Una vez aprobado, se hace *merge* y se borra la rama.

## Licencia

Pendiente de definir.
