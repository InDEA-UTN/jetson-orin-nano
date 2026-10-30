# Extensión LCD — texto de señas en una pantalla 16x2

**Estado.** Al 29/10/2026: **el LCD funciona de punta a punta con el reconocedor** — mano →
letra → texto en el LCD, probado contra el hardware real. Antes, el 23/10, se había verificado
el LCD aislado (`i2c.scan()` responde en `0x27`, `demo_lcd.py` escribe). Desde el 29/10 **la
matriz quedó reservada para el espejo facial**: el reconocedor de señas ya no le manda la letra
(`MANDAR_A_MATRIZ = False`). **Implementado pero todavía sin probar:** correr los dos proyectos a
la vez con dos cámaras (CSI para la cara, webcam USB para las señas) — ver "Los dos proyectos a
la vez".

Antes hay que haber hecho: el pipeline del [README principal](../README.md) andando de punta a
punta (cámara → letra → matriz).

## Objetivo

Sumar una pantalla LCD de caracteres para mostrar **el texto que se va escribiendo con señas**,
algo que la matriz 8×8 no puede (muestra una sola letra a la vez):

```
┌────────────────┐
│HOLA MUNDO      │  línea 1: el texto escrito (los últimos 16 caracteres)
│Letra: B      5 │  línea 2: letra confirmada + frames que faltan para escribirla
└────────────────┘
```

## Hardware

- **LCD 16x2 de 16 pines** (controlador HD44780, el estándar de casi todos los LCD de caracteres).
- **Módulo I2C soldado atrás, chip PCF8574T**, con 4 pines: GND, VCC, SDA, SCL. Habla **I2C, no
  SPI** (SPI es lo que usa la matriz).

### Cómo funciona el módulo

El LCD solo necesitaría unos 11 cables (RS, RW, E, 8 de datos, más alimentación y luz). El
PCF8574 es un **expansor de pines**: cada byte que recibe por I2C lo copia tal cual a sus 8
patitas de salida, que ya vienen soldadas a pines del LCD:

```
bit:   7    6    5    4    3     2    1    0
       D7   D6   D5   D4   LUZ   E    RW   RS
```

O sea: **desde la Pico no se controla ningún pin del LCD directamente — el byte que se manda por
I2C *es* el estado de esos pines**. "Prender E" significa mandar un byte con el bit 2 en 1.

- **RS**: 0 = el byte es un comando ("borrá", "andá a la línea 2"), 1 = es un carácter a escribir.
- **E**: el LCD toma los datos cuando E baja de 1 a 0 (el "pulso").
- **Modo 4 bits**: como solo quedan 4 patitas para datos (D4-D7), cada byte se manda en **dos
  mitades** (primero la alta, después la baja), cada una con su pulso de E. El HD44780 soporta
  este modo justamente para ahorrar cables.

Ejemplo real, escribir una `A` (`0x41` = `0100 0001`), con RS=1 y LUZ=1:

| Byte | D7-D4 | LUZ | E | RW | RS | Qué pasa |
|---|---|---|---|---|---|---|
| `0x4D` | 0100 | 1 | **1** | 0 | 1 | mitad alta, E arriba |
| `0x49` | 0100 | 1 | **0** | 0 | 1 | E baja → el LCD la toma |
| `0x1D` | 0001 | 1 | **1** | 0 | 1 | mitad baja, E arriba |
| `0x19` | 0001 | 1 | **0** | 0 | 1 | E baja → aparece la `A` |

### Por qué la dirección es `0x27`

I2C usa 2 cables compartidos (SCL = reloj, SDA = datos) y cada dispositivo tiene una dirección.
`i2c.scan()` pregunta por todas (`0x08`…`0x77`) y lista las que contestan. El PCF8574 tiene base
`0x20` más 3 pines de dirección (los pads A0/A1/A2 del módulo), que de fábrica están en 1:
`0x20 + 0b111 = 0x27`. La variante PCF8574**A**T arranca en `0x38` y queda en `0x3F`.

## Cableado (Pico W)

| Módulo LCD | Pico W | Pin físico |
|---|---|---|
| GND | GND | 8 |
| VCC | VBUS (5 V) | 40 |
| SDA | GP6 (I2C1) | 9 |
| SCL | GP7 (I2C1) | 10 |

- **Se usa I2C1 en GP6/GP7** porque la matriz ya ocupa GP2/GP3/GP5 (ver
  [`../../espejo_facial_led/README.md`](../../espejo_facial_led/README.md), sección 7): el otro
  par I2C posible, GP4/GP5, chocaría con el CS de la matriz en GP5.
- **El pin 40 (VBUS) lo comparten la matriz y el LCD** — se reparte con el riel `+` de una
  protoboard. Para GND se usó el pin 8 (al lado de GP6/GP7); todos los GND de la Pico son lo mismo.
- **Decisión consciente: 5 V directo, sin conversor de niveles.** El módulo trae resistencias
  pull-up a VCC, así que SDA/SCL quedan a 5 V sobre pines de 3.3 V de la Pico. Suele andar (las
  pull-up limitan la corriente) y es lo que hacen muchos tutoriales, pero es un riesgo asumido. Lo
  seguro sería un level shifter; alimentarlo a 3.3 V tampoco sirve bien porque la mayoría de estos
  LCD casi no tienen contraste a ese voltaje.
- **Contraste**: si se prende la luz pero no se ve texto (o solo una fila de cuadraditos), girar
  el potenciómetro azul de atrás del módulo.

## Los archivos

### `lcd_i2c.py` — el driver (va guardado en la Pico)

Escrito a mano en vez de bajar una librería, para que quede a la vista qué hace cada byte. Por
partes:

- **Constantes `RS`, `E`, `LUZ`**: posiciones de bit dentro del byte (no pines de la Pico).
  `INICIO_LINEA = (0x00, 0x40)`: la línea 2 empieza en la posición de memoria `0x40`, no en
  `0x10` — así está diseñado el HD44780.
- **`_nibble` / `_byte`**: mandan media palabra con el pulso de E (dos bytes, E=1 y E=0, en una
  sola transacción I2C) y un byte completo como dos mitades. Son la tabla de la `A` de arriba
  hecha código.
- **Secuencia de arranque (`__init__`)**: al encenderse no se sabe si el LCD quedó en modo 8 o 4
  bits (por ejemplo si se reinició la Pico pero el LCD nunca perdió alimentación). La hoja de
  datos indica mandar "modo 8 bits" (`0x30`) tres veces para llevarlo a un estado conocido, y
  recién ahí pasar a 4 bits (`0x20`). Después: `0x28` (2 líneas, 5×8), `0x08` (apagado),
  borrar, `0x06` (el cursor avanza solo), `0x0C` (prendido, sin cursor). Las esperas cumplen las
  mínimas de la hoja con margen; cada envío I2C ya tarda ~0.3 ms, más que lo que necesita
  cualquier comando salvo borrar (~1.5 ms, se esperan 2).
- **`mover`, `escribir`, `linea`**: lo que se usa desde afuera. `linea(fila, texto)` rellena con
  espacios hasta 16 columnas en vez de llamar a `borrar()` antes — los espacios pisan lo viejo y
  la pantalla no parpadea. Caracteres fuera de ASCII básico (ñ, tildes) se muestran como `?`: no
  existen en la tabla de caracteres del LCD.

### `demo_lcd.py` — prueba aislada, sin WiFi

Mismo rol que `demo_cara_feliz.py` para la matriz: probar cableado y driver antes de mezclarlo
con red. Imprime el `i2c.scan()` y escribe dos líneas. **Verificado el 23/10.**

Cómo correrlo en Thonny:

1. Abrir `lcd_i2c.py` y guardarlo **en la Pico** (*File → Save as… → Raspberry Pi Pico*, mismo
   nombre) — el demo lo importa desde ahí.
2. Abrir `demo_lcd.py` y darle **Run (F5)**. Este no hace falta guardarlo en la Pico.

## Cómo se conecta al reconocedor

### Mandar el estado completo, no letra por letra

La primera idea natural era que la Pico tome el mismo paquete de 8 bytes de la matriz y vaya
escribiendo letra por letra. No sirve, por tres razones:

1. **El paquete de 8 bytes son píxeles, no una letra.** La Pico no sabe qué letra está dibujando;
   y `del`, `space` y sin-mano mandan los tres el mismo sprite vacío.
2. **La letra confirmada se manda en cada frame (30 veces por segundo)**, no una vez por letra:
   sostener una `H` un segundo son 30 paquetes iguales. Escribiendo uno por paquete quedaría
   `HHHHHHHHHH…`. Saber cuándo una letra es "nueva" es justamente lo que hace
   `EstabilizadorLetra`, que vive en la Jetson.
3. **UDP pierde paquetes en silencio.** Mandando eventos ("agregá una B"), un paquete perdido es
   una letra perdida para siempre. Mandando **la pantalla entera** cada vez, un paquete perdido no
   importa: el siguiente trae todo y corrige solo — el mismo criterio que ya usa la matriz (ver
   "El envío por UDP: siempre, no solo cuando cambia" en el [README principal](../README.md)).

Entonces la Jetson, que es la que sabe qué texto hay escrito, le manda el texto ya armado, y la
Pico sigue siendo una "pantalla tonta" que muestra lo que le llega.

### El paquete de 33 bytes

```
 L  H O L A _ _ _ _ _ _ _ _ _ _ _ _  L e t r a : _ B _ _ _ _ _ _ 5
 ↑  └──────── línea 1: 16 ────────┘  └──────── línea 2: 16 ────────┘
 1  +            16                  +            16                 = 33
```

- 16×2 = 32 caracteres, 1 byte cada uno, más 1 byte de marca (`'L'`). La Jetson rellena con
  espacios: largo fijo = la Pico no tiene que buscar dónde termina cada línea, y los espacios
  borran lo que quedaba de un texto más largo (después de un `del`).
- **La Pico distingue por LARGO primero**: 8 bytes → matriz (sin mirar con qué empieza, porque un
  sprite puede empezar con `0x4C` = `'L'`, que es una fila válida `01001100`); 33 bytes **y**
  empieza con `'L'` → LCD; cualquier otra cosa se ignora. El espejo facial no se entera del
  cambio.
- **La Jetson manda en cada frame, pero la Pico solo reescribe el LCD si el texto cambió**:
  escribir 32 caracteres por I2C tarda ~15 ms, no tiene sentido hacerlo 30 veces por segundo.
- Si algún día se pasa a un 20×4: 80 + 1 = 81 bytes, se ajusta en los dos lados.

### Lado Pico: `main.py` (29/10)

No se hizo un `main.py` aparte: la Pico corre **uno solo**, así que se amplió el que ya existía en
[`../../espejo_facial_led/pico/main.py`](../../espejo_facial_led/pico/main.py) para que maneje
matriz y LCD. Necesita `lcd_i2c.py` guardado en la Pico al lado.

- **Al arrancar busca el LCD con `i2c.scan()`**. Si está, lo prende y muestra "Esperando..."
  hasta el primer paquete; si no, sigue solo con la matriz (`lcd = None`). Así el espejo facial
  anda igual sin el LCD conectado.
- **En el loop**: 33 bytes y empieza con `'L'` → LCD; 8 bytes → matriz, sin cambios; cualquier
  otra cosa se ignora.
- **Recuerda el último paquete de cada tipo** (`ultimo_texto`, `ultimo_sprite`): reescribe el LCD
  e imprime en la consola de Thonny solo cuando algo cambia. Antes imprimía cada sprite; con los
  dos tipos de paquete serían ~60 líneas por segundo, ilegibles.
- Los bytes se pasan a texto con `chr()` uno por uno, no con `.decode()`: un paquete con bytes
  raros haría fallar `.decode()` y mataría el script; así, `lcd_i2c` los muestra como `?`.

Se probó primero **sin el reconocedor**, mandando un paquete a mano desde la Jetson:

```bash
python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(b'L' + b'HOLA DESDE'.ljust(16) + b'LA JETSON'.ljust(16), ('10.42.0.170', 5005))"
```

### Lado Jetson: `enviar_a_lcd()` (29/10)

Agregada a [`../jetson/reconocer_letra.py`](../jetson/reconocer_letra.py) y
[`../jetson/reconocer_letra_stream.py`](../jetson/reconocer_letra_stream.py) (duplicada a
propósito, mismo criterio que `enviar_a_matriz()`). Se llama en cada frame, con o sin mano, y usa
el mismo socket, IP y puerto que la matriz.

- **Línea 1: `texto[-16:]`**, los últimos 16 caracteres. Al pasar de 16, el texto se corre a la
  izquierda y siempre se ve lo más reciente.
- **Línea 2: `Letra: B       5`**, la letra confirmada y los frames que faltan para escribirla. El
  formato (`:<5` y `:>3`) reserva lugar fijo, así entra en 16 incluso con `space` o `del`:

  ```
  Letra: B       5
  Letra: space  12
  Letra: -       -     ← sin mano
  ```

**Probado de punta a punta el 29/10**: mano → texto en el LCD.

## Los dos proyectos a la vez (para la presentación)

Idea: correr **el espejo facial y el de señas al mismo tiempo** en la Jetson, contra la misma Pico
— **la matriz para los gestos de cara y el LCD para las señas**. Son dos programas que no se
conocen: cada uno manda sus paquetes por su propio socket a la misma IP y puerto, y la Pico,
con un solo socket, los atiende uno por uno según el largo. Un paquete de cara nunca toca el
LCD y uno de señas nunca toca la matriz. En la consola de Thonny se distinguen por el puerto de
origen (`addr`), distinto para cada programa.

```
jetson_face.py      (cámara CSI) ──► 8 bytes  ──┐
                                                ├──► Pico 10.42.0.170:5005 ─┬─► matriz
reconocer_letra*.py (webcam USB) ──► 33 bytes ──┘                           └─► LCD
```

Lo hecho para eso (29/10):

1. **El reconocedor de señas ya no manda a la matriz.** Si los dos programas le mandaran sprites,
   titilaría entre la cara y la letra. Se hizo con un interruptor arriba de los dos scripts,
   `MANDAR_A_MATRIZ = False`, en vez de borrar el código: en `True` vuelve a mandar la letra, por
   si se quiere mostrar este proyecto solo. Mientras está en `False`, la matriz se queda con lo
   último que recibió (la Pico no la borra sola); Stop/Run de `main.py` en Thonny la limpia.
2. **Una cámara para cada uno.** Las dos cámaras se abren de formas completamente distintas, así
   que no se pueden confundir:
   - **Espejo facial → cámara CSI** (la que ya se había usado al principio de ese proyecto), por
     el pipeline de GStreamer `nvarguscamerasrc` ya verificado en
     [`../../espejo_facial_led/lado_jetson.md`](../../espejo_facial_led/lado_jetson.md)
     sección 5. Detalle en
     [`../../espejo_facial_led/integracion.md`](../../espejo_facial_led/integracion.md)
     sección 13. Además, no pasa por USB, así que no le quita ancho de banda a la webcam.
   - **Señas → webcam USB, por su nombre fijo**, constante `CAMARA` en los dos scripts:

     ```python
     CAMARA = "/dev/v4l/by-id/usb-SN0002_1080P_Web_Camera_SN0002-video-index0"
     cap = cv2.VideoCapture(CAMARA, cv2.CAP_V4L2)
     ```

     Hacía falta: con las dos conectadas, `ls /dev/video*` dio `video0 video1 video2` y
     `ls -l /dev/v4l/by-id/` mostró que la webcam es `video1` (`index0`, el video) y `video2`
     (`index1`, metadatos). **La CSI se quedó con `video0`**: el `VideoCapture(0)` de antes habría
     abierto la CSI cruda (imagen verde). `cv2.CAP_V4L2` va explícito porque, con un texto en
     vez de un número, OpenCV podría tratarlo como archivo de video o pipeline de GStreamer.
     Si se cambia de webcam, el nombre nuevo sale de `ls -l /dev/v4l/by-id/`.

**Todavía sin probar.** Orden sugerido: primero cada uno solo (señas con su webcam escribiendo en
el LCD; cara con la CSI moviendo la matriz) y después los dos juntos, una terminal para cada uno.
Con los dos juntos, mirar la velocidad: si alguno reacciona notablemente más lento que solo,
bajar la resolución de la CSI en el pipeline. `jetson_face.py` abre ventana (`cv2.imshow`), así
que hay que estar sentado en la Jetson con el monitor, no por SSH.

## Trampas de la jornada del 29/10

| Síntoma | Causa | Solución |
|---|---|---|
| La Pico repite `Conectando a wifi... status: -2` | `-2` = `STAT_NO_AP_FOUND`: no encuentra la red. El hotspot de la Jetson no estaba levantado (al reiniciar, la Jetson vuelve a la WiFi del laboratorio) | En la Jetson: `nmcli device status` (si la WiFi dice `unavailable`, `sudo nmcli radio wifi on`) y `sudo nmcli connection up Hotspot`. La Pico reintenta sola, no hace falta reiniciarla |
| `No module named 'joblib'` | El venv no estaba activado (el prompt no mostraba `(espejo_facial_venv)`) | Activarlo, ver la fila siguiente |
| `source ~/espejo_facial_venv/bin/activate` → `No such file or directory` | El venv se mudó el 09/09 a `~/proyecto_gestos/` ([integracion.md](../../espejo_facial_led/integracion.md) sección 12) | `source ~/proyecto_gestos/espejo_facial_venv/bin/activate` |
| `Can't initialize GTK backend` al correr `reconocer_letra.py` | Por SSH no hay ventana donde abrir `cv2.imshow` (trampa ya conocida del 16/09) | Por SSH, usar `reconocer_letra_stream.py` con el túnel |
| `InconsistentVersionWarning: ... from version 1.9.1 when using version 1.7.2` | El `abecedario_modelo.pkl` actual (del 17/09) se guardó con scikit-learn 1.9.1, no con el venv de entrenamiento (1.7.2) | **Pendiente:** reentrenar con `entrenamiento_venv` activado y volver a copiarlo (ver "Compatibilidad de versiones" en el [README principal](../README.md)) |

## Próximos pasos

1. Probar los dos proyectos a la vez (ver arriba), y medir si la velocidad alcanza.
2. Reentrenar el `.pkl` con scikit-learn 1.7.2 para sacar el `InconsistentVersionWarning`.
