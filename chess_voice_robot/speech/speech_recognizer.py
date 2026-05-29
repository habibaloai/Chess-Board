"""
Microphone speech recognition using the speech_recognition library.
Runs in a background thread; can be paused when the computer is thinking or after errors.
"""

import threading
import time
from typing import Callable, Optional

import speech_recognition as sr

from chess_voice_robot import config


class SpeechRecognizer:
    """
    Listens for chess move commands when not paused.
    Pausing prevents stale/echo utterances during engine moves and TTS feedback.
    """

    def __init__(self) -> None:
        self._recognizer = sr.Recognizer()
        self._microphone = sr.Microphone()
        self._running = False
        self._paused = True  # start paused until game says "your turn"
        self._thread: Optional[threading.Thread] = None
        self._pause_lock = threading.Lock()

        with self._microphone as source:
            print("[Speech] Calibrating microphone for ambient noise...")
            self._recognizer.adjust_for_ambient_noise(source, duration=1)
            print("[Speech] Ready.")

    def set_paused(self, paused: bool) -> None:
        """When paused, the mic loop idles and does not enqueue speech."""
        with self._pause_lock:
            self._paused = paused
        state = "paused" if paused else "listening"
        print(f"[Speech] Microphone {state}.")

    def is_paused(self) -> bool:
        with self._pause_lock:
            return self._paused

    def listen_once(self) -> Optional[str]:
        try:
            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=config.SPEECH_TIMEOUT,
                    phrase_time_limit=config.SPEECH_PHRASE_LIMIT,
                )
            text = self._recognizer.recognize_google(audio)
            print(f"[Speech] Heard: {text}")
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("[Speech] Could not understand audio.")
            return None
        except sr.RequestError as exc:
            print(f"[Speech] Recognition service error: {exc}")
            return None

    def start_listening(self, on_speech: Callable[[str], None]) -> None:
        if self._running:
            return
        self._running = True

        def _loop():
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
