# Abecedario de Senas LED - lado Jetson - Fase 4/5: clasificar letra en vivo, con ventana de
# landmarks y estabilizador temporal.
#
# Mismo patron que jetson_face.py del espejo facial: abre una ventana local (cv2.imshow) con los
# landmarks dibujados sobre el video y el estado actual en texto, para poder ajustar sin
# necesitar la PC ni streaming por RTP. Igual que alli, hace falta un monitor conectado a la
# Jetson con sesion grafica activa (DISPLAY seteado); si se corre por SSH sin -X, cv2.imshow no
# tiene donde abrir la ventana y el script corta con error. Cerrar la ventana con 'q' (con foco
# en ella) o Ctrl+C en la consola.
#
# Ademas de clasificar cada frame (como antes), agrega el estabilizador temporal (paso 5 del
# plan): el ruido frame a frame del detector (ya visto en probar_manos.py, una punta de dedo
# saltando de golpe en algun frame suelto) puede tirar una letra distinta por un instante aunque
# la mano no se haya movido -- sin filtrar eso, la matriz de LEDs titilaria entre letras. La
# letra "cruda" (la que predice el modelo en ESE frame) no se confirma hasta que se repite
# UMBRAL_ESTABLE veces seguidas -- ver la clase EstabilizadorLetra abajo. Es el mismo rol que la
# media movil de gestos.py en el espejo facial, pero sobre un valor discreto (contar
# repeticiones) en vez de promediar un numero continuo.
#
# Con la letra ya estabilizada arma un TEXTO de corrido: cada letra confirmada se agrega a una
# sola linea de consola que se reescribe con \r (no una linea nueva por letra), y las etiquetas
# 'space' y 'del' del dataset se usan como lo que son, comandos de edicion: espacio y borrar el
# ultimo caracter. Para escribir una letra repetida ("LL", "RR") o borrar varios caracteres hay
# dos caminos: sostener la misma letra, que se auto-repite como una tecla mantenida
# (UMBRAL_REPETICION), o sacar la mano un instante y volver a hacerla (UMBRAL_SIN_MANO).
#
# Antes de correr: necesita, ademas de lo que ya usa probar_manos.py (mediapipe, opencv,
# hand_landmarker.task), tener scikit-learn y joblib instalados EN LA MISMA VERSION con la que
# se genero el .pkl en la PC de escritorio -- ver ../README.md, seccion "Compatibilidad de
# versiones entre la PC y la Jetson". Si no coinciden, joblib.load() puede tirar
# InconsistentVersionWarning (no siempre un error duro, pero sin garantia de resultado correcto).

import time

import cv2
import joblib
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import manos

MODELO_MANOS = '/home/indea/hand_landmarker.task'
MODELO_LETRAS = 'abecedario_modelo.pkl'

# Cuantos frames SEGUIDOS tiene que repetirse la misma letra cruda antes de confirmarla. Es el
# primer numero a tocar en el paso 8 (ajuste fino): muy bajo deja pasar ruido, muy alto hace que
# la matriz tarde en reaccionar a una letra nueva.
UMBRAL_ESTABLE = 8

# Cada cuantos frames EXTRA de sostener la misma letra se vuelve a escribir. Es el auto-repeat
# del teclado: mantener la letra escribe "AA", "LL", "RR", y mantener 'del' borra varios
# caracteres seguidos, sin tener que sacar la mano entre medio. Mas alto = mas dificil repetir
# sin querer mientras uno piensa; mas bajo = repetir es mas comodo pero se escapan duplicados.
UMBRAL_REPETICION = 16

# Cuantos frames SEGUIDOS sin letra valida (sin mano a la vista, o vector degenerado) hacen falta
# para "soltar" la letra sostenida. Sacando la mano, la siguiente letra vuelve a escribirse a los
# UMBRAL_ESTABLE frames en vez de esperar el auto-repeat: es el camino rapido para repetir.
UMBRAL_SIN_MANO = 10


class EstabilizadorLetra:
    """Filtra el ruido frame a frame del detector y decide QUE ESCRIBIR en cada frame.

    `procesar()` devuelve la etiqueta que hay que escribir en este frame, o None si no hay nada
    que escribir (que es lo normal en la gran mayoria de los frames). `self.confirmada` queda con
    la letra que se esta sosteniendo, para mostrarla en pantalla.

    Tres reglas:
      1. Una letra nueva se escribe recien cuando salio UMBRAL_ESTABLE frames seguidos: asi el
         ruido del detector (una punta de dedo saltando en un frame suelto) no llega al texto.
      2. Sostenerla UMBRAL_REPETICION frames mas la vuelve a escribir, y otra vez cada
         UMBRAL_REPETICION mientras siga sostenida -- igual que mantener una tecla apretada.
      3. Un parpadeo del detector en el medio (la letra cambia unos pocos frames y vuelve) NO
         reescribe la letra: para volver a escribirla tiene que pasar por la regla 2 o por
         UMBRAL_SIN_MANO. Sin esto, cualquier salto de ruido mientras se sostiene una letra
         ensuciaria el texto con duplicados.
    """

    def __init__(self, umbral=UMBRAL_ESTABLE, repeticion=UMBRAL_REPETICION,
                 umbral_sin_mano=UMBRAL_SIN_MANO):
        self.umbral = umbral
        self.repeticion = repeticion
        self.umbral_sin_mano = umbral_sin_mano
        self.candidata = None
        self.repeticiones = 0
        self.sin_mano = 0
        self.confirmada = None

    def procesar(self, letra_cruda):
        if letra_cruda is None:
            self.candidata = None
            self.repeticiones = 0
            self.sin_mano += 1
            if self.sin_mano >= self.umbral_sin_mano:
                self.confirmada = None
            return None

        self.sin_mano = 0
        if letra_cruda == self.candidata:
            self.repeticiones += 1
        else:
            self.candidata = letra_cruda
            self.repeticiones = 1

        if self.repeticiones == self.umbral:
            if self.candidata != self.confirmada:      # regla 1: letra nueva
                self.confirmada = self.candidata
                return self.candidata
            return None                                # regla 3: era un parpadeo, no reescribe

        if (self.repeticiones > self.umbral
                and (self.repeticiones - self.umbral) % self.repeticion == 0):
            return self.candidata                      # regla 2: sostenida, auto-repeat

        return None

    def faltan(self):
        """Frames que faltan para la proxima escritura si se sigue sosteniendo la letra actual.
        Solo para mostrar en pantalla: sirve para ver venir el auto-repeat."""
        if self.candidata is None:
            return None
        if self.repeticiones < self.umbral:
            return self.umbral - self.repeticiones
        return self.repeticion - ((self.repeticiones - self.umbral) % self.repeticion)


def aplicar_al_texto(texto, etiqueta):
    """Traduce una etiqueta recien confirmada a su efecto sobre el texto que se va escribiendo.
    'space' y 'del' no son letras: son los dos comandos de edicion que trae el dataset."""
    if etiqueta == "space":
        return texto + " "
    if etiqueta == "del":
        return texto[:-1]
    return texto + etiqueta


def mostrar_texto(texto):
    # Se reescribe SIEMPRE la misma linea de consola (\r al principio, sin salto al final): asi
    # el texto se ve crecer de corrido, como si se escribiera, en vez de una linea por letra. El
    # relleno a 60 borra lo que haya quedado de un texto mas largo despues de un 'del'.
    print(f"\rTexto: {texto:<60}", end="", flush=True)


def texto_con_borde(frame, texto, y, color=(0, 255, 0)):
    # Texto negro grueso debajo y de color fino encima: se lee igual sobre fondo claro u oscuro
    # (mismo helper que jetson_face.py del espejo facial).
    cv2.putText(frame, texto, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
    cv2.putText(frame, texto, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)


options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODELO_MANOS),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

modelo = joblib.load(MODELO_LETRAS)  # se carga una sola vez, antes del loop
estabilizador = EstabilizadorLetra()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    # Casi siempre es otro proceso que quedo con la camara tomada (ojo con Ctrl+Z, que
    # suspende en vez de cerrar). Se limpia con:  pkill -f reconocer_letra
    raise SystemExit(
        "No se pudo abrir la camara (/dev/video0). Suele ser otro proceso que la tiene "
        "ocupada: revisalo con 'ps aux | grep -E \"probar_manos|reconocer_letra\" | grep -v grep'")

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

VENTANA = "Abecedario de Senas - landmarks (Jetson)"
cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)

print("Camara abierta. Mostrale una letra - 'q' en la ventana o Ctrl+C en la consola para cortar")
print("Sostener la misma letra la repite (como mantener una tecla); tambien vale sacar la mano.\n")

texto = ""
inicio = time.time()

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        ts_ms = int((time.time() - inicio) * 1000)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = detector.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)

        if not resultado.hand_landmarks:
            # Sin mano nunca hay nada que escribir; procesar(None) solo lleva la cuenta para
            # soltar la letra sostenida despues de UMBRAL_SIN_MANO frames.
            estabilizador.procesar(None)
            texto_con_borde(frame, "Mano: no detectada", 30, (0, 0, 255))
            texto_con_borde(frame, f"Texto: {texto[-30:]}", 80, (255, 255, 0))
            cv2.imshow(VENTANA, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # hand_landmarks (no world_landmarks) esta en 0..1 relativo a la imagen -- sirve para
        # dibujar sobre el frame. hand_world_landmarks (mas abajo) trae la profundidad real que
        # necesita manos.vector_normalizado(); son dos cosas distintas, ver README.md.
        lm = resultado.hand_landmarks[0]
        h, w = frame.shape[:2]
        for p in lm:
            cv2.circle(frame, (int(p.x * w), int(p.y * h)), 3, (0, 255, 0), -1)

        mundo = resultado.hand_world_landmarks[0]
        mano = resultado.handedness[0][0].category_name

        vector = manos.vector_normalizado(mundo, mano)
        if vector is None:
            # Misma escala degenerada que ya filtraba extraer_landmarks.py durante el
            # entrenamiento: mano demasiado pegada al centro, distancia muneca->nudillo ~0.
            letra_cruda = None
            texto_con_borde(frame, "Mano detectada, vector degenerado", 30, (0, 165, 255))
        else:
            letra_cruda = modelo.predict([vector])[0]
            texto_con_borde(frame, f"Letra cruda (este frame): {letra_cruda}", 30)

        a_escribir = estabilizador.procesar(letra_cruda)
        if a_escribir is not None:
            texto = aplicar_al_texto(texto, a_escribir)
            mostrar_texto(texto)

        confirmada = estabilizador.confirmada
        faltan = estabilizador.faltan()
        color_confirmada = (0, 255, 0) if confirmada == letra_cruda else (200, 200, 200)
        texto_con_borde(
            frame,
            f"Letra confirmada: {confirmada or '-'}  "
            f"(escribe en {faltan if faltan is not None else '-'})",
            55, color_confirmada)
        texto_con_borde(frame, f"Texto: {texto[-30:]}", 80, (255, 255, 0))

        cv2.imshow(VENTANA, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    # El \n cierra la linea que se venia reescribiendo con \r, para que el texto final quede
    # escrito en la consola y no lo pise el prompt.
    print(f"\nTexto final: {texto!r}")
    # En un finally para que la camara se libere tambien si el script muere por un error
    # inesperado, no solo con Ctrl+C.
    cap.release()
    cv2.destroyAllWindows()
    detector.close()
