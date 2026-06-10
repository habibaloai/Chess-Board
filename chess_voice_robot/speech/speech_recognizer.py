"""
Microphone speech recognition using faster-whisper (local, offline).
Runs in a background thread; can be paused when the computer is thinking or after errors.
"""

import math
import struct
import threading
import time
from typing import Callable, Optional

import numpy as np
import pyaudio
from faster_whisper import WhisperModel

from chess_voice_robot import config


class _MicrophoneRecorder:
    """Capture a single spoken phrase from the default microphone."""

    RATE = 16000
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1

    def __init__(self) -> None:
        self._pa = pyaudio.PyAudio()
        self._energy_threshold = config.SPEECH_ENERGY_THRESHOLD

    def close(self) -> None:
        self._pa.terminate()

    @staticmethod
    def _rms(frame: bytes) -> float:
        count = len(frame) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"{count}h", frame)
        return math.sqrt(sum(s * s for s in shorts) / count)

    def calibrate(self, duration: float = 1.0) -> None:
        """Set energy threshold from ambient noise level."""
        stream = self._pa.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
        )
        try:
            samples = []
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                samples.append(self._rms(data))
            ambient = sum(samples) / len(samples) if samples else 300.0
            self._energy_threshold = max(ambient * 1.8, 200.0)
        finally:
            stream.stop_stream()
            stream.close()

    def record_phrase(
        self,
        timeout: float,
        phrase_limit: float,
    ) -> Optional[np.ndarray]:
        """Wait for speech, then record until silence or phrase_limit."""
        stream = self._pa.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
        )
        try:
            frames: list[bytes] = []
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                if self._rms(data) >= self._energy_threshold:
                    frames.append(data)
                    break
            else:
                return None

            pause_chunks = int(config.SPEECH_PAUSE_THRESHOLD * self.RATE / self.CHUNK)
            silent_run = 0
            start = time.monotonic()

            while time.monotonic() - start < phrase_limit:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                if self._rms(data) < self._energy_threshold:
                    silent_run += 1
                    if silent_run >= pause_chunks:
                        break
                else:
                    silent_run = 0

            if not frames:
                return None
            raw = b"".join(frames)
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        finally:
            stream.stop_stream()
            stream.close()


class SpeechRecognizer:
    """
    Listens for chess move commands when not paused.
    Uses faster-whisper for local transcription (no internet required).
    """

    def __init__(self) -> None:
        self._running = False
        self._paused = True
        self._thread: Optional[threading.Thread] = None
        self._pause_lock = threading.Lock()
        self._mic = _MicrophoneRecorder()

        self._model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        self._mic.calibrate(duration=1.0)

    def set_paused(self, paused: bool) -> None:
        """When paused, the mic loop idles and does not enqueue speech."""
        with self._pause_lock:
            self._paused = paused

    def is_paused(self) -> bool:
        with self._pause_lock:
            return self._paused

    def _transcribe(self, audio: np.ndarray) -> Optional[str]:
        segments, _ = self._model.transcribe(
            audio,
            language=config.WHISPER_LANGUAGE,
            vad_filter=True,
            beam_size=5,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text if text else None

    def listen_once(self) -> Optional[str]:
        try:
            audio = self._mic.record_phrase(
                timeout=config.SPEECH_TIMEOUT,
                phrase_limit=config.SPEECH_PHRASE_LIMIT,
            )
            if audio is None:
                return None

            text = self._transcribe(audio)
            if not text:
                return None

            print(text)
            return text
        except OSError:
            return None
        except Exception:
            return None

    def start_listening(self, on_speech: Callable[[str], None]) -> None:
        if self._running:
            return
        self._running = True

        def _loop() -> None:
            while self._running:
                if self.is_paused():
                    time.sleep(0.05)
                    continue
                text = self.listen_once()
                if text and not self.is_paused():
                    on_speech(text)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._mic.close()
