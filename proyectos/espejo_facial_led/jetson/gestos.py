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
DELTA_CURVA_SONRISA   = 0.015   # sonrisa si la curvatura sube esto sobre la neutra
DELTA_CURVA_TRISTE    = 0.015   # triste si la curvatura baja esto de la neutra

VENTANA_SUAVIZADO = 5    # media movil corta: saca el temblor del detector

METRICAS = ("ear_izq", "ear_der", "cejas", "mar", "curva")


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

def medir(lm):
    """Las cinco metricas crudas de un frame."""
    return {
        "ear_izq": ear_izquierdo(lm),
        "ear_der": ear_derecho(lm),
        "cejas":   altura_cejas(lm),
        "mar":     mar(lm),
        "curva":   curvatura_boca(lm),
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


# --------------------------------------------------- composicion del sprite
#
# Reparto de las 8 filas:
#   0    cejas levantadas
#   1    cejas normales / fruncidas
#   2    (separador: sin esta fila, unas cejas normales y unos ojos cerrados quedan pegados
#         y se leen como una sola ceja gruesa)
#   3    ojos
#   4    (separador)
#   5-7  boca

def construir_sprite(ojo_izq, ojo_der, cejas, boca):
    """Compone la matriz de 8x8 combinando el estado de cada rasgo por separado, en vez de
    elegir entre caritas completas predefinidas."""
    grid = [['0'] * 8 for _ in range(8)]

    # Cejas: arriba = levantadas, abajo = normales, abajo y juntas hacia el centro = fruncidas
    if cejas == "levantadas":
        for c in (1, 2, 5, 6):
            grid[0][c] = '1'
    elif cejas == "fruncidas":
        for c in (2, 3, 4, 5):
            grid[1][c] = '1'
    else:
        for c in (1, 2, 5, 6):
            grid[1][c] = '1'

    # Ojos: abierto = un punto; cerrado = dos puntos horizontales (el parpado cerrado),
    # extendiendose hacia afuera de la cara para que quede libre el centro (columnas 3 y 4)
    # y los dos ojos se sigan leyendo separados, en vez de fundirse en una sola linea.
    if ojo_izq == "abierto":
        grid[3][2] = '1'
    else:
        grid[3][1] = grid[3][2] = '1'

    if ojo_der == "abierto":
        grid[3][5] = '1'
    else:
        grid[3][5] = grid[3][6] = '1'

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

        return {
            "calibrando": False,
            "progreso":   1.0,
            "ojo_izq": estado_ojo(s["ear_izq"], self.umbrales["ear_izq_cerrado"]),
            "ojo_der": estado_ojo(s["ear_der"], self.umbrales["ear_der_cerrado"]),
            "cejas":   estado_cejas(s["cejas"], self.umbrales),
            "boca":    estado_boca(s["mar"], s["curva"], self.umbrales),
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
    ])
