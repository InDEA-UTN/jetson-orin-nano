# Espejo Facial LED - lado Jetson
# Fase 6 + 7: captura la webcam USB, corre MediaPipe Face Landmarker en vivo, cuantiza los
# gestos a estados discretos (ojos abierto/cerrado por ojo, cejas en 3 posiciones, boca en 4
# formas, mirada izquierda/centro/derecha cuando los dos ojos estan abiertos), compone un sprite de
# 8x8 y lo manda por UDP a la Pico W, que lo dibuja en la matriz MAX7219 (ver ../lado_pico.md
# seccion 9 y ../lado_jetson.md).
#
# Ademas, si hay un monitor conectado a la Jetson, abre una ventana local (cv2.imshow) con los
# landmarks dibujados y los mismos estados/valores que se mandan a la matriz -- para ajustar
# gestos.py ya no hace falta la PC ni el streaming por RTP de ver_camara_en_vivo.py, que sigue
# existiendo para cuando la Jetson esta sin monitor. Cerrar la ventana con 'q' (con foco en ella)
# o Ctrl+C en la consola.
#
# Necesita, con el venv (~/espejo_facial_venv) activado:
#   - mediapipe, opencv (ver ../lado_jetson.md secciones 3 y 5)
#   - el modelo descargado en /home/indea/proyecto_gestos/face_landmarker.task
#   - gestos.py al lado de este archivo (la logica de metricas, estados y sprite)
#   - un monitor conectado a la Jetson con sesion grafica activa (DISPLAY seteado); si se corre
#     por SSH sin -X, cv2.imshow no tiene donde abrir la ventana y el script corta con error
#
# Al arrancar hace 3 segundos de calibracion: hay que quedarse con CARA NEUTRA mirando a la
# camara mientras dura. Con ese promedio arma los umbrales de esta persona y recien despues
# empieza a reaccionar a los gestos (ver gestos.py). Durante la calibracion la matriz ya
# muestra la cara neutra, asi que se ve que el sistema esta vivo.
#
# IP_PICO es la IP que le asigna el hotspot de la propia Jetson (red "espejo-jetson", ver
# ../integracion.md seccion 11) - la asigna el DHCP de la Jetson y puede cambiar entre sesiones,
# asi que conviene confirmarla en el Shell de Thonny (main.py la imprime al conectar) antes de
# correr este script si dejo de andar.

import cv2, time, socket
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import gestos

MODEL = '/home/indea/proyecto_gestos/face_landmarker.task'
IP_PICO = "10.42.0.170"
PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1)
detector = vision.FaceLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    # Casi siempre es otro proceso que quedo con la camara tomada (ojo con Ctrl+Z, que
    # suspende en vez de cerrar). Se limpia con:  pkill -f jetson_face ; pkill -f ver_camara
    raise SystemExit(
        "No se pudo abrir la camara (/dev/video0). Suele ser otro proceso que la tiene "
        "ocupada: revisalo con 'ps aux | grep -E \"jetson_face|ver_camara\" | grep -v grep'")

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

VENTANA = "Espejo Facial - landmarks (Jetson)"
cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)

print("Camara abierta. Mandando a", IP_PICO, "puerto", PORT,
      "- 'q' en la ventana o Ctrl+C en la consola para cortar")
print(f"Calibrando {gestos.SEGUNDOS_CALIBRACION:.0f} s: quedate con CARA NEUTRA mirando a la camara...")

analizador = gestos.AnalizadorGestos()
anterior = None
ultimo_restante = None
start = time.time()


def texto_con_borde(frame, texto, y, color=(0, 255, 0)):
    # Texto negro grueso debajo y de color fino encima: se lee igual sobre fondo claro u oscuro.
    cv2.putText(frame, texto, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
    cv2.putText(frame, texto, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)


try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        ts_ms = int((time.time() - start) * 1000)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)
        if not result.face_landmarks:
            # Sin esto la matriz queda congelada en el ultimo gesto cuando la persona se va de
            # cuadro -- mismo criterio que los scripts de abecedario_de_senas: mandar SIEMPRE,
            # haya deteccion o no, para que la matriz refleje el estado real de la camara.
            sock.sendto(gestos.sprite_a_bytes(["0" * 8] * 8), (IP_PICO, PORT))
            cv2.imshow(VENTANA, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        lm = result.face_landmarks[0]
        h, w = frame.shape[:2]
        for p in lm:
            cv2.circle(frame, (int(p.x * w), int(p.y * h)), 1, (0, 255, 0), -1)

        estados = analizador.procesar(lm)
        sprite = gestos.construir_sprite(
            estados["ojo_izq"], estados["ojo_der"], estados["cejas"], estados["boca"],
            estados["mirada"])
        sock.sendto(gestos.sprite_a_bytes(sprite), (IP_PICO, PORT))

        if estados["calibrando"]:
            texto_con_borde(
                frame,
                f"CALIBRANDO {estados['restante']:.1f}s - QUEDATE CON CARA NEUTRA",
                30, (0, 200, 255))
            ancho = int(estados["progreso"] * (frame.shape[1] - 20))
            cv2.rectangle(frame, (10, 40), (10 + ancho, 52), (0, 200, 255), -1)

            # Cuenta regresiva en consola, una linea por segundo entero (util si no se ve la
            # ventana, por ejemplo corriendo por SSH sin monitor a mano en ese momento).
            restante = int(estados["restante"]) + 1
            if restante != ultimo_restante:
                print(f"  calibrando... {restante} s (cara neutra)")
                ultimo_restante = restante

            cv2.imshow(VENTANA, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        if ultimo_restante is not None:      # primer frame ya calibrado: se muestra que salio
            print("Calibracion lista. Umbrales de esta cara:")
            print(gestos.resumen_calibracion(estados["base"], estados["umbrales"]))
            ultimo_restante = None

        v = estados["valores"]
        u = estados["umbrales"]
        texto_con_borde(frame, f"Cejas: {estados['cejas']}", 30)
        texto_con_borde(frame, f"Ojos: izq {estados['ojo_izq']} / der {estados['ojo_der']}", 55)
        texto_con_borde(frame, f"Boca: {estados['boca']}", 80)
        texto_con_borde(frame, f"Mirada: {estados['mirada']}", 105)
        # Los valores crudos con el umbral YA CALIBRADO de esta persona al lado: son los numeros
        # que hay que mirar para ajustar los DELTA_* de gestos.py si algun gesto no se dispara.
        texto_con_borde(
            frame,
            f"EAR {v['ear_izq']:.2f}/{v['ear_der']:.2f} "
            f"(cerr <{u['ear_izq_cerrado']:.2f}/{u['ear_der_cerrado']:.2f})  "
            f"MAR {v['mar']:.2f} (abierta >{u['mar_abierta']:.2f})",
            130, (200, 200, 200))
        texto_con_borde(
            frame,
            f"cejas {v['cejas']:.3f} "
            f"(frunc <{u['ceja_fruncida']:.3f} / lev >{u['ceja_levantada']:.3f})  "
            f"curva {v['curva']:+.4f} "
            f"(triste <{u['curva_triste']:+.4f} / sonrisa >{u['curva_sonrisa']:+.4f})",
            153, (200, 200, 200))
        texto_con_borde(
            frame,
            f"gaze_x {v['gaze_x']:.3f} "
            f"(izq <{u['gaze_izq']:.3f} / der >{u['gaze_der']:.3f})",
            176, (200, 200, 200))

        cv2.imshow(VENTANA, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Solo se imprime cuando cambia algun estado, para no llenar la consola a 30 por segundo
        actual = (estados["ojo_izq"], estados["ojo_der"], estados["cejas"], estados["boca"],
                  estados["mirada"])
        if actual != anterior:
            print(f"ojo_izq={actual[0]:<9} ojo_der={actual[1]:<9} "
                  f"cejas={actual[2]:<11} boca={actual[3]:<8} mirada={actual[4]}")
            anterior = actual

except KeyboardInterrupt:
    print("Cortado con Ctrl+C")
finally:
    # En un finally para que la camara se libere tambien si el script muere por un error
    # inesperado, no solo con Ctrl+C.
    cap.release()
    cv2.destroyAllWindows()
    detector.close()
