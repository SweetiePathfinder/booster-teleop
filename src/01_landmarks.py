# src/01_landmarks.py
import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from utils import FPSMeter

# Индексы landmarks (как в документации Pose Landmarker)
# 11: left shoulder, 13: left elbow, 15: left wrist
# 12: right shoulder, 14: right elbow, 16: right wrist  :contentReference[oaicite:1]{index=1}
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW,    R_ELBOW    = 13, 14
L_WRIST,    R_WRIST    = 15, 16


def lm2pt_norm(lm, w: int, h: int) -> np.ndarray:
    """Normalized landmark (x,y in 0..1) -> pixel (x,y)."""
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)


def draw_point(img, p: np.ndarray, label: str, color=(0, 255, 0)):
    x, y = int(p[0]), int(p[1])
    cv2.circle(img, (x, y), 6, color, -1)
    cv2.putText(img, label, (x + 8, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def main(cam_index: int = 0, model_path: str = "models/pose_landmarker_lite.task"):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {cam_index}")

    # Создаём PoseLandmarker
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6,
        output_segmentation_masks=False,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    fpsm = FPSMeter()
    t_ms = 0  # timestamp в миллисекундах (монотонный)

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break

        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # MediaPipe Tasks принимает mp.Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # В режиме VIDEO надо подавать timestamp_ms (монотонный)
        t_ms += 33  # грубо ~30 FPS; можно считать от time.time(), но для MVP хватит
        result = landmarker.detect_for_video(mp_image, t_ms)

        fps = fpsm.tick()

        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            lms = result.pose_landmarks[0]  # одна поза

            S = lms[L_SHOULDER]
            E = lms[L_ELBOW]
            W = lms[L_WRIST]

            pS = lm2pt_norm(S, w, h)
            pE = lm2pt_norm(E, w, h)
            pW = lm2pt_norm(W, w, h)

            draw_point(frame_bgr, pS, "LS", (0, 255, 0))
            draw_point(frame_bgr, pE, "LE", (0, 200, 255))
            draw_point(frame_bgr, pW, "LW", (255, 200, 0))

            cv2.line(frame_bgr, tuple(pS.astype(int)), tuple(pE.astype(int)), (255, 255, 255), 2)
            cv2.line(frame_bgr, tuple(pE.astype(int)), tuple(pW.astype(int)), (255, 255, 255), 2)

        cv2.putText(frame_bgr, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow("01_landmarks_tasks", frame_bgr)
        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()