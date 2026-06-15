# AI Drowsiness Detection System 🚗💤

Real-time AI-powered drowsiness detection software that monitors eye state using your webcam and triggers a loud alarm if you start falling asleep.

## Features

- **Real-time webcam detection** — Opens your camera automatically
- **Face & eye tracking** — MediaPipe Face Mesh with 468+ landmarks
- **Eye Aspect Ratio (EAR)** — Continuous eye-openness measurement
- **Smart blink filtering** — Ignores normal blinks (< 3 seconds)
- **Loud alarm system** — Continuous piercing alarm when drowsy
- **Instant alarm stop** — Alarm stops the moment eyes reopen
- **Live HUD overlay** — EAR bar, FPS counter, status display
- **CPU-optimized** — Runs smoothly without GPU

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Face Detection | MediaPipe Face Mesh |
| Video Processing | OpenCV |
| Math/EAR | NumPy |
| Audio Alarm | Pygame |
| Language | Python 3.8+ |

## Project Structure

```
AI-Eyes Detection-Vidit/
├── main.py              # Main application loop & HUD rendering
├── eye_detector.py      # MediaPipe Face Mesh eye detection
├── alarm.py             # Pygame alarm manager with auto-generation
├── utils.py             # EAR computation, constants, FPS counter
├── requirements.txt     # Python dependencies
├── sounds/
│   └── alarm.wav        # Alarm sound (auto-generated if missing)
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `Q` / `ESC` | Quit the application |
| `+` / `=` | Increase EAR threshold |
| `-` / `_` | Decrease EAR threshold |
| `R` | Reset drowsiness timer |

## How It Works

1. **Captures** webcam frames in real-time
2. **Detects** face landmarks using MediaPipe Face Mesh (468 points)
3. **Extracts** 6 key eye landmarks per eye
4. **Computes** Eye Aspect Ratio (EAR) — ratio of eye height to width
5. **Monitors** if EAR stays below threshold for > 3 seconds
6. **Triggers** alarm on drowsiness, stops when eyes reopen

### EAR Formula

```
EAR = (||p2 - p6|| + ||p3 - p5||) / (2 × ||p1 - p4||)
```

- **EAR ≈ 0.25–0.30** → Eyes open
- **EAR < 0.21** → Eyes closed
- **Eyes closed > 3s** → DROWSY ALARM!

## License

MIT License