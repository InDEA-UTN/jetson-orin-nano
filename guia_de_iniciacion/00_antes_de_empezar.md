# 00 — Antes de empezar

Este documento no tiene pasos para ejecutar. Es lo que conviene entender **antes** de conectar la
placa, más una lista de las trampas conocidas de esta plataforma. La Jetson Orin Nano se parece por
fuera a una Raspberry Pi, y no arranca ni se actualiza como una Raspberry Pi: casi todos los
problemas del principio salen de ahí.

> **Origen de este documento.** Está escrito a partir de la documentación oficial de NVIDIA y de
> material de la comunidad, **antes** de tener la placa en marcha. Sirve como mapa y como lista de
> advertencias, no como registro de lo que pasó. A medida que se recorra la guía, cada punto de acá
> hay que confirmarlo o corregirlo contra lo que realmente ocurrió, y anotar la versión con la que
> se verificó. Si algo de este documento resulta falso en la práctica, se corrige acá mismo.

## 1. Vocabulario mínimo

Sin estos seis términos no se entiende ninguna página de documentación de Jetson.

| Término | Qué es |
|---------|--------|
| **Módulo** | La computadora en sí: el System-on-Module con el SoC Orin, la RAM y el firmware. Es la plaquita que va enchufada arriba. |
| **Placa portadora** (*carrier board*) | La placa de abajo, con los conectores: USB, red, DisplayPort, M.2, CSI, jack de alimentación. El *Developer Kit* es módulo + portadora. |
| **Jetson Linux** / **L4T** | El sistema operativo base: Ubuntu adaptado por NVIDIA, con su kernel, su bootloader y sus drivers. Se versiona aparte, por ejemplo *L4T 36.5*. |
| **JetPack** | El paquete completo: Jetson Linux + CUDA + cuDNN + TensorRT + herramientas. Es la versión que uno nombra en la práctica, por ejemplo *JetPack 6.2.2*. Cada JetPack corresponde a un L4T. |
| **QSPI** | Una memoria flash **en el módulo**, separada de la microSD y del SSD, donde vive el firmware de arranque (UEFI). Es la protagonista de la trampa nº 1. |
| **Modo *force recovery*** | Un modo especial de arranque en el que la placa no arranca su sistema, sino que se deja programar desde una PC por el puerto USB-C. Es la única forma de escribir el firmware y de instalar en el SSD. Se entra puenteando los **pines 9 y 10 del header J14** (debajo del módulo) **con la placa desalimentada**, y recién después enchufando la fuente. |

Dos herramientas que van a aparecer todo el tiempo:

- **SDK Manager**: la aplicación de NVIDIA que corre en una PC con Ubuntu x86_64 y flashea la
  placa (firmware y sistema operativo, incluyendo instalación directa en SSD NVMe).
- **`jtop`**: monitor de la placa (CPU, GPU, RAM, temperatura, versión de JetPack). No viene
  instalado; se instala con `sudo pip3 install -U jetson-stats` y necesita reiniciar. Es lo primero
  que conviene tener.

## 2. Cómo arranca esta placa

El orden es este:

1. Se aplica alimentación.
2. El módulo ejecuta el **firmware UEFI que tiene en su QSPI**.
3. Ese firmware busca un sistema operativo y lo carga: desde la **microSD**, desde un **SSD NVMe**
   en el slot M.2, o desde USB.

La consecuencia práctica, y es la idea más importante de todo el documento:

> **El firmware del módulo y la versión del sistema operativo tienen que ser compatibles.** El
> firmware no está en la tarjeta: está en el módulo. Grabar una imagen nueva en la microSD no
> actualiza el firmware.

De ahí sale la diferencia con una Raspberry Pi: ahí grabar la tarjeta es todo lo que hay que hacer.
Acá, si el firmware es más viejo que la imagen, la placa simplemente **no arranca** —
característicamente con pantalla negra y sin ningún mensaje de error útil. No está rota: le falta
el firmware.

## 3. Las trampas

### 3.1 Firmware viejo + imagen nueva = no arranca (la más importante)

> **Verificado el 30/07/2026: a nuestra placa esta trampa no le tocó.** El UEFI reportó firmware
> **`36.4.3`** (= JetPack 6.2), o sea generación 6, así que arranca imágenes 6.x directo y no hubo
> que actualizar nada. Igual **hay que leer el firmware antes de instalar**: es lo que decide el
> camino, y es un minuto.

Las Orin Nano que salieron de fábrica con JetPack 5.x traen firmware anterior a la versión 36.0, y
**ese firmware no puede arrancar una imagen de JetPack 6.x**. Hay que actualizarlo primero. Los dos
caminos, según la documentación oficial:

- **Camino por SDK Manager**: desde una PC con Ubuntu x86_64 nativo, con la placa en *force
  recovery*. Escribe la **QSPI y el sistema operativo en la misma operación**, y acepta tanto la
  **microSD** como el **SSD NVMe** como destino. Si hay PC anfitriona, **es el camino corto**: un
  solo procedimiento resuelve firmware e instalación, sin importar de qué versión se venga. Y es
  obligatorio si el destino es el SSD.

- **Camino puente por microSD**, para quien **no** tiene esa PC: grabar y arrancar la imagen de
  **JetPack 5.1.3** (NVIDIA publica una imagen específica para esto), verificar que la actualización
  de bootloader quedó agendada e instalar el paquete actualizador de QSPI:

  ```bash
  sudo systemctl status nv-l4t-bootloader-config
  sudo apt update
  sudo apt install nvidia-l4t-jetson-orin-nano-qspi-updater
  ```

  Después de que reinicie y actualice la QSPI, se cambia la microSD por la de la versión destino.
  Son dos descargas grandes, tres reinicios y dos esperas a ciegas.

Para ver qué firmware tiene la placa: apretar **Esc** durante la pantalla de arranque de NVIDIA
para entrar al menú de UEFI, y leer la versión ahí. Sin monitor, lo mismo por consola serie.

**Esto hay que hacerlo antes de cualquier otra cosa**, y es lo primero que el documento
[`03_firmware_y_version_de_jetpack.md`](03_firmware_y_version_de_jetpack.md) tiene que resolver y
dejar registrado: qué versión de firmware traía *nuestra* placa y qué camino usamos.

**Versiones vigentes (julio 2026).** Los números envejecen rápido; conviene confirmarlos contra la
página de descargas antes de bajar nada.

- **JetPack 6.2.2** = Jetson Linux 36.5, Ubuntu 22.04, kernel 5.15. Es la línea madura para Orin y
  la que elegimos. Ojo: **NVIDIA no publica imagen de microSD de 6.2.2** — se instala **6.2.1** y se
  sube a 6.2.2 con `apt`, que es legítimo porque no cambia la versión mayor (ver §3.6).
- **JetPack 7.2** = Jetson Linux 39.2, Ubuntu 24.04. Ya alcanza a la familia Orin, pero **exige
  firmware de generación 36.x igual**, así que no ahorra ningún paso, y el material de tutoriales
  todavía está migrando.

### 3.2 El puerto USB-C no alimenta la placa

Es **solo datos** (modo host, modo device y modo recovery). La alimentación entra por el **jack DC
de 5,5 × 2,5 mm**, a 19 V (la fuente del kit es de 19 V; conviene anotar los watts de la etiqueta de
la nuestra). Alimentar de menos es una causa clásica de reinicios espontáneos y de fallas que
parecen de software.

Y al revés: para flashear hace falta un **cable USB-C que transporte datos**. Un cable de solo carga
no sirve, y es una hora perdida buscando el problema en otro lado.

### 3.3 No hay HDMI

La salida de video es **DisplayPort** únicamente. Si el monitor es HDMI hace falta un adaptador
DisplayPort → HDMI, y conviene que sea activo. Vale la pena confirmar qué monitores hay disponibles
en el laboratorio antes de empezar.

### 3.4 Los conectores de cámara son de 22 pines, no de 15

La placa tiene **dos conectores flex MIPI CSI de 22 posiciones, paso 0,5 mm, contacto abajo**. Las
cámaras estilo Raspberry Pi usan flex de **15 pines**. Hace falta el cable o adaptador 15 → 22, y
muchos módulos vendidos "para Jetson" ya lo incluyen.

Sobre los sensores: JetPack trae drivers de fábrica para **IMX219** (el de la Raspberry Pi Camera
v2) y para **IMX477** (el de la Raspberry Pi HQ Camera). Con esos dos, la cámara se habilita
eligiendo el sensor en la utilidad de configuración del conector:

```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
```

En cambio, sensores más nuevos como el **IMX708** (Raspberry Pi Camera Module 3) **no tienen driver
en JetPack**: requieren un driver de terceros y compilar kernel, que no es una tarea de iniciación.
Una webcam USB, por contraste, funciona directo por V4L2 sin configurar nada, y es un buen plan B
para no quedar bloqueado.

> **Pendiente concreto:** identificar el modelo exacto de sensor de la cámara que compró el
> laboratorio, y con qué flex viene. De eso depende todo el documento
> `07_camara_csi.md`.

### 3.5 `pip install torch` no sirve acá

La Jetson es **aarch64 con CUDA**. Las ruedas genéricas de PyPI no traen soporte de CUDA para esta
combinación: se instalan sin error y después no ven la GPU. Hay que usar las ruedas que publica
NVIDIA para Jetson (o el índice de paquetes de Jetson AI Lab), y la rueda tiene que corresponder a
la versión de JetPack instalada.

La alternativa más robusta, y la que conviene documentar como camino principal, es **usar los
contenedores** de NVIDIA (`jetson-containers`): ya vienen con PyTorch, TensorRT y compañía
compilados y consistentes con el JetPack de la placa. Instalar el stack de IA a mano en Jetson es
una fuente inagotable de tardes perdidas.

Verificación rápida de que la GPU está visible desde Python:

```python
import torch
print(torch.__version__, torch.cuda.is_available())
```

Nota al margen: `nvidia-smi` no es la herramienta acá (la GPU es integrada). Se usa `tegrastats` o
`jtop`.

### 3.6 Cuidado con `apt upgrade` y con los paquetes `nvidia-l4t-*`

Dentro de una misma versión de JetPack, actualizar está bien. Lo que no hay que hacer es:

- **Saltar de una versión mayor de JetPack a otra por `apt`** creyendo que es una actualización
  normal. Cambiar de JetPack 5.x a 6.x implica cambio de Ubuntu, de kernel y de firmware: es
  reinstalación, no actualización.
- **Desinstalar o pisar paquetes `nvidia-l4t-*`**, ni instalar drivers de NVIDIA de escritorio o
  CUDA "de PC". Los de la placa ya vienen con JetPack y son los únicos que sirven.
- Agregar repositorios de terceros de Ubuntu genérico que reemplacen bibliotecas del sistema.

Cuando algo se rompe de esta manera, el camino de vuelta suele ser reflashear. Vale la pena que la
guía diga esto en voz alta.

### 3.7 8 GB de RAM son compartidos entre CPU y GPU

No hay memoria de video aparte: los 8 GB son de todo el sistema. Los modelos de IA de hoy llenan
eso rápido. Dos medidas que se hacen una vez y ayudan siempre:

- **Trabajar sin escritorio gráfico** cuando se corre algo pesado; libera cientos de megabytes:

  ```bash
  sudo systemctl set-default multi-user.target   # arranca sin escritorio
  sudo systemctl set-default graphical.target    # para volver atrás
  ```

- **Tener swap en el SSD**, y **solo** en el SSD. En la microSD **no**: el swap la escribe sin parar
  y la destruye en poco tiempo. Mientras no haya SSD, la medida realista es la anterior — trabajar
  sin escritorio gráfico. Ayuda sobre todo al compilar y al cargar modelos grandes.

Este es, además, el argumento principal para instalar en SSD y no en microSD.

### 3.8 El "modo Super" hay que habilitarlo

El mismo hardware Orin Nano 8GB rinde 40 TOPS en sus modos originales y hasta **67 TOPS** en el modo
de energía **MAXN SUPER**, que NVIDIA habilitó a partir de **JetPack 6.2**. No viene activo por
defecto:

```bash
sudo nvpmodel -q      # ver el modo actual y los disponibles
sudo nvpmodel -m 2    # seleccionar MAXN SUPER (confirmar el número con -q)
```

Si en `nvpmodel -q` no aparece un modo SUPER, es por la versión de JetPack o por la configuración
con la que se flasheó la placa. Dos advertencias: es un modo **sin techo de consumo**, así que
exige que la fuente y el ventilador estén a la altura, y si se pasa del presupuesto térmico el
módulo baja la frecuencia solo. Todo *benchmark* que anotemos tiene que decir en qué modo de
energía se corrió, o no se puede comparar con nada.

### 3.9 La microSD importa

Tiene que ser rápida (clase **A2**, 64 GB o más) y de marca conocida. Una tarjeta lenta o falsa se
manifiesta como un sistema que tarda minutos en arrancar, se cuelga o corrompe archivos. Muchos
"la placa no anda" son "la tarjeta no anda".

### 3.10 Para flashear hace falta una PC con Ubuntu x86_64

SDK Manager corre en Ubuntu sobre x86_64. Ni macOS ni Windows nativo, y en máquina virtual el
*passthrough* del USB durante el reinicio de la placa falla seguido: si se puede, mejor una PC con
Ubuntu instalado de verdad. **Conviene resolver esto antes de arrancar**, porque sin ese equipo no
hay actualización de firmware ni instalación en SSD.

## 4. Cómo saber en qué estado está la placa

Comandos para dejar registrados al principio de cada documento de la guía, con su salida real:

```bash
cat /etc/nv_tegra_release              # versión de Jetson Linux (L4T)
apt-cache show nvidia-jetpack | head   # versión de JetPack instalada
dpkg -l | grep nvidia-l4t-bootloader   # versión del paquete de bootloader
uname -a                               # kernel y arquitectura
nvpmodel -q                             # modo de energía actual
df -h                                   # de dónde está arrancando y cuánto espacio queda
jtop                                    # vista general (si ya está instalado)
```

## 5. Fuentes oficiales

Cuando algo de este repositorio contradiga a estas páginas, ganan ellas — y hay que corregir el
documento.

- [Guía de usuario del Jetson Orin Nano Developer Kit](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/) —
  inicio rápido, layout del hardware y **camino de actualización de firmware**.
- [Descargas y notas de JetPack](https://developer.nvidia.com/embedded/jetpack/downloads) — qué
  versión está vigente y qué trae.
- [Documentación de Jetson Linux](https://docs.nvidia.com/jetson/archives/) — el detalle fino del
  BSP, el flasheo y las cámaras.
- [Jetson AI Lab](https://www.jetson-ai-lab.com/) — tutoriales de IA generativa, visión y LLMs
  corriendo en la placa, con contenedores listos.
- [`dusty-nv/jetson-inference`](https://github.com/dusty-nv/jetson-inference) — *Hello AI World*:
  el recorrido clásico de clasificación, detección y segmentación con cámara.
- [`dusty-nv/jetson-containers`](https://github.com/dusty-nv/jetson-containers) — contenedores para
  Jetson (PyTorch, TensorRT, Ollama, llama.cpp, Whisper y demás).
- [JetsonHacks](https://jetsonhacks.com/) — material de la comunidad, muy útil para cámaras CSI e
  instalación en SSD. No es oficial: verificar contra la documentación de NVIDIA.
- [Foros de desarrolladores de Jetson](https://forums.developer.nvidia.com/c/robotics-edge-computing/jetson-systems/) —
  donde se resuelven los casos raros; conviene buscar acá antes de preguntar.

## 6. Orden sugerido de trabajo

1. Conseguir la PC con Ubuntu x86_64, el cable USB-C de datos y el adaptador de video (§3.10, §3.2,
   §3.3).
2. Identificar el modelo de la cámara y su flex (§3.4).
3. Ver la versión de firmware de la placa y decidir la versión de JetPack objetivo (§3.1).
4. Instalación en microSD con SDK Manager, que **actualiza el firmware en la misma operación**.
   Sirve además para confirmar que la placa, la fuente y el monitor están sanos antes de complicar.
5. Puesta a punto: `jtop`, modo de energía, Docker, verificación de CUDA.
6. Cámara y primer ejemplo de inferencia.
7. Instalación en SSD NVMe cuando esté el disco: el mismo procedimiento del punto 4 cambiando el
   destino. Recién ahí, swap.

Sin PC anfitriona el orden es otro: el puente por JetPack 5.1.3 (§3.1) va antes del punto 4, y la
instalación en SSD no es posible hasta conseguirla.

Y una regla de trabajo: **anotar mientras se hace, no después**. El valor de este repositorio no
está en el resultado final sino en los pasos intermedios y en los errores, que es exactamente lo que
uno olvida al día siguiente.
