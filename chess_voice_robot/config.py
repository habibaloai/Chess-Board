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
STOCKFISH_TIME_LIMIT = 2  # seconds per engine move

# Pause before the computer plays (feels like online chess)
ENGINE_MOVE_DELAY =2.0  # seconds

# After invalid speech, ignore mic briefly (avoids echo + stale queue)
SPEECH_COOLDOWN_AFTER_INVALID = 2.0  # seconds

# ---------------------------------------------------------------------------
# GUI (pygame)
# ---------------------------------------------------------------------------
WINDOW_TITLE = "Wizard Chess"
SQUARE_SIZE = 90  # pixels per square
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
COLOR_SELECTED_SQUARE = (255, 235, 59, 100)   # yellow tint
COLOR_LEGAL_MOVE = (76, 175, 80, 140)         # green tint / dot
COLOR_ILLEGAL_FLASH = (211, 47, 47, 180)      # red tint
COLOR_INPUT_TOGGLE_ON = (76, 175, 80)
COLOR_INPUT_TOGGLE_OFF = (90, 90, 95)
COLOR_ESTOP = (211, 47, 47)
COLOR_ESTOP_PRESSED = (183, 28, 28)
COLOR_ESTOP_TEXT = (255, 255, 255)
ESTOP_BUTTON_WIDTH = 52
ESTOP_BUTTON_HEIGHT = 28
INPUT_TOGGLE_WIDTH = 64
INPUT_TOGGLE_HEIGHT = 28
MIC_BUTTON_SIZE = 44
MIC_HIT_PADDING = 10
STATUS_FONT_SIZE = 20
STATUS_SUB_FONT_SIZE = 14
ESTOP_FONT_SIZE = 13

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
# Speech recognition (faster-whisper — local, offline)
# Model sizes: tiny, base, small, medium, large-v3 (larger = more accurate, slower)
# Override: WHISPER_MODEL=small WHISPER_DEVICE=cpu
# ---------------------------------------------------------------------------
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_LANGUAGE = "en"

SPEECH_TIMEOUT = 5          # seconds to wait for speech to start
SPEECH_PHRASE_LIMIT = 8     # max seconds per utterance
SPEECH_PAUSE_THRESHOLD = 0.8  # seconds of silence to end phrase
SPEECH_ENERGY_THRESHOLD = 300  # initial RMS threshold (auto-calibrated on startup)

# ---------------------------------------------------------------------------
# UI messages (visual only — no voice)
# ---------------------------------------------------------------------------
ENGINE_THINKING_MESSAGE = "Opponent is thinking."
ROBOT_MOVING_MESSAGE = "Robot is moving — please wait."
SPEAK_NOW_HINT = "Speak a move, or click 🎤 / press M for mouse mode"
MOUSE_MODE_HINT = "Mic off — click a piece, then its destination (M toggles voice)"
INVALID_MOVE_FLASH_MS = 600

# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
# Human plays white; Stockfish plays black
HUMAN_COLOR = "white"

# ---------------------------------------------------------------------------
# Physical robot (GRBL / Arduino)
# Override port with environment variable: SERIAL_PORT=/dev/tty.usbmodemXXXX
# Set USE_ROBOT_SIMULATOR=1 to test without hardware
# ---------------------------------------------------------------------------
USE_ROBOT_SIMULATOR = os.environ.get("USE_ROBOT_SIMULATOR", "0") == "1"

SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/tty.usbmodem141011")
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 1.0
SERIAL_OPEN_DELAY = 2.0  # seconds — wait for Arduino reset after opening port

GRBL_UNLOCK_ON_START = True
# After serial open the Arduino resets — send G92 so work zero matches the park position.
# Park the carriage on the bottom-left corner of the board before starting.
GRBL_ZERO_ON_START = os.environ.get("GRBL_ZERO_ON_START", "1") == "1"
GRBL_WAIT_FOR_OK = True
GRBL_RESPONSE_TIMEOUT = 5.0  # seconds
GRBL_WAIT_FOR_IDLE = True    # poll ? until GRBL reports Idle (motors stopped)
GRBL_IDLE_TIMEOUT = 120.0    # seconds — max wait per motion segment
GRBL_IDLE_POLL_INTERVAL = 0.05  # seconds between ? status polls

# Board geometry (millimetres)
# Work zero (G92) is the bottom-left corner of the board — park there before starting.
# Play area (board lines, edge to edge): 40 cm across 8 squares.
PLAY_AREA_MM = 400.0
SQUARE_SIZE_MM = PLAY_AREA_MM / 8.0  # 50 mm centre-to-centre

# Board coordinate origin (a1 centre) — unchanged square math; see ORIGIN_OFFSET below.
BOARD_ORIGIN_X_MM = 0.0
BOARD_ORIGIN_Y_MM = 0.0
HOME_WORK_X_MM = 0.0
HOME_WORK_Y_MM = 0.0

# Shift from board coordinates to physical work coordinates (a1 centre is +2.5 cm X/Y).
ORIGIN_OFFSET_X_MM = 25.0
ORIGIN_OFFSET_Y_MM = 25.0

X_AXIS_DIRECTION = 1      # 1 or -1 — flip if X moves the wrong way
Y_AXIS_DIRECTION = 1      # 1 or -1 — flip if Y moves the wrong way

# Motion tuning
MOVE_FEED_RATE = 0        # mm/min — 0 lets GRBL use its default
MOVE_SETTLE_TIME = 0.5    # seconds to wait after each G0 command