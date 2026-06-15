"""
eye_detector.py — Real-time eye state detection using MediaPipe FaceLandmarker (Tasks API).

Uses the new MediaPipe Tasks Python API (mp.tasks.python.vision.FaceLandmarker)
to extract face landmarks, compute the Eye Aspect Ratio (EAR), and determine
whether the subject's eyes are open or closed.
"""

import os
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,
)

from utils import (
    LEFT_EYE_INDICES,
    RIGHT_EYE_INDICES,
    EAR_THRESHOLD,
    compute_ear,
)

# Path to the face landmarker model — accept common locations (models/ or face/)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_MODEL_PATHS = [
    os.path.join(_BASE_DIR, "models", "face_landmarker.task"),
    os.path.join(_BASE_DIR, "face", "face_landmarker.task"),
    os.path.join(_BASE_DIR, "face_landmarker.task"),
]

_MODEL_PATH = None
for _p in _CANDIDATE_MODEL_PATHS:
    if os.path.exists(_p):
        _MODEL_PATH = _p
        break

if _MODEL_PATH is None:
    # Default location (used in error message if missing)
    _MODEL_PATH = os.path.join(_BASE_DIR, "models", "face_landmarker.task")


class EyeDetector:
    """
    Detects eye state (open/closed) from a video frame using
    MediaPipe FaceLandmarker and the EAR metric.
    """

    def __init__(
        self,
        max_num_faces=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        ear_threshold=EAR_THRESHOLD,
    ):
        """
        Args:
            max_num_faces: Maximum number of faces to detect.
            min_detection_confidence: Minimum confidence for face detection.
            min_tracking_confidence: Minimum confidence for face tracking.
            ear_threshold: EAR value below which eyes are considered closed.
        """
        self.ear_threshold = ear_threshold

        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"Face landmarker model not found at: {_MODEL_PATH}\n"
                "Download it with:\n"
                "  python -c \"import urllib.request; "
                "urllib.request.urlretrieve("
                "'https://storage.googleapis.com/mediapipe-models/"
                "face_landmarker/face_landmarker/float16/latest/"
                "face_landmarker.task', 'models/face_landmarker.task')\""
            )

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )

        self._landmarker = FaceLandmarker.create_from_options(options)
        self._frame_timestamp_ms = 0

    def process(self, frame_rgb, frame_w, frame_h):
        """
        Process a single RGB frame and return eye state info.

        Args:
            frame_rgb: The video frame in RGB color space (numpy array).
            frame_w: Frame width in pixels.
            frame_h: Frame height in pixels.

        Returns:
            result (dict | None):
                If a face is detected:
                    {
                        "ear_left": float,
                        "ear_right": float,
                        "ear_avg": float,
                        "eyes_closed": bool,
                        "left_eye_points": [(x,y), ...],
                        "right_eye_points": [(x,y), ...],
                    }
                If no face is detected: None
        """
        # Create a MediaPipe Image from the numpy array
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb,
        )

        # Increment timestamp for VIDEO mode
        self._frame_timestamp_ms += 33  # ~30 FPS

        # Run face landmark detection
        result = self._landmarker.detect_for_video(mp_image, self._frame_timestamp_ms)

        if not result.face_landmarks or len(result.face_landmarks) == 0:
            return None

        # Use the first detected face — landmarks are NormalizedLandmark objects
        face_landmarks = result.face_landmarks[0]

        # Compute EAR for each eye
        ear_left, left_pts = compute_ear(
            face_landmarks, LEFT_EYE_INDICES, frame_w, frame_h
        )
        ear_right, right_pts = compute_ear(
            face_landmarks, RIGHT_EYE_INDICES, frame_w, frame_h
        )

        ear_avg = (ear_left + ear_right) / 2.0
        eyes_closed = ear_avg < self.ear_threshold

        return {
            "ear_left": ear_left,
            "ear_right": ear_right,
            "ear_avg": ear_avg,
            "eyes_closed": eyes_closed,
            "left_eye_points": left_pts,
            "right_eye_points": right_pts,
        }

    def close(self):
        """Release MediaPipe resources."""
        self._landmarker.close()