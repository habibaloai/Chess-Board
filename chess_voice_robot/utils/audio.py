"""
Audio — continuous looping background music + loading VO + narrator clips.

Background music uses a reserved mixer channel (not pygame.mixer.music) so
screen changes and other Sound clips cannot pause or restart the theme.

SFX move beeps remain disabled. Narration is driven only by game-state
transitions in the controller (never by redraw/resize).
"""

from __future__ import annotations

import os
from collections import deque
from typing import Deque, Optional

import pygame

from chess_voice_robot import config

_MUSIC_CHANNEL_ID = 0

_bgm_sound: Optional[pygame.mixer.Sound] = None
_bgm_channel: Optional[pygame.mixer.Channel] = None
_music_path: str | None = None
_music_volume = float(config.BACKGROUND_MUSIC_VOLUME)

_sound_cache: dict[str, pygame.mixer.Sound] = {}
_narration_queue: Deque[str] = deque()
_narration_channel: Optional[pygame.mixer.Channel] = None
_loading_channel: Optional[pygame.mixer.Channel] = None
_playing_path: Optional[str] = None
_game_over_lock = False


def _ensure_mixer() -> bool:
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        # Re-apply even if pygame.init() already started the mixer.
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(1)
        return True
    except pygame.error:
        return False


def _music_busy() -> bool:
    return _bgm_channel is not None and _bgm_channel.get_busy()


def _apply_music_volume() -> None:
    if _bgm_channel is None:
        return
    try:
        _bgm_channel.set_volume(max(0.0, min(1.0, _music_volume)))
    except pygame.error:
        pass


def start_background_music() -> None:
    """Start (or keep) the looping theme on a reserved channel."""
    global _bgm_sound, _bgm_channel, _music_path, _music_volume
    path = config.BACKGROUND_MUSIC
    if not os.path.isfile(path):
        print(f"[Audio] music not found: {path}", flush=True)
        return
    if not _ensure_mixer():
        print("[Audio] could not initialize mixer; skipping music", flush=True)
        return

    try:
        if _bgm_sound is None or _music_path != path:
            _bgm_sound = pygame.mixer.Sound(path)
            _music_path = path

        if _bgm_channel is None:
            _bgm_channel = pygame.mixer.Channel(_MUSIC_CHANNEL_ID)

        # Already playing — only unpause / keep volume. Never restart or reset level.
        if _bgm_channel.get_busy():
            try:
                _bgm_channel.unpause()
            except pygame.error:
                pass
            _apply_music_volume()
            return

        _music_volume = float(config.BACKGROUND_MUSIC_VOLUME)
        _bgm_channel.play(_bgm_sound, loops=-1)
        _apply_music_volume()
    except pygame.error as exc:
        print(f"[Audio] failed to play music: {exc}", flush=True)


def play_loading_screen_audio() -> float:
    """Play the loading VO once over the theme. Returns duration in seconds (0 if missing)."""
    global _loading_channel
    path = config.LOADING_SCREEN_AUDIO
    if not os.path.isfile(path):
        print(f"[Audio] loading screen audio not found: {path}", flush=True)
        return 0.0
    if not _ensure_mixer():
        return 0.0
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(float(config.NARRATOR_VOLUME))
        if _loading_channel is not None:
            try:
                _loading_channel.stop()
            except pygame.error:
                pass
        _loading_channel = sound.play(loops=0)
        # Keep BGM going under the VO — never touch the music channel here.
        return float(sound.get_length())
    except pygame.error as exc:
        print(f"[Audio] failed to play loading screen audio: {exc}", flush=True)
        _loading_channel = None
        return 0.0


def loading_screen_audio_busy() -> bool:
    return _loading_channel is not None and _loading_channel.get_busy()


def set_gameplay_music_volume() -> None:
    """Slightly quieter music on the game screen so narration stays clear.

    Only adjusts volume — never stops, pauses, or restarts the stream.
    """
    global _music_volume
    _music_volume = float(config.BACKGROUND_MUSIC_VOLUME_GAME)
    if _music_busy():
        try:
            _bgm_channel.unpause()
        except pygame.error:
            pass
        _apply_music_volume()
    else:
        start_background_music()
        _music_volume = float(config.BACKGROUND_MUSIC_VOLUME_GAME)
        _apply_music_volume()


def ensure_background_music() -> None:
    """Keep the theme playing across loading → gameplay without restarting."""
    if not _ensure_mixer():
        return
    if _music_busy():
        try:
            _bgm_channel.unpause()
        except pygame.error:
            pass
        _apply_music_volume()
        return
    start_background_music()


def stop_background_music() -> None:
    """Stop music only on application shutdown."""
    global _bgm_sound, _bgm_channel, _music_path
    if _bgm_channel is not None:
        try:
            _bgm_channel.stop()
        except pygame.error:
            pass
    _bgm_channel = None
    _bgm_sound = None
    _music_path = None


def _get_sound(path: str) -> Optional[pygame.mixer.Sound]:
    if not os.path.isfile(path):
        print(f"[Audio] narrator clip missing: {path}", flush=True)
        return None
    if not _ensure_mixer():
        return None
    cached = _sound_cache.get(path)
    if cached is not None:
        return cached
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(float(config.NARRATOR_VOLUME))
        _sound_cache[path] = sound
        return sound
    except pygame.error as exc:
        print(f"[Audio] failed to load narrator clip {path}: {exc}", flush=True)
        return None


def _channel_busy() -> bool:
    return _narration_channel is not None and _narration_channel.get_busy()


def tick_narrator() -> None:
    """Advance the narration queue; call once per frame from the game loop."""
    global _narration_channel, _playing_path
    if _channel_busy():
        return
    _playing_path = None
    _narration_channel = None
    if not _narration_queue:
        return
    path = _narration_queue.popleft()
    sound = _get_sound(path)
    if sound is None:
        return
    try:
        _narration_channel = sound.play()
        _playing_path = path
    except pygame.error as exc:
        print(f"[Audio] narrator play failed: {exc}", flush=True)
        _narration_channel = None
        _playing_path = None


def narrator_busy() -> bool:
    return _channel_busy() or bool(_narration_queue)


def clear_narration(*, stop_current: bool = True) -> None:
    """Drop queued clips; optionally halt the clip currently playing."""
    global _narration_channel, _playing_path
    _narration_queue.clear()
    if stop_current and _narration_channel is not None:
        try:
            _narration_channel.stop()
        except pygame.error:
            pass
        _narration_channel = None
        _playing_path = None


def reset_narrator_session() -> None:
    """Reset session lock for a new game."""
    global _game_over_lock
    _game_over_lock = False
    clear_narration(stop_current=True)


def _enqueue(path: str, *, bypass_game_over: bool = False) -> None:
    if _game_over_lock and not bypass_game_over:
        return
    if path in _narration_queue:
        return
    if _playing_path == path and _channel_busy():
        return
    _narration_queue.append(path)
    tick_narrator()


def queue_game_intro() -> None:
    """Once per new game: board awaits → first-move prompt (no overlap)."""
    global _game_over_lock
    _game_over_lock = False
    clear_narration(stop_current=True)
    _enqueue(config.NARRATOR_BOARD_AWAITS)
    _enqueue(config.NARRATOR_FIRST_MOVE)


def play_players_turn() -> None:
    _enqueue(config.NARRATOR_PLAYERS_TURN)


def play_opposing_stir() -> None:
    _enqueue(config.NARRATOR_OPPOSING_STIR)


def play_invalid_move() -> None:
    """Illegal attempt — ignore repeats while the same clip is already active."""
    if _game_over_lock:
        return
    if _playing_path == config.NARRATOR_INVALID_MOVE and _channel_busy():
        return
    if config.NARRATOR_INVALID_MOVE in _narration_queue:
        return
    _enqueue(config.NARRATOR_INVALID_MOVE)


def play_piece_fallen() -> None:
    _enqueue(config.NARRATOR_PIECE_FALLEN)


def play_takes_too_long() -> None:
    _enqueue(config.NARRATOR_TAKES_TOO_LONG)


def play_player_checkmate() -> None:
    """Player's king is threatened (in check)."""
    _enqueue(config.NARRATOR_PLAYER_CHECKMATE)


def play_opponent_checkmate() -> None:
    """Opponent's king is threatened (in check)."""
    _enqueue(config.NARRATOR_OPPONENT_CHECKMATE)


def play_player_wins() -> None:
    """Human checkmates the AI — king 'dies'; game over."""
    global _game_over_lock
    _game_over_lock = True
    clear_narration(stop_current=True)
    _enqueue(config.NARRATOR_PLAYER_WINS, bypass_game_over=True)


def play_opponent_wins() -> None:
    """AI checkmates the human — king 'dies'; game over."""
    global _game_over_lock
    _game_over_lock = True
    clear_narration(stop_current=True)
    _enqueue(config.NARRATOR_OPPONENT_WINS, bypass_game_over=True)


def play_invalid_beep() -> None:
    play_invalid_move()


def play_valid_move() -> None:
    return


def announce_invalid_move() -> None:
    play_invalid_move()
