# Espejo Facial LED - lado Jetson - herramienta de diagnostico
# Transmite la webcam en vivo por RTP/UDP hacia una PC (la Jetson no tiene monitor), con los
# landmarks de MediaPipe dibujados encima y los estados de cejas/ojos/boca como texto, mas los
# valores numericos crudos -- esos numeros son los que sirven para ajustar los umbrales de
# gestos.py si algun gesto cuesta que se dispare. Ver ../lado_jetson.md.
#
# Usa exactamente la misma logica que jetson_face.py (ambos importan gestos.py), asi lo que
# ves aca es lo mismo que se le manda a la matriz. Eso incluye la calibracion: los primeros
# 3 segundos hay que quedarse con cara neutra, y en pantalla aparece la cuenta regresiva.
#
# En la PC, correr esto ANTES de este script (mismo puerto que PORT_VIDEO):
#   gst-launch-1.0 -v udpsrc port=1234 \
#     caps="application/x-rtp, media=(string)video, encoding-name=(string)H264, payload=(int)96" ! \
#     rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink

import cv2, time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import gestos

MODEL = '/home/indea/face_landmarker.task'
IP_PC = "192.168.1.101"
PORT_VIDEO = 1234

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

pipeline_salida = (
    f"appsrc ! videoconvert ! x264enc speed-preset=ultrafast tune=zerolatency ! "
    f"rtph264pay config-interval=1 pt=96 ! udpsink host={IP_PC} port={PORT_VIDEO}"
)
out = cv2.VideoWriter(pipeline_salida, cv2.CAP_GSTREAMER, 0, 20, (640, 480), True)

print("Transmitiendo a", IP_PC, "puerto", PORT_VIDEO, "- Ctrl+C para cortar")
print(f"Calibrando {gestos.SEGUNDOS_CALIBRACION:.0f} s: quedate con CARA NEUTRA mirando a la camara...")

analizador = gestos.AnalizadorGestos()
ya_mostro_calibracion = False
start = time.time()


def texto_con_borde(frame, texto, y, color=(0, 255, 0)):
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

        if result.face_landmarks:
            lm = result.face_landmarks[0]
            h, w = frame.shape[:2]
            for p in lm:
                cv2.circle(frame, (int(p.x * w), int(p.y * h)), 1, (0, 255, 0), -1)

            estados = analizador.procesar(lm)
            v = estados["valores"]

            if estados["calibrando"]:
                texto_con_borde(
                    frame,
                    f"CALIBRANDO {estados['restante']:.1f}s - QUEDATE CON CARA NEUTRA",
                    30, (0, 200, 255))
                # Barra de progreso, para que se entienda cuanto falta sin leer el numero
                ancho = int(estados["progreso"] * (frame.shape[1] - 20))
                cv2.rectangle(frame, (10, 40), (10 + ancho, 52), (0, 200, 255), -1)
            else:
                if not ya_mostro_calibracion:
                    print("Calibracion lista. Umbrales de esta cara:")
                    print(gestos.resumen_calibracion(estados["base"], estados["umbrales"]))
                    ya_mostro_calibracion = True

                u = estados["umbrales"]
                texto_con_borde(frame, f"Cejas: {estados['cejas']}", 30)
                texto_con_borde(frame, f"Ojos: izq {estados['ojo_izq']} / der {estados['ojo_der']}", 55)
                texto_con_borde(frame, f"Boca: {estados['boca']}", 80)
                texto_con_borde(frame, f"Mirada: {estados['mirada']}", 105)
                # Los valores crudos con el umbral YA CALIBRADO de esta persona al lado: son los
                # numeros que hay que mirar para ajustar los DELTA_* de gestos.py si algun gesto
                # no se dispara.
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

        out.write(frame)
except KeyboardInterrupt:
    print("Cortado con Ctrl+C")
finally:
    # En un finally para que la camara se libere tambien si el script muere por un error
    # inesperado, no solo con Ctrl+C.
    cap.release()
    out.release()
    detector.close()
