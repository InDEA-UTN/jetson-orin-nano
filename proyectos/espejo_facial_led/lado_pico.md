# Lado Pico W — WiFi y LED

Primeros pasos del lado "cara" del proyecto: confirmar que la Pico W ya tiene MicroPython,
prender un LED, y validar el camino completo por WiFi entre la Jetson y la Pico usando el LED de
a bordo como reemplazo provisorio de la matriz MAX7219 (todavía no llegó). El lado Jetson
(MediaPipe, sprites) está documentado en [`lado_jetson.md`](lado_jetson.md).

> **Estado.** Verificado el **2026-08-25**: Fase 1 simplificada (LED en vez de matriz) y Fase 2
> completas — la Pico se conecta por WiFi, abre un socket UDP y prende/apaga el LED al recibir un
> paquete desde la Jetson. Falta la matriz MAX7219 en sí (Fase 1-2 "de verdad") y definir IP fija.

**Herramienta usada:** [Thonny](https://thonny.org/), con la Pico W ya conectada por USB y
detectada como intérprete **"MicroPython (Raspberry Pi Pico)"**.

---

## 1. Confirmar que la Pico ya tenía MicroPython

La Pico W del laboratorio ya venía con firmware cargado — no hizo falta flashear nada. Conectada
por USB (sin tocar el botón **BOOTSEL**: eso solo hace falta para *grabar* un firmware nuevo, no
para uso normal), el Shell de Thonny mostró directo:

```
MicroPython v1.28.0 on 2026-04-06; Raspberry Pi Pico W with RP2040
Type "help()" for more information.
>>>
```

---

## 2. Fase 1 simplificada — prender el LED de a bordo

Sin matriz LED todavía, se usó el LED integrado de la placa como primera prueba:

```python
from machine import Pin
import time

try:
    led = Pin("LED", Pin.OUT)   # Pico W: el LED está en el chip WiFi (CYW43), no en un GPIO común
except TypeError:
    led = Pin(25, Pin.OUT)      # Pico normal (sin W): GPIO25 directo

while True:
    led.toggle()
    time.sleep(0.5)
```

**Trampa real: pegar un `while True` en el Shell interactivo lo bloquea.** Corrido línea por línea
en el `>>>`, el LED tostaba bien, pero el Shell quedaba congelado en el loop infinito y no
aceptaba más comandos. Se resuelve con **Ctrl+C** para cortar, y de ahí en adelante todo el código
se escribió en el **editor** de Thonny (pestaña de arriba) y se corrió con **F5** — así se puede
iterar sin perder el Shell.

---

## 3. Trampa real: Thonny se desconectó y pareció un problema de firmware

Al desconectar la Pico un momento, `%Run` (F5) siguió "andando" pero tirando:

```
ModuleNotFoundError: No module named 'network'
```

Esto llevó a sospechar, en un primer momento, que el firmware instalado no era el build específico
de la **W** (el único que trae el driver WiFi CYW43 y el módulo `network`). El diagnóstico real fue
con:

```python
help('modules')
```

La lista que salió (`numpy`, `matplotlib`, `PyQt5`, `gnuradio`, `apt`, `dbus`, ...) es del **Python
de escritorio de la PC**, no de MicroPython — confirmó que Thonny, al perder la Pico, había caído
sola al intérprete local de la computadora sin avisarlo con claridad (el indicador está abajo a la
derecha, mostraba `<no backend>`). No era un problema de firmware.

**Solución:** reconectar la Pico por USB (sin BOOTSEL — normal, no modo bootloader) y volver a
elegir manualmente el intérprete **"MicroPython (Raspberry Pi Pico)"** con el puerto correcto en
`Ejecutar → Configurar intérprete`. Para confirmar el puerto desde la terminal de la PC, si hace
falta:

```bash
lsusb | grep -i "2e8a"      # 2e8a = vendor ID de Raspberry Pi
ls /dev/ttyACM*
```

En esta sesión, el dispositivo apareció como `Bus 003 Device 017: ID 2e8a:0005 MicroPython Board
in FS mode` y el puerto fue `/dev/ttyACM0`.

---

## 4. Fase 2 — Conectar la Pico por WiFi

### Trampa real: eduroam no es una opción para la Pico W

El laboratorio usa **eduroam**, que es WPA2-**Enterprise** (802.1X, con EAP — en este caso
Tunneled TLS + MSCHAPv2, usuario y contraseña institucionales en vez de una clave compartida). El
driver WiFi de MicroPython para el chip CYW43439 de la Pico W solo implementa **WPA/WPA2-Personal**
(PSK): no hace la negociación EAP que pide eduroam. No es una limitación de configuración, es que
el módulo `network` de MicroPython no tiene ese protocolo implementado. Se descartó eduroam de
entrada para este dispositivo.

Se evaluó como alternativa usar el hotspot del celular (WPA2-Personal estándar, sin este
problema), pero terminó sin hacer falta: apareció una red abierta del laboratorio.

### Trampa real: parecía que no conectaba a la red del laboratorio (`lab-raspi`)

Con la red **`lab-raspi`** (un router viejo del laboratorio) el primer intento se quedó
imprimiendo puntos sin parar, sin timeout. Antes de reintentar a ciegas, se armó un script de
diagnóstico que escanea las redes visibles y reporta el tipo de seguridad de cada una, y que
además reemplaza el loop infinito por uno con **timeout** y reporte del código de estado real:

```python
import network
import time

ssid = "lab-raspi"
password = "raspi-indea"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

for red in wlan.scan():
    print(red[0].decode(), "canal", red[2], "seguridad", red[4])

wlan.connect(ssid, password)

t0 = time.time()
while not wlan.isconnected() and time.time() - t0 < 15:
    print("status:", wlan.status())
    time.sleep(1)

if wlan.isconnected():
    print("Conectado. IP:", wlan.ifconfig()[0])
else:
    print("No conectó. Status final:", wlan.status())
```

La sospecha inicial era un bug conocido del CYW43 con routers viejos configurados en modo
WPA/WPA2 **mixto con TKIP** (que se queda "conectando" para siempre sin fallar nunca). El `scan()`
mostró `lab-raspi` con seguridad tipo `5`, junto con `eduroam` y otras redes cifradas también en
`5`/`7`, y las abiertas (`Red-UTN`, `BugNET`, `GittoNet`) en `0`. En la corrida con timeout,
conectó igual en unos segundos (`status: 1` dos veces, `status: 2` tres veces, y listo) — **fue
una falsa alarma**, probablemente solo necesitaba un poco más de tiempo que la primera vez, no un
problema real de compatibilidad.

**Resultado real:** la Pico quedó en la red `192.168.1.0/24` (router viejo, sin reserva DHCP —
la IP cambió entre reconexiones: `192.168.1.101` en la primera prueba, `192.168.1.103` en la
siguiente). Pendiente fijar una IP reservada si esto sigue pasando cuando se integre con la
Jetson de forma permanente.

---

## 5. Servidor UDP en la Pico + LED

Con WiFi conectado, la Pico abre un socket UDP y prende/apaga el LED cada vez que le llega
cualquier paquete — el mismo mecanismo que después va a recibir los 8 bytes del sprite de la
matriz (protocolo ya definido en el `README.md` del proyecto, sección 9), solo que acá el
"dibujo" es un simple toggle:

```python
import network
import socket
import time
from machine import Pin

ssid = "lab-raspi"
password = "raspi-indea"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
while not wlan.isconnected():
    time.sleep(0.5)
print("IP:", wlan.ifconfig()[0])

try:
    led = Pin("LED", Pin.OUT)
except TypeError:
    led = Pin(25, Pin.OUT)

PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PORT))
print("Escuchando UDP en el puerto", PORT)

while True:
    data, addr = sock.recvfrom(64)
    print("Paquete de", addr, ":", data)
    led.toggle()
```

---

## 6. Lado Jetson: sumarla a la misma red WiFi

La Jetson necesita estar en la **misma red** que la Pico para poder mandarle los paquetes UDP. Se
usó el módulo WiFi de fábrica del Developer Kit (M.2 Key E, ya documentado en
`02_que_hace_falta.md` de `guia_de_iniciacion/`):

```bash
sudo nmcli device wifi connect "lab-raspi" password "raspi-indea"
hostname -I
```

### Trampa real: el SSH desde la laptop a la Jetson dejó de andar

Al mover la Jetson de Ethernet (red de la facultad) a WiFi (`lab-raspi`), el `ssh indea@<ip>` desde
la laptop dejó de conectar. La causa no fue la Jetson ni el SSH: **la laptop se había quedado en
otra red** (la de la facultad), mientras que la IP nueva de la Jetson (`192.168.1.x`) solo existe
dentro de `lab-raspi` — sin las dos máquinas en la misma red, no hay ruta posible, con o sin SSH de
por medio. Se resolvió conectando también la laptop a `lab-raspi`. Diagnóstico usado para
confirmarlo antes de tocar nada de SSH: `ping` simple primero, que aísla si el problema es de red
o del servicio:

```bash
ping -c 3 <ip_de_la_jetson>
```

---

## 7. Prueba de punta a punta

Con la Jetson y la Pico en la misma red y el servidor UDP corriendo en la Pico, desde una sesión
SSH en la Jetson:

```bash
echo "on" | nc -u -w1 192.168.1.103 5005
```

**Resultado real:** el LED de la Pico cambió de estado en cada ejecución, y el Shell de Thonny
imprimió `Paquete de (...) : b'on\n'` cada vez — confirma el camino completo **Jetson → WiFi →
Pico → LED** funcionando de punta a punta.

**Dato para más adelante:** el `ping` entre la Jetson y la Pico dio latencias altas y variables
(98–342 ms), esperable en un router viejo con señal floja. No afecta esta prueba puntual, pero
puede notarse cuando se mande el sprite completo a ~30 veces por segundo — si pasa, acercar los
dispositivos al router o pasar al hotspot del celular son los caminos más simples.

---

## 8. Complicaciones y cómo se resolvieron

| Problema | Causa | Solución |
|---|---|---|
| El `while True` del blink congela el Shell de Thonny | Se pegó código con loop infinito directo en el `>>>` interactivo | Cortar con `Ctrl+C`; escribir el código en el editor y correr con F5 |
| `ModuleNotFoundError: No module named 'network'` | Al desconectarse la Pico, Thonny cayó al intérprete local de la PC (Python de escritorio) sin avisarlo con claridad | Reconectar la Pico por USB (sin BOOTSEL) y reseleccionar el intérprete "MicroPython (Raspberry Pi Pico)" con el puerto correcto |
| No se podía conectar a `eduroam` desde la Pico | Eduroam es WPA2-Enterprise (802.1X/EAP); el driver CYW43 de MicroPython solo soporta WPA/WPA2-Personal (PSK) | Usar otra red: se descartó eduroam para este dispositivo, se conectó a `lab-raspi` (WPA2-Personal) |
| Primer intento a `lab-raspi` parecía quedarse "conectando" para siempre | Sospecha de bug conocido de CYW43 con routers en modo WPA/WPA2 mixto+TKIP — no confirmado, resultó falsa alarma | Reintentar con un script con timeout y `wlan.status()`; conectó en unos segundos |
| SSH de la laptop a la Jetson dejó de andar al pasar la Jetson a WiFi | La laptop había quedado en otra red (la de la facultad), sin ruta a la IP nueva de la Jetson en `lab-raspi` | Conectar también la laptop a `lab-raspi`; diagnosticado primero con `ping` simple, antes de sospechar del SSH |
| La IP de la Pico cambió entre una prueba y la siguiente (`.101` → `.103`) | El router viejo no tiene reserva DHCP para la MAC de la Pico | Confirmar la IP con `wlan.ifconfig()[0]` en cada sesión; pendiente fijar una IP reservada |

---

## 9. Próximos pasos

1. Cuando llegue la matriz MAX7219: reemplazar `led.toggle()` por escribir el framebuffer de 8
   bytes vía SPI, sobre el mismo socket UDP ya funcionando (protocolo definido en el `README.md`
   del proyecto, sección 9).
2. Fijar una IP reservada para la Pico en el router (o pasar a un router/AP que la sostenga), para
   no tener que reconfirmar la IP en cada sesión.
3. Guardar el script final de la Pico como `main.py` en la placa, para que arranque solo sin
   depender de Thonny conectado.
4. Si la latencia del router viejo se vuelve un problema con el streaming real del sprite, migrar
   a otra red (hotspot del celular u otro router) antes de invertir tiempo optimizando el
   protocolo.
