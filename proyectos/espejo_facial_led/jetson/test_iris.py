import cv2, time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL = '/home/indea/face_landmarker.task'

options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1)
detector = vision.FaceLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise SystemExit("no se pudo abrir la camara")

GRUPO_A = 468   # centro de un iris (el otro grupo de 5 empieza en 473)
GRUPO_B = 473

def gaze_relativo(lm, centro_iris, esquina_ext, esquina_int):
    """0.0 = mirando hacia la esquina externa, 1.0 = hacia la interna (nariz)."""
    ext_x, int_x = lm[esquina_ext].x, lm[esquina_int].x
    return (lm[centro_iris].x - ext_x) / (int_x - ext_x)

print("Cabeza QUIETA, mové solo los ojos de un lado a otro. Ctrl+C para cortar.")
start = time.time()
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        ts_ms = int((time.time() - start) * 1000)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)
        if not result.face_landmarks:
            continue
        lm = result.face_landmarks[0]
        if len(lm) < 478:
            raise SystemExit(f"Solo {len(lm)} landmarks: sin iris.")

        # ojo_izq de este proyecto = esquinas 33 (externa) / 133 (interna)
        # ojo_der de este proyecto = esquinas 362 (interna) / 263 (externa)
        x_izq = sorted([lm[33].x, lm[133].x])
        iris_izq = GRUPO_A if x_izq[0] <= lm[GRUPO_A].x <= x_izq[1] else GRUPO_B
        iris_der = GRUPO_B if iris_izq == GRUPO_A else GRUPO_A

        g_izq = gaze_relativo(lm, iris_izq, 33, 133)
        g_der = gaze_relativo(lm, iris_der, 263, 362)
        print(f"gaze izq={g_izq:.2f}  gaze der={g_der:.2f}")
except KeyboardInterrupt:
    pass
finally:
    cap.release()
    detector.close()
