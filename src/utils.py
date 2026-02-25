import time
import numpy as np

def now() -> float:
    """ Текущее время (сек) - для меток времени и dt"""
    return time.time()

class FPSMeter:
    """ 
    Экспоненциально-сглаженный FPS (сглаживает скачки фпс за каждую секунду)
    alpha ближе к 1 => сильнее сглаживание.
    """ 
    def __init__(self, alpha: float = 0.9):
        self.alpha = float(alpha)
        self._fps = 0.0
        self._t_prev = None

    def tick(self):
        t = now()
        if self._t_prev is None:
            self._t_prev = t
            return 0
        dt = t - self._t_prev
        self._t_prev = t
        if dt <= 0:
            return self._fps
        inst = 1.0 / dt
        self._fps = self.alpha * self._fps + (1.0 - self.alpha) * inst
        return self._fps

def angle_elbow(S: np.ndarray, 
                E: np.ndarray,
                W: np.ndarray, 
                eps: float = 1e-9) -> float:
                
    u = S - E
    v = W - E
    nu = np.linalg.norm(u) + eps
    nv = np.linalg.norm(v) + eps
    c = float(np.dot(u, v) / (nu * nv))
    c = max(-1.0, min(1.0, c)) # защита от численных ошибок
    return float(np.arccos(c))

def angle_shoulder_dir(S: np.ndarray, E: np.ndarray) -> float:
    a = E - S
    return float(np.arctan2(a[1], a[0]))

