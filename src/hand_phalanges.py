import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Индексы 21 точки кисти (MediaPipe Hands)
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

FINGERS = {
    "thumb":  [THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP],
    "index":  [INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP],
    "middle": [MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP],
    "ring":   [RING_MCP, RING_PIP, RING_DIP, RING_TIP],
    "pinky":  [PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP],
}

# Рёбра для рисования "костей" (фаланги/суставы)
EDGES = [
    # ладонь
    (WRIST, THUMB_CMC), (WRIST, INDEX_MCP), (WRIST, MIDDLE_MCP), (WRIST, RING_MCP), (WRIST, PINKY_MCP),
    # большой палец
    (THUMB_CMC, THUMB_MCP), (THUMB_MCP, THUMB_IP), (THUMB_IP, THUMB_TIP),
    # указательный
    (INDEX_MCP, INDEX_PIP), (INDEX_PIP, INDEX_DIP), (INDEX_DIP, INDEX_TIP),
    # средний
    (MIDDLE_MCP, MIDDLE_PIP), (MIDDLE_PIP, MIDDLE_DIP), (MIDDLE_DIP, MIDDLE_TIP),
    # безымянный
    (RING_MCP, RING_PIP), (RING_PIP, RING_DIP), (RING_DIP, RING_TIP),
    # мизинец
    (PINKY_MCP, PINKY_PIP), (PINKY_PIP, PINKY_DIP), (PINKY_DIP, PINKY_TIP),
    # перемычки по ладони (как в mediapipe drawing)
    (THUMB_CMC, INDEX_MCP), (INDEX_MCP, MIDDLE_MCP), (MIDDLE_MCP, RING_MCP), (RING_MCP, PINKY_MCP),
]


def lm_to_px(lm, w, h):
    """Normalized landmark -> пиксели."""
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)


def draw_hand(frame, pts_px):
    """Рисуем точки и рёбра."""
    # точки
    for i, p in enumerate(pts_px):
        x, y = int(p[0]), int(p[1])
        cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

    # кости
    for a, b in EDGES:
        pa = pts_px[a].astype(int)
        pb = pts_px[b].astype(int)
        cv2.line(frame, tuple(pa), tuple(pb), (255, 255, 255), 2)


def phalanx_vectors(pts_px):
    """
    Возвращает "фаланги" как векторы между последовательными суставами:
    например index: MCP->PIP, PIP->DIP, DIP->TIP.
    """
    out = {}
    for name, idxs in FINGERS.items():
        segs = []
        for i in range(len(idxs) - 1):
            a = pts_px[idxs[i]]
            b = pts_px[idxs[i + 1]]
            segs.append(b - a)  # вектор фаланги в пикселях
        out[name] = segs
    return out


def main(cam_index=0, model_path="models/hand_landmarker.task"):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {cam_index}")

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

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

        # result.hand_landmarks: list рук, каждая — список из 21 landmark
        if result.hand_landmarks:
            for hand_i, lms in enumerate(result.hand_landmarks):
                pts_px = np.stack([lm_to_px(lm, w, h) for lm in lms], axis=0)

                draw_hand(frame_bgr, pts_px)

                # Печать ключевых суставов (пример: для указательного)
                idx = FINGERS["index"]
                p_mcp = pts_px[idx[0]]
                p_pip = pts_px[idx[1]]
                p_dip = pts_px[idx[2]]
                p_tip = pts_px[idx[3]]

                cv2.putText(frame_bgr, f"hand {hand_i}: index TIP=({int(p_tip[0])},{int(p_tip[1])})",
                            (10, 30 + 25 * hand_i), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (255, 255, 255), 2, cv2.LINE_AA)

                # Если нужно: фаланги как векторы
                vecs = phalanx_vectors(pts_px)
                # пример: длины фаланг указательного в пикселях
                lens = [float(np.linalg.norm(v)) for v in vecs["index"]]
                # можно печатать в консоль (не каждый кадр, чтобы не спамить)
                # print("index phalanx lengths px:", lens)

        cv2.imshow("hand_phalanges", frame_bgr)
        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()