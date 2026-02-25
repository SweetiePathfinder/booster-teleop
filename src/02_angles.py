# src/02_angles.py
import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from utils import FPSMeter, angle_elbow, angle_shoulder_dir

# Индексы landmarks из документации :contentReference[oaicite:2]{index=2}
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW,    R_ELBOW    = 13, 14
L_WRIST,    R_WRIST    = 15, 16


def lm2pt_norm(lm, w: int, h: int) -> np.ndarray:
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)


def main(cam_index: int = 0, model_path: str = "models/pose_landmarker_lite.task"):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {cam_index}")

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
    t_ms = 0

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break

        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        t_ms += 33
        result = landmarker.detect_for_video(mp_image, t_ms)
        fps = fpsm.tick()

        txt = ["TRACK: no"]

        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            lms = result.pose_landmarks[0]

            S = lms[L_SHOULDER]
            E = lms[L_ELBOW]
            W = lms[L_WRIST]

            pS = lm2pt_norm(S, w, h)
            pE = lm2pt_norm(E, w, h)
            pW = lm2pt_norm(W, w, h)

            cv2.line(frame_bgr, tuple(pS.astype(int)), tuple(pE.astype(int)), (255, 255, 255), 2)
            cv2.line(frame_bgr, tuple(pE.astype(int)), tuple(pW.astype(int)), (255, 255, 255), 2)

            theta_el = angle_elbow(pS, pE, pW)
            theta_sh = angle_shoulder_dir(pS, pE)

            txt = [
                "TRACK: yes",
                f"shoulder(rad): {theta_sh:+.3f}  deg: {np.degrees(theta_sh):+.1f}",
                f"elbow(rad):    {theta_el:+.3f}  deg: {np.degrees(theta_el):+.1f}",
                f"S/E/W: ({S.x:.2f},{S.y:.2f}) ({E.x:.2f},{E.y:.2f}) ({W.x:.2f},{W.y:.2f})",
            ]

        y = 30
        for line in txt:
            cv2.putText(frame_bgr, line, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            y += 28

        cv2.putText(frame_bgr, f"FPS: {fps:.1f}", (10, frame_bgr.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow("02_angles_tasks", frame_bgr)
        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()