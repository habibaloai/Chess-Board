"""
Audio feedback — short tones only (no voice).
Invalid move: low buzz. Valid move: pleasant confirmation chime.
"""

import io
import math
import struct
import wave

import pygame

# Cached sounds
_invalid_sound = None
_valid_sound = None


def _ensure_mixer() -> None:
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)


def _make_tone_wav(frequency: float, duration: float, volume: float = 0.35) -> bytes:
    """Build a mono 16-bit WAV tone in memory."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = []
        for i in range(n_samples):
            t = i / sample_rate
            envelope = 1.0 - (i / n_samples) * 0.5
            value = int(
                32767 * volume * envelope * math.sin(2 * math.pi * frequency * t)
            )
            frames.append(struct.pack("<h", value))
        wav.writeframes(b"".join(frames))
    return buf.getvalue()


def _make_valid_move_wav() -> bytes:
    """Two-note success chime (C5 then E5)."""
    sample_rate = 44100
    notes = [(523.25, 0.12), (659.25, 0.18)]
    frames = []
    for freq, duration in notes:
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            envelope = 1.0 - (i / n_samples) * 0.4
            value = int(
                32767 * 0.28 * envelope * math.sin(2 * math.pi * freq * t)
            )
            frames.append(struct.pack("<h", value))
    buf = io.BytesIO()
    with wave.open(buf, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(frames))
    return buf.getvalue()


def _get_invalid_sound() -> pygame.mixer.Sound:
    global _invalid_sound
    if _invalid_sound is None:
        _ensure_mixer()
        _invalid_sound = pygame.mixer.Sound(buffer=_make_tone_wav(880.0, 0.25))
    return _invalid_sound


def _get_valid_sound() -> pygame.mixer.Sound:
    global _valid_sound
    if _valid_sound is None:
        _ensure_mixer()
        _valid_sound = pygame.mixer.Sound(buffer=_make_valid_move_wav())
    return _valid_sound


def _play(sound: pygame.mixer.Sound) -> None:
    try:
        sound.play()
    except Exception:
        print("\a", end="", flush=True)


def play_invalid_beep() -> None:
    """Low buzz when speech or move is invalid."""
    _play(_get_invalid_sound())


def play_valid_move() -> None:
    """Short chime when the player's move is accepted."""
    _play(_get_valid_sound())


# Backwards-compatible name used by controller
def announce_invalid_move() -> None:
    play_invalid_beep()
