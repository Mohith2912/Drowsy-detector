"""
alarm.py — Alarm manager using Pygame mixer.

Handles loading, playing (looped), and stopping the alarm sound.
Uses a dedicated thread-safe approach so the main CV loop stays responsive.
"""

import os
import pygame


class AlarmManager:
    """
    Manages a looping alarm sound via Pygame's mixer.
    Thread-safe: play/stop can be called from any thread.
    """

    def __init__(self, sound_path=None, volume=1.0):
        """
        Args:
            sound_path: Path to the .wav alarm file.
                        Defaults to sounds/alarm.wav next to this script.
            volume: Float 0.0–1.0 for alarm volume (1.0 = max).
        """
        if sound_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            sound_path = os.path.join(base_dir, "sounds", "alarm.wav")

        self._sound_path = sound_path
        self._volume = volume
        self._playing = False
        self._sound = None

        # Initialize Pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        self._load_sound()

    def _load_sound(self):
        """Load the alarm sound file."""
        if not os.path.exists(self._sound_path):
            print(f"[AlarmManager] WARNING: Sound file not found: {self._sound_path}")
            print("[AlarmManager] Generating a default alarm tone...")
            self._generate_default_alarm()

        try:
            self._sound = pygame.mixer.Sound(self._sound_path)
            self._sound.set_volume(self._volume)
        except Exception as e:
            print(f"[AlarmManager] ERROR loading sound: {e}")
            self._sound = None

    def _generate_default_alarm(self):
        """Generate a very loud, aggressive alarm .wav file."""
        import numpy as np
        import wave
        import struct

        os.makedirs(os.path.dirname(self._sound_path), exist_ok=True)

        sample_rate = 44100
        duration = 2.0  # seconds (will loop)

        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

        # Layer multiple piercing frequencies for maximum loudness
        signal = (
            1.0 * np.sin(2 * np.pi * 880 * t)      # A5 — base alarm tone
            + 0.8 * np.sin(2 * np.pi * 1320 * t)    # E6 — harsh fifth
            + 0.7 * np.sin(2 * np.pi * 1760 * t)    # A6 — octave up
            + 0.5 * np.sin(2 * np.pi * 2640 * t)    # E7 — very high piercing
            + 0.4 * np.sin(2 * np.pi * 3520 * t)    # A7 — ultra piercing
        )

        # Fast aggressive pulsing (6 Hz) — sharper attack than sine
        pulse = np.clip(np.sin(2 * np.pi * 6 * t) * 3.0, 0.0, 1.0)
        signal = signal * (0.3 + 0.7 * pulse)  # Never fully silent

        # Hard-clip to absolute max amplitude for maximum loudness
        signal = np.clip(signal, -1.0, 1.0)
        signal = signal / np.max(np.abs(signal))
        signal = (signal * 32767).astype(np.int16)

        # Write as stereo WAV (both channels at full blast)
        with wave.open(self._sound_path, "w") as wav_file:
            wav_file.setnchannels(2)       # Stereo
            wav_file.setsampwidth(2)       # 16-bit
            wav_file.setframerate(sample_rate)
            for sample in signal:
                s = int(sample)
                # Write same sample to left and right channels
                wav_file.writeframes(struct.pack("<hh", s, s))

        print(f"[AlarmManager] Loud alarm generated: {self._sound_path}")

    def play(self):
        """Start playing the alarm in an infinite loop (if not already playing)."""
        if self._playing or self._sound is None:
            return
        self._sound.play(loops=-1)  # -1 = infinite loop
        self._playing = True

    def stop(self):
        """Stop the alarm immediately."""
        if not self._playing or self._sound is None:
            return
        self._sound.stop()
        self._playing = False

    @property
    def is_playing(self):
        return self._playing

    def set_volume(self, volume):
        """Adjust alarm volume (0.0 – 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        if self._sound:
            self._sound.set_volume(self._volume)

    def cleanup(self):
        """Stop sound and quit Pygame mixer."""
        self.stop()
        pygame.mixer.quit()