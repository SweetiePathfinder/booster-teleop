import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from utils import FPSMeter, angle_elbow, angle_shoulder_dir

# Индексы landmarks Pose Landmarker (MediaPipe)
# 11: L shoulder, 13: L elbow, 15: L wrist
# 12: R shoulder, 14: R elbow, 16: R wrist
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW,    R_ELBOW    = 13, 14
L_WRIST,    R_WRIST    = 15, 16


def lm2px(lm, w: int, h: int) -> np.ndarray:
    """Normalized landmark -> пиксели."""
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)


def draw_arm(frame, pS, pE, pW, color=(255, 255, 255)):
    cv2.line(frame, tuple(pS.astype(int)), tuple(pE.astype(int)), color, 2)
    cv2.line(frame, tuple(pE.astype(int)), tuple(pW.astype(int)), color, 2)
    cv2.circle(frame, tuple(pS.astype(int)), 5, color, -1)
    cv2.circle(frame, tuple(pE.astype(int)), 5, color, -1)
    cv2.circle(frame, tuple(pW.astype(int)), 5, color, -1)


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

        # timestamp для VIDEO режима (монотонный)
        t_ms += 33
        result = landmarker.detect_for_video(mp_image, t_ms)

        fps = fpsm.tick()

        lines = ["TRACK: no"]
        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            lms = result.pose_landmarks[0]

            # --- Левая рука ---
            lS, lE, lW = lms[L_SHOULDER], lms[L_ELBOW], lms[L_WRIST]
            pLS, pLE, pLW = lm2px(lS, w, h), lm2px(lE, w, h), lm2px(lW, w, h)
            draw_arm(frame_bgr, pLS, pLE, pLW, color=(0, 255, 0))

            th_el_L = angle_elbow(pLS, pLE, pLW)
            th_sh_L = angle_shoulder_dir(pLS, pLE)

            # --- Правая рука ---
            rS, rE, rW = lms[R_SHOULDER], lms[R_ELBOW], lms[R_WRIST]
            pRS, pRE, pRW = lm2px(rS, w, h), lm2px(rE, w, h), lm2px(rW, w, h)
            draw_arm(frame_bgr, pRS, pRE, pRW, color=(0, 200, 255))

            th_el_R = angle_elbow(pRS, pRE, pRW)
            th_sh_R = angle_shoulder_dir(pRS, pRE)

            lines = [
                "TRACK: yes",
                f"L shoulder: {np.degrees(th_sh_L):+6.1f} deg   L elbow: {np.degrees(th_el_L):6.1f} deg",
                f"R shoulder: {np.degrees(th_sh_R):+6.1f} deg   R elbow: {np.degrees(th_el_R):6.1f} deg",
            ]

        # Оверлей текста
        y = 30
        for s in lines:
            cv2.putText(frame_bgr, s, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            y += 30

        cv2.putText(frame_bgr, f"FPS: {fps:.1f}", (10, frame_bgr.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow("02_angles_both_arms", frame_bgr)
        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()