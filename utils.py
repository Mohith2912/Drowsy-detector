"""
utils.py — Utility constants and helper functions for AI Drowsiness Detection.
"""

import time
import numpy as np

# ─── MediaPipe Face Mesh Landmark Indices ──────────────────────────────────────
# These are the specific landmark indices from the 468-point Face Mesh model
# that outline each eye. We use 6 points per eye to compute EAR.

# Left eye (from the subject's perspective)
LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

# Right eye (from the subject's perspective)
RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]

# ─── EAR Thresholds ───────────────────────────────────────────────────────────
EAR_THRESHOLD = 0.21          # Below this → eyes considered "closed"
DROWSY_TIME_THRESHOLD = 3.0   # Seconds of continuous eye closure → drowsy alarm

# ─── Display Colors (BGR for OpenCV) ──────────────────────────────────────────
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_YELLOW = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_CYAN = (255, 255, 0)
COLOR_DARK_BG = (30, 30, 30)


def compute_ear(landmarks, eye_indices, frame_w, frame_h):
    """
    Compute the Eye Aspect Ratio (EAR) for one eye.

    EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)

    Points layout:
        p2    p3
    p1            p4
        p6    p5

    Args:
        landmarks: MediaPipe face landmarks (normalized 0–1).
        eye_indices: List of 6 landmark indices [p1, p2, p3, p4, p5, p6].
        frame_w: Frame width in pixels.
        frame_h: Frame height in pixels.

    Returns:
        ear (float): The Eye Aspect Ratio value.
        points (list): List of (x, y) pixel coordinates for the 6 landmarks.
    """
    coords = []
    for idx in eye_indices:
        lm = landmarks[idx]
        x = int(lm.x * frame_w)
        y = int(lm.y * frame_h)
        coords.append((x, y))

    # Convert to numpy for vectorized distance computation
    p = np.array(coords, dtype=np.float64)

    # Vertical distances
    vertical_1 = np.linalg.norm(p[1] - p[5])  # ||p2 - p6||
    vertical_2 = np.linalg.norm(p[2] - p[4])  # ||p3 - p5||

    # Horizontal distance
    horizontal = np.linalg.norm(p[0] - p[3])   # ||p1 - p4||

    # Avoid division by zero
    if horizontal < 1e-6:
        return 0.0, coords

    ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
    return ear, coords


class FPSCounter:
    """Smoothed FPS counter using a rolling window."""

    def __init__(self, window_size=30):
        self._times = []
        self._window = window_size

    def tick(self):
        """Call once per frame."""
        self._times.append(time.perf_counter())
        if len(self._times) > self._window:
            self._times.pop(0)

    @property
    def fps(self):
        if len(self._times) < 2:
            return 0.0
        elapsed = self._times[-1] - self._times[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._times) - 1) / elapsed