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
| [`abecedario_de_senas/`](abecedario_de_senas/) | Traductor de abecedario dactilológico (ASL) a letras, escribiendo el texto en un LCD 16x2 conectado a la misma Pico W del espejo facial (la matriz LED quedó para el espejo, y los dos proyectos corren a la vez). La Jetson ve la mano con MediaPipe Hands y clasifica la letra; mismo canal UDP hacia la Pico W. | Lisandro Elmelaj | Funcionando de punta a punta desde el 16/09 (con LCD desde el 29/10); pendientes: reentrenar el `.pkl` con scikit-learn 1.7.2, probar J y Z con el gesto real y afinar las letras flojas (M, N, U, V, R) |

## Puesta en marcha paso a paso: espejo facial y abecedario de señas

Los dos proyectos comparten el hardware (una Jetson, una Pico W y una red WiFi propia), así que
la puesta en marcha es una sola. La matriz LED es del espejo facial y el LCD del abecedario de
señas, y se pueden correr por separado o los dos a la vez. Este es el orden para una sesión
normal, con todo ya instalado. El porqué de cada paso está en los documentos que se linkean.

### 0. Lo que tiene que estar listo de antes (una sola vez)

- **Cableado de la Pico:** matriz MAX7219 ([`espejo_facial_led/README.md`](espejo_facial_led/README.md)
  sección 7) y LCD ([`abecedario_de_senas/extension_lcd/README.md`](abecedario_de_senas/extension_lcd/README.md),
  "Cableado"). El VCC de los dos sale del pin 40 (VBUS), repartido con la protoboard.
- **Cámaras en la Jetson:** la CSI (cable plano) para el espejo facial y la webcam USB para las
  señas. Con una sola de las dos alcanza para correr su proyecto.
- **Archivos en la Pico** (guardados con Thonny): `main.py` y `max7219.py` de
  [`espejo_facial_led/pico/`](espejo_facial_led/pico/), `lcd_i2c.py` de
  [`abecedario_de_senas/extension_lcd/`](abecedario_de_senas/extension_lcd/) (opcional, solo
  para el LCD) y `wifi_config.py` (copia de `wifi_config.example.py` con la red del hotspot; no se
  commitea).
- **Hotspot creado en la Jetson**, con la banda forzada a 2.4 GHz: ver
  [`espejo_facial_led/integracion.md`](espejo_facial_led/integracion.md) sección 11. Queda
  guardado en el perfil `Hotspot`; en cada sesión solo hay que levantarlo (paso 2).
- **Venv de la Jetson** en `~/proyecto_gestos/espejo_facial_venv`, con mediapipe, OpenCV del
  sistema, `scikit-learn==1.7.2` y joblib.

### 1. Entrar a la Jetson por SSH (por Ethernet)

Desde la PC:

```bash
ssh indea@<ip-jetson>
```

Usá la IP del **cable Ethernet** de la Jetson, no la de su WiFi. En el paso 2 la WiFi pasa a ser
el hotspot y deja la red del laboratorio, así que una sesión que entrara por la WiFi se cortaría.

### 2. Levantar el hotspot

En la Jetson:

```bash
nmcli device status
```

Si la fila `wlP1p1s0` dice `unavailable`, la radio WiFi está apagada:

```bash
sudo nmcli radio wifi on
```

Después:

```bash
sudo nmcli connection up Hotspot
iw dev wlP1p1s0 info
```

En la salida de `iw`, el `channel` tiene que mostrar una frecuencia que empiece con **24xx MHz**
(2.4 GHz). Si empieza con 5, la Pico no va a ver la red: ver integracion.md sección 11.

### 3. Arrancar la Pico

1. Conectar la Pico por USB a la PC y abrir Thonny.
2. Abrir `main.py` (el de la Pico) y darle **Run**.
3. En la consola tienen que aparecer, en este orden:
   - `LCD encontrado en 0x27` (o un aviso de que sigue sin LCD, si no está conectado);
   - `IP: 10.42.0.xxx`: **anotá esa IP**;
   - `Escuchando UDP en el puerto 5005`.

Si se queda repitiendo `Conectando a wifi... status: -2`, la Pico no encuentra la red: volver al
paso 2. La Pico reintenta sola, no hace falta reiniciarla.

### 4. Copiar el código a la Jetson (solo si cambió algo)

Desde la PC, en la raíz del repo:

```bash
scp proyectos/espejo_facial_led/jetson/jetson_face.py proyectos/espejo_facial_led/jetson/gestos.py indea@<ip-jetson>:~/proyecto_gestos/
scp proyectos/abecedario_de_senas/jetson/reconocer_letra.py proyectos/abecedario_de_senas/jetson/reconocer_letra_stream.py proyectos/abecedario_de_senas/jetson/manos.py proyectos/abecedario_de_senas/jetson/letras_matriz.py proyectos/abecedario_de_senas/abecedario_modelo.pkl indea@<ip-jetson>:~/proyecto_senas/
```

Después de cada `scp`, confirmar en la Jetson que llegó la versión nueva, buscando algo del
cambio con `grep -n`. Un `scp` olvidado ya hizo perder tiempo una vez (ver
[`abecedario_de_senas/README.md`](abecedario_de_senas/README.md), "Trampas de infraestructura").

### 5. Revisar la IP de la Pico

En la Jetson, confirmar que `IP_PICO` coincide con la IP del paso 3:

```bash
grep -n "IP_PICO =" ~/proyecto_gestos/jetson_face.py ~/proyecto_senas/reconocer_letra*.py
```

Si no coincide, cambiarla en esos archivos. La asigna el DHCP del hotspot y puede cambiar entre
sesiones.

### 6. Activar el venv

En cada terminal de la Jetson donde se vaya a correr un proyecto:

```bash
source ~/proyecto_gestos/espejo_facial_venv/bin/activate
```

El prompt tiene que empezar con `(espejo_facial_venv)`. Ojo, la ruta vieja `~/espejo_facial_venv`
ya no existe.

### 7a. Correr el espejo facial (cámara CSI → matriz)

**Sentado en la Jetson, con monitor y teclado:** abre una ventana, y por SSH falla con
`Can't initialize GTK backend`.

```bash
cd ~/proyecto_gestos
python3 jetson_face.py
```

Durante los primeros 3 segundos, quedarse con **cara neutra** mirando a la cámara (calibración).
Después la matriz copia los gestos. Se corta con `q` en la ventana o `Ctrl+C`.

Si la cámara CSI no abre:

```bash
sudo systemctl restart nvargus-daemon
```

### 7b. Correr el abecedario de señas (webcam USB → LCD)

**Sentado en la Jetson** (con ventana):

```bash
cd ~/proyecto_senas
python3 reconocer_letra.py
```

**Por SSH** (sin ventana, el video se ve en el navegador de la PC):

```bash
cd ~/proyecto_senas
python3 reconocer_letra_stream.py
```

y en **otra terminal de la PC** se abre el túnel:

```bash
ssh -L 8000:localhost:8000 indea@<ip-jetson>
```

y en el navegador de la PC, `http://localhost:8000/`. El texto aparece en el LCD: línea 1 lo
escrito, línea 2 la letra actual. Se corta con `q` (versión con ventana) o `Ctrl+C`.

### 8. Los dos a la vez

Una terminal para cada uno, cada una con el venv activado (paso 6): `jetson_face.py` en una y
`reconocer_letra.py` (o `_stream`) en la otra. Cada uno usa su cámara (CSI para la cara, webcam
para las señas) y la Pico atiende los dos: matriz para la cara, LCD para las señas. Probado el
30/10, los dos fluidos.

### Si algo no anda

| Síntoma | Qué revisar |
|---|---|
| La Pico repite `status: -2` | Hotspot caído: paso 2 |
| `No module named ...` | Venv sin activar: paso 6 |
| `Can't initialize GTK backend` | Se corrió por SSH una versión con ventana: usar `reconocer_letra_stream.py`, o correrlo sentado en la Jetson |
| `No se pudo abrir la webcam` / `la camara CSI` | Otro proceso la tiene tomada: `ps aux \| grep -E "jetson_face\|reconocer_letra" \| grep -v grep` y cerrarlo con `pkill -f <nombre>`. Si es la CSI, además `sudo systemctl restart nvargus-daemon` |
| La matriz o el LCD no reaccionan | `IP_PICO` distinta de la IP de la Pico (paso 5), o un `scp` sin repetir (paso 4) |
| La Pico tira `[CYW43] HT not ready` / `EPERM` | Desenchufar el USB de la Pico unos segundos y volver a enchufar (`Ctrl+D` no alcanza) |

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
