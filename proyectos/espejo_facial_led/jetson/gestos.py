# Espejo Facial LED - lado Jetson - logica de gestos compartida
#
# Todo lo que va desde "landmarks de MediaPipe" hasta "sprite de 8x8": metricas (EAR, MAR,
# altura de cejas, curvatura de boca), calibracion por persona, cuantizacion a estados
# discretos, suavizado y composicion del sprite.
#
# Lo usan jetson_face.py (que manda a la matriz) y ver_camara_en_vivo.py (el visor de
# diagnostico), para que los dos muestren/manden exactamente los mismos estados.
# Ver ../lado_jetson.md.
#
# CALIBRACION: los primeros SEGUNDOS_CALIBRACION segundos con cara detectada se promedian con
# la persona en CARA NEUTRA, y ese promedio queda como linea de base fija de la sesion. Los
# umbrales se calculan una sola vez a partir de esa base y ya no se mueven mas.
#
# Esto es a proposito: es calibracion inicial, NO una linea de base movil. Si la base siguiera
# actualizandose durante la sesion, el sistema "se acostumbraria" a un gesto sostenido (cejas
# levantadas 10 segundos) y dejaria de detectarlo. Asi, en cambio, la misma pose da siempre el
# mismo estado durante toda la sesion, pero adaptado a la cara de quien esta adelante.
#
# Las metricas ya vienen normalizadas por el tamano de la cara (ver escala()), asi que la
# calibracion no corrige la distancia a la camara: corrige la ANATOMIA (cejas naturalmente
# altas o bajas, ojos mas o menos rasgados, boca con las comisuras un poco caidas en reposo).

import math
import time
from collections import deque

# --- Calibracion inicial ---
SEGUNDOS_CALIBRACION = 3.0   # cuanto se promedia la cara neutra al arrancar
MIN_MUESTRAS_CALIBRACION = 15  # si la cara se detecto en menos frames que esto, se sigue calibrando

# --- Cuanto hay que apartarse de la propia cara neutra para que dispare cada gesto. Estos son
# los numeros a tocar si algun gesto cuesta que salga. Los valores por defecto reproducen los
# umbrales absolutos que se venian usando, para una cara neutra tipica. ---
FRACCION_OJO_CERRADO  = 0.65    # ojo cerrado si el EAR baja a menos de este % de su EAR neutro
DELTA_MAR_ABIERTA     = 0.25    # boca abierta si el MAR sube esto por encima del neutro
DELTA_CEJA_LEVANTADA  = 0.06    # cejas levantadas si suben esto sobre su altura neutra
DELTA_CEJA_FRUNCIDA   = 0.06    # cejas fruncidas si bajan esto de su altura neutra
DELTA_CURVA_SONRISA   = 0.025   # sonrisa si la curvatura sube esto sobre la neutra
DELTA_CURVA_TRISTE    = 0.025   # triste si la curvatura baja esto de la neutra
DELTA_GAZE_X          = 0.15    # mirada izq/der si gaze_x se aparta esto del neutro

# Se probo tambien mirada arriba/abajo (gaze_y) y se saco: en hardware real, mirar arriba o
# abajo mueve el parpado y la ceja lo suficiente como para disparar guinos y cejas levantadas
# falsos -- es un confundido anatomico, no un umbral mal calibrado, asi que no tiene arreglo
# ajustando un DELTA. Izquierda/derecha si funciona bien porque mover los ojos a los costados
# no cambia la apertura del parpado.

VENTANA_SUAVIZADO = 5    # media movil corta: saca el temblor del detector

METRICAS = ("ear_izq", "ear_der", "cejas", "mar", "curva", "gaze_x")

# Los dos grupos de landmarks del iris que trae el modelo (478 en total en vez de 468).
# MediaPipe no dice por su cuenta cual es "izquierdo"/"derecho" de este proyecto -- eso se
# verifica en _iris_izq_der() contra las esquinas de ojo que ya usa el resto del archivo.
# Confirmado con test_iris.py: mirando de lado, los dos ojos se mueven en direcciones
# opuestas de su propia escala, la firma de una mirada conjugada real (no de la cabeza).
IRIS_A = 468
IRIS_B = 473


# ---------------------------------------------------------------- metricas

def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def escala(lm):
    """Distancia entre las esquinas externas de los ojos. Referencia estable para normalizar
    las medidas verticales, asi no dependen de la distancia a la camara."""
    return dist(lm[33], lm[263])

def ear(lm, arriba, abajo, izq, der):
    return dist(lm[arriba], lm[abajo]) / dist(lm[izq], lm[der])

def ear_izquierdo(lm):
    return ear(lm, 159, 145, 33, 133)

def ear_derecho(lm):
    return ear(lm, 386, 374, 362, 263)

def mar(lm):
    return dist(lm[13], lm[14]) / dist(lm[61], lm[291])

def altura_cejas(lm):
    """Cuanto se levanta cada ceja por encima del parpado, normalizado. Landmarks segun la
    tabla del README (seccion 8): ceja izq 105, ceja der 334; parpados 159 y 386."""
    e = escala(lm)
    izq = (lm[159].y - lm[105].y) / e
    der = (lm[386].y - lm[334].y) / e
    return (izq + der) / 2

def curvatura_boca(lm):
    """Positivo = comisuras (61, 291) mas arriba que el centro de los labios (13, 14) =
    sonrisa. Negativo = comisuras caidas = triste. Es el dato que el MAR solo no da."""
    y_centro = (lm[13].y + lm[14].y) / 2
    y_comisuras = (lm[61].y + lm[291].y) / 2
    return (y_centro - y_comisuras) / escala(lm)

def _iris_izq_der(lm):
    """Cual de los dos grupos de iris (IRIS_A o IRIS_B) es el ojo izquierdo de este proyecto
    (esquinas 33/133) y cual el derecho (362/263): el que cae dentro del rango x de cada ojo."""
    x_izq = sorted((lm[33].x, lm[133].x))
    if x_izq[0] <= lm[IRIS_A].x <= x_izq[1]:
        return IRIS_A, IRIS_B
    return IRIS_B, IRIS_A

def gaze_x(lm):
    """0 = mirando a la izquierda de la imagen, 1 = a la derecha, ~0.5 = al centro (antes de
    calibrar contra la cara neutra de cada uno). Combina los dos ojos porque se mueven juntos
    (mirada conjugada) y promediarlos cancela ruido del detector.

    Cada ojo por separado da 0 en su esquina externa y 1 en la interna (hacia la nariz) -- pero
    "hacia la nariz" es la DERECHA de la imagen para el ojo izquierdo y la IZQUIERDA para el
    derecho, asi que hay que invertir uno de los dos antes de promediar."""
    iris_izq, iris_der = _iris_izq_der(lm)
    g_izq = (lm[iris_izq].x - lm[33].x)  / (lm[133].x - lm[33].x)   # 0 afuera, 1 hacia la nariz
    g_der = (lm[iris_der].x - lm[263].x) / (lm[362].x - lm[263].x)  # 0 afuera, 1 hacia la nariz
    return (g_izq + (1 - g_der)) / 2

def medir(lm):
    """Las metricas crudas de un frame."""
    return {
        "ear_izq": ear_izquierdo(lm),
        "ear_der": ear_derecho(lm),
        "cejas":   altura_cejas(lm),
        "mar":     mar(lm),
        "curva":   curvatura_boca(lm),
        "gaze_x":  gaze_x(lm),
    }


# ------------------------------------------------------------- calibracion

def umbrales_desde_base(base):
    """Convierte las medidas de la cara neutra de esta persona en los umbrales absolutos que
    se usan durante el resto de la sesion.

    Los ojos van por fraccion (un ojo rasgado tiene un EAR neutro mas bajo, y su umbral de
    cerrado tiene que bajar en la misma proporcion) y se calibra cada ojo por separado, porque
    casi ninguna cara es simetrica. El resto va por diferencia: lo que importa no es el valor
    absoluto sino cuanto te apartaste de tu propia cara neutra.
    """
    return {
        "ear_izq_cerrado": base["ear_izq"] * FRACCION_OJO_CERRADO,
        "ear_der_cerrado": base["ear_der"] * FRACCION_OJO_CERRADO,
        "mar_abierta":     base["mar"]   + DELTA_MAR_ABIERTA,
        "ceja_levantada":  base["cejas"] + DELTA_CEJA_LEVANTADA,
        "ceja_fruncida":   base["cejas"] - DELTA_CEJA_FRUNCIDA,
        "curva_sonrisa":   base["curva"] + DELTA_CURVA_SONRISA,
        "curva_triste":    base["curva"] - DELTA_CURVA_TRISTE,
        "gaze_izq":        base["gaze_x"] - DELTA_GAZE_X,
        "gaze_der":        base["gaze_x"] + DELTA_GAZE_X,
    }


# ------------------------------------------------- cuantizacion a estados

def estado_ojo(valor, umbral):
    return "cerrado" if valor < umbral else "abierto"

def estado_cejas(valor, u):
    if valor >= u["ceja_levantada"]:
        return "levantadas"
    if valor <= u["ceja_fruncida"]:
        return "fruncidas"
    return "normal"

def estado_boca(mar_val, curva, u):
    if mar_val > u["mar_abierta"]:
        return "abierta"
    if curva >= u["curva_sonrisa"]:
        return "sonrisa"
    if curva <= u["curva_triste"]:
        return "triste"
    return "neutra"

def estado_mirada(gaze_x_val, u):
    """Solo tiene sentido con los dos ojos abiertos -- sin iris visible no hay de donde sacar
    esto (el llamador se encarga de no invocarla si no). Solo el eje horizontal: ver el
    comentario junto a DELTA_GAZE_X sobre por que se saco el vertical."""
    if gaze_x_val > u["gaze_der"]:
        return "derecha"
    if gaze_x_val < u["gaze_izq"]:
        return "izquierda"
    return "centro"


# --------------------------------------------------- composicion del sprite
#
# Reparto de las 8 filas con los dos ojos abiertos:
#   0    cejas levantadas
#   1    cejas normales / fruncidas
#   2    (separador: sin esta fila, unas cejas normales y unos ojos cerrados quedan pegados
#         y se leen como una sola ceja gruesa)
#   3    ojos
#   4    (separador)
#   5-7  boca
#
# Cuando un ojo se cierra, el ojo pasa a ocupar las filas 1-2-3 dibujando un guino ">"/"<":
# dos puntos exteriores (arriba y abajo) mas uno interior al medio. Usa la fila 1 -- normalmente
# de cejas -- porque la mitad de la ceja de ESE lado se apaga cuando el ojo cierra (no se dibuja
# ninguna fila de ceja ahi), asi que queda libre: se ve como si la ceja bajara junto con el
# parpado, en vez de quedar flotando arriba. Importante: el guino NO puede bajar a la fila 4 en
# vez de subir a la 1, porque la fila 4 es el separador contra la boca -- pegado ahi, la punta
# de abajo del guino se funde con las comisuras de la sonrisa (mismas columnas 1 y 6).

def construir_sprite(ojo_izq, ojo_der, cejas, boca, mirada="centro"):
    """Compone la matriz de 8x8 combinando el estado de cada rasgo por separado, en vez de
    elegir entre caritas completas predefinidas."""
    grid = [['0'] * 8 for _ in range(8)]

    # La mirada se ignora en cuanto CUALQUIER ojo cierra: no tiene sentido mostrar hacia donde
    # miraba un ojo que ya no se ve, y evita que el punto salte de lugar justo al guinar.
    if ojo_izq == "cerrado" or ojo_der == "cerrado":
        mirada = "centro"

    # Cejas: arriba = levantadas, abajo = normales, abajo y juntas hacia el centro = fruncidas.
    # Las columnas de cada mitad coinciden con las columnas del ojo de ese mismo lado, para que
    # apagar una mitad cuando ese ojo se cierra se lea como que la ceja "se fue" con el ojo.
    if cejas == "levantadas":
        fila_cejas, cols_izq, cols_der = 0, (1, 2), (5, 6)
    elif cejas == "fruncidas":
        fila_cejas, cols_izq, cols_der = 1, (2, 3), (4, 5)
    else:
        fila_cejas, cols_izq, cols_der = 1, (1, 2), (5, 6)

    if ojo_izq == "abierto":
        for c in cols_izq:
            grid[fila_cejas][c] = '1'
    if ojo_der == "abierto":
        for c in cols_der:
            grid[fila_cejas][c] = '1'

    # Ojos: abierto = un punto; cerrado = guino ">" o "<" en tres filas (ver el comentario de
    # arriba). El punto interior del guino queda en la misma columna que el ojo abierto, asi
    # que abrir y cerrar el ojo se lee como el mismo punto que se "duplica" hacia afuera.
    #
    # Con el ojo abierto, el punto se corre 1 columna segun la mirada -- misma direccion para
    # los dos ojos, porque en la imagen los dos se mueven juntos hacia el mismo lado.
    col_desvio = 0
    if mirada == "derecha":
        col_desvio = 1
    elif mirada == "izquierda":
        col_desvio = -1

    if ojo_izq == "abierto":
        grid[3][2 + col_desvio] = '1'
    else:
        grid[1][1] = grid[2][2] = grid[3][1] = '1'

    if ojo_der == "abierto":
        grid[3][5 + col_desvio] = '1'
    else:
        grid[1][6] = grid[2][5] = grid[3][6] = '1'

    # Boca
    if boca == "abierta":                       # ovalo
        for c in (2, 3, 4, 5): grid[5][c] = '1'
        for c in (1, 2, 5, 6): grid[6][c] = '1'
        for c in (2, 3, 4, 5): grid[7][c] = '1'
    elif boca == "sonrisa":                     # comisuras arriba, centro abajo
        for c in (1, 6): grid[5][c] = '1'
        for c in (2, 3, 4, 5): grid[6][c] = '1'
    elif boca == "triste":                      # centro arriba, comisuras abajo
        for c in (2, 3, 4, 5): grid[5][c] = '1'
        for c in (1, 6): grid[6][c] = '1'
    else:                                       # neutra: linea recta
        for c in (2, 3, 4, 5): grid[6][c] = '1'

    return [''.join(fila) for fila in grid]


def sprite_a_bytes(sprite):
    """8 filas de texto '0'/'1' -> los 8 bytes del protocolo (bit 7 = pixel izquierdo)."""
    return bytes(int(fila, 2) for fila in sprite)


# ----------------------------------------------- calibracion + suavizado

class AnalizadorGestos:
    """Toma landmarks crudos frame a frame y devuelve estados discretos ya suavizados.

    Arranca en modo calibracion: promedia las metricas durante SEGUNDOS_CALIBRACION con la
    persona en cara neutra y deja fijos los umbrales de la sesion. Mientras calibra devuelve
    siempre la cara neutra, con calibrando=True y progreso de 0 a 1, para que quien lo use
    pueda avisar en pantalla o en la matriz.

    Terminada la calibracion la base NO se vuelve a tocar (ver el comentario de arriba del
    archivo): un gesto sostenido se sigue detectando todo el tiempo que dure.
    """

    ESTADOS_NEUTROS = {
        "ojo_izq": "abierto",
        "ojo_der": "abierto",
        "cejas":   "normal",
        "boca":    "neutra",
        "mirada":  "centro",
    }

    def __init__(self, segundos_calibracion=SEGUNDOS_CALIBRACION,
                 ventana_suavizado=VENTANA_SUAVIZADO):
        self.segundos_calibracion = segundos_calibracion
        self._buf = {k: deque(maxlen=ventana_suavizado) for k in METRICAS}
        self.recalibrar()

    def recalibrar(self):
        """Vuelve a empezar la calibracion. Util si se sienta otra persona adelante."""
        self.calibrando = True
        self.base = None
        self.umbrales = None
        self._acum = {k: 0.0 for k in METRICAS}
        self._n = 0
        self._t0 = None

    def procesar(self, lm):
        medidas = medir(lm)

        for k, buf in self._buf.items():
            buf.append(medidas[k])
        s = {k: sum(buf) / len(buf) for k, buf in self._buf.items()}

        if self.calibrando:
            return self._paso_calibracion(medidas, s)

        ojo_izq = estado_ojo(s["ear_izq"], self.umbrales["ear_izq_cerrado"])
        ojo_der = estado_ojo(s["ear_der"], self.umbrales["ear_der_cerrado"])
        # La mirada solo tiene sentido con los dos ojos abiertos (sin iris visible no hay de
        # donde sacarla); con cualquiera cerrado queda en "centro" -- ver tambien
        # construir_sprite(), que aplica la misma regla por su cuenta al armar el sprite.
        ambos_abiertos = ojo_izq == "abierto" and ojo_der == "abierto"
        mirada = estado_mirada(s["gaze_x"], self.umbrales) if ambos_abiertos else "centro"

        return {
            "calibrando": False,
            "progreso":   1.0,
            "ojo_izq": ojo_izq,
            "ojo_der": ojo_der,
            "cejas":   estado_cejas(s["cejas"], self.umbrales),
            "boca":    estado_boca(s["mar"], s["curva"], self.umbrales),
            "mirada":  mirada,
            "valores": s,
            "base":     self.base,
            "umbrales": self.umbrales,
        }

    def _paso_calibracion(self, medidas, suavizadas):
        """Acumula un frame de cara neutra. El reloj arranca con el primer frame en el que se
        detecto una cara, no con la creacion del objeto: si MediaPipe tarda en enganchar la
        cara, la calibracion espera en vez de promediar tres segundos de nada.

        Ademas de los 3 segundos exige un minimo de frames: en una Jetson cargada el video
        puede ir a pocos FPS, y con 4 o 5 muestras un parpadeo justo en ese momento alcanza
        para arruinar la base de los ojos.
        """
        ahora = time.monotonic()
        if self._t0 is None:
            self._t0 = ahora

        for k in METRICAS:
            self._acum[k] += medidas[k]
        self._n += 1

        transcurrido = ahora - self._t0
        listo = transcurrido >= self.segundos_calibracion and self._n >= MIN_MUESTRAS_CALIBRACION
        if listo:
            self.base = {k: self._acum[k] / self._n for k in METRICAS}
            self.umbrales = umbrales_desde_base(self.base)
            self.calibrando = False

        progreso = (transcurrido / self.segundos_calibracion
                    if self.segundos_calibracion > 0 else 1.0)
        resultado = {
            "calibrando": self.calibrando,
            "progreso":   min(1.0, progreso),
            "restante":   max(0.0, self.segundos_calibracion - transcurrido),
            "muestras":   self._n,
            "valores":    suavizadas,
            "base":       self.base,
            "umbrales":   self.umbrales,
        }
        # Mientras calibra se muestra/manda cara neutra: la persona ya la esta poniendo.
        resultado.update(self.ESTADOS_NEUTROS)
        return resultado


def resumen_calibracion(base, umbrales):
    """Una linea por metrica, con el valor neutro medido y el umbral que salio de ahi. Es lo
    que conviene mirar (o anotar) cuando un gesto no dispara como se espera."""
    return "\n".join([
        f"  ojo izq   neutro {base['ear_izq']:.3f}  -> cerrado si < {umbrales['ear_izq_cerrado']:.3f}",
        f"  ojo der   neutro {base['ear_der']:.3f}  -> cerrado si < {umbrales['ear_der_cerrado']:.3f}",
        f"  cejas     neutro {base['cejas']:.3f}  -> fruncidas si < {umbrales['ceja_fruncida']:.3f}"
        f" / levantadas si > {umbrales['ceja_levantada']:.3f}",
        f"  boca MAR  neutro {base['mar']:.3f}  -> abierta si > {umbrales['mar_abierta']:.3f}",
        f"  curvatura neutro {base['curva']:+.4f} -> triste si < {umbrales['curva_triste']:+.4f}"
        f" / sonrisa si > {umbrales['curva_sonrisa']:+.4f}",
        f"  mirada    neutro {base['gaze_x']:.3f}  -> izq si < {umbrales['gaze_izq']:.3f}"
        f" / der si > {umbrales['gaze_der']:.3f}",
    ])
