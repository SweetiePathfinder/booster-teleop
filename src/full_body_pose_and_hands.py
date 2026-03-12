import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ----------------------------
# Pose (33 landmarks) indices
# ----------------------------
# Важно: индексы стандартные для Pose Landmarker (BlazePose).
# Ключевые для корпуса:
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW,    R_ELBOW    = 13, 14
L_WRIST,    R_WRIST    = 15, 16
L_HIP,      R_HIP      = 23, 24
L_KNEE,     R_KNEE     = 25, 26
L_ANKLE,    R_ANKLE    = 27, 28

POSE_EDGES = [
    # туловище
    (L_SHOULDER, R_SHOULDER),
    (L_SHOULDER, L_HIP),
    (R_SHOULDER, R_HIP),
    (L_HIP, R_HIP),

    # руки
    (L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST),
    (R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST),

    # ноги
    (L_HIP, L_KNEE), (L_KNEE, L_ANKLE),
    (R_HIP, R_KNEE), (R_KNEE, R_ANKLE),
]

# ----------------------------
# Hands (21 landmarks) edges
# ----------------------------
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

HAND_EDGES = [
    (WRIST, THUMB_CMC), (WRIST, INDEX_MCP), (WRIST, MIDDLE_MCP), (WRIST, RING_MCP), (WRIST, PINKY_MCP),
    (THUMB_CMC, THUMB_MCP), (THUMB_MCP, THUMB_IP), (THUMB_IP, THUMB_TIP),
    (INDEX_MCP, INDEX_PIP), (INDEX_PIP, INDEX_DIP), (INDEX_DIP, INDEX_TIP),
    (MIDDLE_MCP, MIDDLE_PIP), (MIDDLE_PIP, MIDDLE_DIP), (MIDDLE_DIP, MIDDLE_TIP),
    (RING_MCP, RING_PIP), (RING_PIP, RING_DIP), (RING_DIP, RING_TIP),
    (PINKY_MCP, PINKY_PIP), (PINKY_PIP, PINKY_DIP), (PINKY_DIP, PINKY_TIP),
    (THUMB_CMC, INDEX_MCP), (INDEX_MCP, MIDDLE_MCP), (MIDDLE_MCP, RING_MCP), (RING_MCP, PINKY_MCP),
]


def n2px(lm, w: int, h: int) -> np.ndarray:
    """Normalized (0..1) -> pixels."""
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)


def draw_edges(frame, pts_px: np.ndarray, edges, color=(255, 255, 255), thickness=2):
    for a, b in edges:
        pa = pts_px[a].astype(int)
        pb = pts_px[b].astype(int)
        cv2.line(frame, tuple(pa), tuple(pb), color, thickness)


def draw_points(frame, pts_px: np.ndarray, color=(0, 255, 0), r=3):
    for p in pts_px:
        cv2.circle(frame, (int(p[0]), int(p[1])), r, color, -1)


def create_pose_landmarker(model_path: str):
    base = python.BaseOptions(model_asset_path=model_path)
    opts = vision.PoseLandmarkerOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6,
        output_segmentation_masks=False,
    )
    return vision.PoseLandmarker.create_from_options(opts)


def create_hand_landmarker(model_path: str):
    base = python.BaseOptions(model_asset_path=model_path)
    opts = vision.HandLandmarkerOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    return vision.HandLandmarker.create_from_options(opts)


def main(
    cam_index: int = 0,
    pose_model: str = "models/pose_landmarker_lite.task",
    hand_model: str = "models/hand_landmarker.task",
    flip_mirror: bool = False,
):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {cam_index}")

    pose_lm = create_pose_landmarker(pose_model)
    hand_lm = create_hand_landmarker(hand_model)

    t_ms = 0

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break

        if flip_mirror:
            frame_bgr = cv2.flip(frame_bgr, 1)

        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # VIDEO режим требует монотонный timestamp_ms
        t_ms += 33

        pose_res = pose_lm.detect_for_video(mp_image, t_ms)
        hand_res = hand_lm.detect_for_video(mp_image, t_ms)

        # -------- Pose draw --------
        if pose_res.pose_landmarks and len(pose_res.pose_landmarks) > 0:
            lms = pose_res.pose_landmarks[0]  # одна поза
            pose_pts = np.stack([n2px(lm, w, h) for lm in lms], axis=0)

            draw_edges(frame_bgr, pose_pts, POSE_EDGES, color=(255, 255, 255), thickness=2)
            draw_points(frame_bgr, pose_pts, color=(0, 255, 0), r=2)

            # пример: подпишем плечи/таз
            for idx, name in [(L_SHOULDER, "LS"), (R_SHOULDER, "RS"), (L_HIP, "LH"), (R_HIP, "RH")]:
                p = pose_pts[idx].astype(int)
                cv2.putText(frame_bgr, name, (p[0] + 5, p[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        # -------- Hands draw --------
        if hand_res.hand_landmarks:
            for i, lms in enumerate(hand_res.hand_landmarks):
                hand_pts = np.stack([n2px(lm, w, h) for lm in lms], axis=0)

                # handedness label
                label = f"hand{i}"
                if hand_res.handedness and i < len(hand_res.handedness) and len(hand_res.handedness[i]) > 0:
                    cat = hand_res.handedness[i][0]
                    label = f"{cat.category_name}:{cat.score:.2f}"

                draw_edges(frame_bgr, hand_pts, HAND_EDGES, color=(255, 255, 0), thickness=2)
                draw_points(frame_bgr, hand_pts, color=(0, 200, 255), r=2)

                p = hand_pts[WRIST].astype(int)
                cv2.putText(frame_bgr, label, (p[0] + 5, p[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow("full_body_pose_and_hands", frame_bgr)
        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
