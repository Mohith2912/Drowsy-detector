"""
main.py — AI Drowsiness Detection System

Real-time drowsiness detection using webcam, MediaPipe Face Mesh,
Eye Aspect Ratio (EAR) analysis, and Pygame alarm system.

Controls:
    Q / ESC   — Quit the application
    +/-       — Adjust EAR threshold
    R         — Reset drowsiness timer

Author: AI-Eyes Detection
"""

import sys
import time
import cv2
import numpy as np

from eye_detector import EyeDetector
from alarm import AlarmManager
from utils import (
    EAR_THRESHOLD,
    DROWSY_TIME_THRESHOLD,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    COLOR_WHITE,
    COLOR_CYAN,
    FPSCounter,
)

# ─── Window & Display Config ──────────────────────────────────────────────────
WINDOW_NAME = "AI Drowsiness Detection"
FRAME_WIDTH = 960
FRAME_HEIGHT = 540


def draw_eye_contour(frame, points, color, thickness=2):
    """Draw the eye contour as a closed polygon."""
    if len(points) < 3:
        return
    pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=thickness)
    for (x, y) in points:
        cv2.circle(frame, (x, y), 2, COLOR_CYAN, -1)


def draw_hud(frame, state, ear, fps, ear_threshold, closed_duration):
    """Draw the head-up display overlay with status information."""
    h, w = frame.shape[:2]

    # ── Semi-transparent top bar ──
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 80), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # ── Title ──
    cv2.putText(
        frame, "AI DROWSINESS DETECTION",
        (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_WHITE, 2
    )

    # ── FPS ──
    cv2.putText(
        frame, f"FPS: {fps:.0f}",
        (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_GREEN, 2
    )

    # ── Eye Openness (EAR mapped to 0-100%) ──
    openness_pct = int(max(0.0, min(100.0, (ear / 0.35) * 100.0)))
    ear_color = COLOR_GREEN if ear >= ear_threshold else COLOR_RED
    cv2.putText(
        frame, f"Eye Openness: {openness_pct}%",
        (15, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, ear_color, 2
    )

    # ── Status indicator ──
    if state == "DROWSY":
        # Flashing red alert
        flash = int(time.time() * 4) % 2 == 0
        status_color = COLOR_RED if flash else (0, 0, 180)
        status_text = f"!! DROWSY — {closed_duration:.1f}s !!"
        bg_color = (0, 0, 100)

        # Draw alert bar at bottom
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (0, h - 70), (w, h), bg_color, -1)
        cv2.addWeighted(overlay2, 0.6, frame, 0.4, 0, frame)

        cv2.putText(
            frame, status_text,
            (w // 2 - 200, h - 25), cv2.FONT_HERSHEY_SIMPLEX,
            1.0, status_color, 3
        )

    elif state == "EYES_CLOSED":
        status_color = COLOR_YELLOW
        status_text = f"Eyes Closed ({closed_duration:.1f}s)"

        cv2.putText(
            frame, status_text,
            (w // 2 - 150, h - 25), cv2.FONT_HERSHEY_SIMPLEX,
            0.8, status_color, 2
        )

    elif state == "AWAKE":
        status_color = COLOR_GREEN
        cv2.putText(
            frame, "AWAKE",
            (w - 140, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2
        )

    elif state == "NO_FACE":
        status_color = COLOR_YELLOW
        cv2.putText(
            frame, "No Face Detected",
            (w // 2 - 120, h // 2), cv2.FONT_HERSHEY_SIMPLEX,
            0.8, status_color, 2
        )

    # ── EAR threshold bar (visual) ──
    bar_x, bar_y, bar_w, bar_h = w - 50, 90, 20, 200
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), COLOR_WHITE, 1)

    # EAR fill (clamped 0–0.5 range mapped to bar)
    ear_clamped = max(0.0, min(0.5, ear))
    fill_h = int((ear_clamped / 0.5) * bar_h)
    fill_color = COLOR_GREEN if ear >= ear_threshold else COLOR_RED
    cv2.rectangle(
        frame,
        (bar_x + 2, bar_y + bar_h - fill_h),
        (bar_x + bar_w - 2, bar_y + bar_h),
        fill_color, -1
    )

    # Threshold line on bar
    thresh_y = bar_y + bar_h - int((ear_threshold / 0.5) * bar_h)
    cv2.line(frame, (bar_x - 5, thresh_y), (bar_x + bar_w + 5, thresh_y), COLOR_YELLOW, 2)


def draw_controls_help(frame):
    """Draw keyboard controls in the corner."""
    h = frame.shape[0]
    texts = [
        "Q/ESC: Quit",
        "+/-: Adjust threshold",
        "R: Reset timer",
    ]
    for i, txt in enumerate(texts):
        cv2.putText(
            frame, txt,
            (15, h - 15 - i * 22), cv2.FONT_HERSHEY_SIMPLEX,
            0.4, (150, 150, 150), 1
        )


def main():
    """Main application loop."""
    print("=" * 60)
    print("   AI DROWSINESS DETECTION SYSTEM")
    print("=" * 60)
    print()
    print("Initializing components...")

    # ── Initialize components ──
    detector = EyeDetector(ear_threshold=EAR_THRESHOLD)
    alarm = AlarmManager(volume=1.0)
    fps_counter = FPSCounter(window_size=30)
    ear_threshold = EAR_THRESHOLD

    print("[OK] Eye detector initialized (MediaPipe Face Mesh)")
    print("[OK] Alarm system initialized (Pygame)")

    # ── Open webcam ──
    print("[..] Opening webcam...")

    # Try multiple backends — set properties before reading, handle OpenCV crashes
    cap = None
    # DirectShow first on Windows — most reliable frame format
    backends = [("DirectShow", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF), ("Default", cv2.CAP_ANY)]
    for backend_name, backend_id in backends:
        print(f"[..] Trying {backend_name} backend...")
        attempt = cv2.VideoCapture(0, backend_id)
        if not attempt.isOpened():
            attempt.release()
            continue

        # Set resolution BEFORE first read to avoid format mismatch
        attempt.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        attempt.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        attempt.set(cv2.CAP_PROP_FPS, 30)

        # Try to read — wrap in try/except for OpenCV assertion errors
        try:
            ret, _ = attempt.read()
            if ret:
                cap = attempt
                print(f"[OK] Camera opened with {backend_name} backend")
                break
        except cv2.error:
            pass

        attempt.release()

    if cap is None:
        print("[X] ERROR: Could not open webcam with any backend!")
        print("    Make sure your camera is connected and not in use.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency

    # ── Warm up camera (discard initial frames for stable output) ──
    print("[..] Warming up camera...")
    warmup_ok = False
    for i in range(20):
        try:
            ret, _ = cap.read()
            if ret:
                warmup_ok = True
                break
        except cv2.error:
            pass
        time.sleep(0.1)
    if not warmup_ok:
        print("[X] ERROR: Camera opened but cannot read frames!")
        print("    Try closing other apps that use the camera.")
        cap.release()
        sys.exit(1)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[OK] Webcam ready ({actual_w}x{actual_h})")

    # ── Set permanent fullscreen ──
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
    )
    print("[OK] Fullscreen mode enabled")
    print()
    print("Press 'Q' or 'ESC' to quit.")
    print("-" * 60)

    # ── State tracking ──
    eyes_closed_start = None   # Timestamp when eyes first closed
    is_alarm_active = False
    consecutive_failures = 0

    try:
        while True:
            try:
                ret, frame = cap.read()
            except cv2.error:
                ret = False
                frame = None
            if not ret:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    print("[!] Too many consecutive frame read failures.")
                    break
                time.sleep(0.01)
                continue
            consecutive_failures = 0

            fps_counter.tick()

            # Flip horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            # Convert BGR → RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False  # Performance optimization

            # ── Eye detection ──
            result = detector.process(frame_rgb, w, h)

            if result is None:
                # No face detected — reset drowsiness state
                state = "NO_FACE"
                current_ear = 0.0
                closed_duration = 0.0

                if is_alarm_active:
                    alarm.stop()
                    is_alarm_active = False
                eyes_closed_start = None

            else:
                current_ear = result["ear_avg"]

                # Draw eye landmarks
                eye_color = COLOR_GREEN if not result["eyes_closed"] else COLOR_RED
                draw_eye_contour(frame, result["left_eye_points"], eye_color)
                draw_eye_contour(frame, result["right_eye_points"], eye_color)

                if result["eyes_closed"]:
                    # Eyes are closed
                    if eyes_closed_start is None:
                        eyes_closed_start = time.time()

                    closed_duration = time.time() - eyes_closed_start

                    if closed_duration >= DROWSY_TIME_THRESHOLD:
                        # ─── DROWSY! ───
                        state = "DROWSY"
                        if not is_alarm_active:
                            alarm.play()
                            is_alarm_active = True
                            print(f"[!! ALARM] Drowsiness detected! "
                                  f"Eyes closed for {closed_duration:.1f}s")
                    else:
                        # Eyes closed but not yet drowsy (could be a blink)
                        state = "EYES_CLOSED"

                else:
                    # Eyes are open
                    state = "AWAKE"
                    closed_duration = 0.0
                    eyes_closed_start = None

                    if is_alarm_active:
                        alarm.stop()
                        is_alarm_active = False
                        print("[OK] Eyes reopened -- alarm stopped.")

            # ── Draw HUD ──
            draw_hud(frame, state, current_ear, fps_counter.fps,
                     ear_threshold, closed_duration)
            draw_controls_help(frame)

            # ── Display ──
            cv2.imshow(WINDOW_NAME, frame)

            # ── Handle keyboard input ──
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:  # Q or ESC
                print("\n[->] Shutting down...")
                break

            elif key == ord("+") or key == ord("="):
                ear_threshold = min(0.40, ear_threshold + 0.01)
                detector.ear_threshold = ear_threshold
                print(f"[*] EAR threshold -> {ear_threshold:.2f}")

            elif key == ord("-") or key == ord("_"):
                ear_threshold = max(0.10, ear_threshold - 0.01)
                detector.ear_threshold = ear_threshold
                print(f"[*] EAR threshold -> {ear_threshold:.2f}")

            elif key == ord("r"):
                eyes_closed_start = None
                if is_alarm_active:
                    alarm.stop()
                    is_alarm_active = False
                print("[*] Timer reset.")

    except KeyboardInterrupt:
        print("\n[->] Interrupted by user.")

    finally:
        # ── Cleanup ──
        print("[..] Releasing resources...")
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        alarm.cleanup()
        print("[OK] Done. Stay safe!")


if __name__ == "__main__":
    main()