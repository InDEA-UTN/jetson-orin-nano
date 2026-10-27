# Extensión LCD — texto de señas en una pantalla 16x2

**Estado.** Al 23/10/2026: **el LCD funciona contra la Pico real, de forma aislada** — cableado
verificado con `i2c.scan()` (responde en `0x27`) y `demo_lcd.py` escribiendo dos líneas de texto.
**Todavía no está conectado al reconocedor**: falta que la Pico acepte el paquete de texto por UDP
y que la Jetson lo mande (ver "Próximos pasos"). Hasta entonces, el proyecto de señas sigue
andando exactamente igual que antes, solo con la matriz.

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

## Cómo se va a conectar al reconocedor (diseño acordado, falta implementar)

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

Matriz y LCD funcionan a la vez: la Jetson manda los dos paquetes seguidos en cada frame y la
Pico atiende cada uno según su tipo.

## Próximos pasos

1. **`main.py` de la Pico** (hoy en
   [`../../espejo_facial_led/pico/main.py`](../../espejo_facial_led/pico/main.py)): aceptar el
   paquete de 33 bytes y escribirlo con `lcd_i2c`; arrancar igual si el LCD no está conectado
   (que el espejo facial siga andando sin él).
2. **`reconocer_letra.py` y `reconocer_letra_stream.py`**: agregar `enviar_a_lcd()` que arme las
   dos líneas y mande el paquete en cada frame (duplicado en los dos, mismo criterio que
   `enviar_a_matriz()`). Por ahora siguen mandando también a la matriz.
3. Probar de punta a punta: mano → texto en el LCD.

### Más adelante: los dos proyectos a la vez (para la presentación)

Idea acordada, postergada a propósito para terminar primero el LCD: con **2 cámaras**, correr el
espejo facial y el de señas al mismo tiempo en la Jetson, cada uno con su cámara, contra la misma
Pico — **la matriz para los gestos de cara y el LCD para las señas**. Implica:

- Que el script de señas **deje de mandar a la matriz** (si no, los dos programas se pelean por
  ella y titila).
- Que cada script abra su propia cámara — mejor por nombre fijo (`/dev/v4l/by-id/...`) que por
  número, porque `/dev/video0`/`video1` pueden intercambiarse al reiniciar.
- Chequear que dos webcams en el mismo puerto USB no se queden sin ancho de banda, y que la
  Jetson mantenga buenos fps con los dos modelos corriendo.
