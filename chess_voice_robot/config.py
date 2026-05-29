"""
Application configuration — tune paths and display here.
"""

import os
import shutil

# ---------------------------------------------------------------------------
# Stockfish engine path
# Install: brew install stockfish  (macOS)  |  apt install stockfish  (Linux)
# Override with environment variable: STOCKFISH_PATH=/path/to/stockfish
# ---------------------------------------------------------------------------
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish") or "stockfish"

# How long Stockfish thinks per move (seconds)
STOCKFISH_SKILL_LEVEL = 10  # 0–20 (higher = stronger)
STOCKFISH_TIME_LIMIT = 0.5  # seconds per engine move

# Pause before the computer plays (feels like online chess)
ENGINE_MOVE_DELAY = 1.0  # seconds

# After invalid speech, ignore mic briefly (avoids echo + stale queue)
SPEECH_COOLDOWN_AFTER_INVALID = 1.0  # seconds

# ---------------------------------------------------------------------------
# GUI (pygame)
# ---------------------------------------------------------------------------
WINDOW_TITLE = "Voice Chess vs Stockfish"
SQUARE_SIZE = 72  # pixels per square
BOARD_SIZE = SQUARE_SIZE * 8
STATUS_BAR_HEIGHT = 64
WINDOW_WIDTH = BOARD_SIZE
WINDOW_HEIGHT = BOARD_SIZE + STATUS_BAR_HEIGHT

# Status bar / turn indicator (online-chess style)
COLOR_STATUS_BG = (45, 45, 48)
COLOR_STATUS_TEXT = (240, 240, 240)
COLOR_STATUS_SUB = (180, 180, 185)
COLOR_YOUR_TURN = (76, 175, 80)      # green — speak now
COLOR_OPPONENT_TURN = (255, 152, 0)  # orange — thinking
COLOR_WAIT = (120, 120, 125)
COLOR_INVALID = (229, 115, 115)
STATUS_FONT_SIZE = 20
STATUS_SUB_FONT_SIZE = 14

# Board colors
LIGHT_SQUARE = (240, 217, 181)  # cream
DARK_SQUARE = (181, 136, 99)    # brown
HIGHLIGHT_LAST_MOVE = (255, 255, 0, 80)  # yellow tint (RGBA)

# Label text on each square
LABEL_COLOR_LIGHT = (100, 80, 60)
LABEL_COLOR_DARK = (220, 200, 180)
LABEL_FONT_SIZE = 11
PIECE_FONT_SIZE = 48

# Unicode chess pieces (white / black)
PIECES_UNICODE = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

# ---------------------------------------------------------------------------
# Speech recognition
# ---------------------------------------------------------------------------
# Seconds to wait for microphone input before timing out
SPEECH_TIMEOUT = 5
SPEECH_PHRASE_LIMIT = 8  # max seconds per utterance

# ---------------------------------------------------------------------------
# UI messages (visual only — no voice)
# ---------------------------------------------------------------------------
ENGINE_THINKING_MESSAGE = "Opponent is thinking."
SPEAK_NOW_HINT = "Say a move, e.g. e2 e4 or e two e four"

# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
# Human plays white; Stockfish plays black
HUMAN_COLOR = "white"
