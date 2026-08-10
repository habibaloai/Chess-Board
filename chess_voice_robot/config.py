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
# GUI (pygame) — Wizard Chess theme
# ---------------------------------------------------------------------------
WINDOW_TITLE = "Wizard Chess"
SQUARE_SIZE = 90  # default / reference square size (pixels); board scales at runtime
BOARD_SIZE = SQUARE_SIZE * 8
STATUS_BAR_HEIGHT = 108
WINDOW_BOARD_MARGIN = 80
WINDOW_WIDTH = BOARD_SIZE + WINDOW_BOARD_MARGIN * 2
WINDOW_HEIGHT = BOARD_SIZE + STATUS_BAR_HEIGHT + WINDOW_BOARD_MARGIN
BACKGROUND_IMAGE = os.path.join(
    os.path.dirname(__file__), "ui", "assets", "wizard_scene.png"
)
LOADING_SCREEN_IMAGE = BACKGROUND_IMAGE  # same art — seamless loading → gameplay
LOADING_SCREEN_SECONDS = 4.0
BOARD_FADE_IN_SECONDS = 1.4
# Fit the board inside available space, then shrink slightly (keeps it square).
BOARD_SCALE = 0.86
_SOUND_DIR = os.path.join(os.path.dirname(__file__), "ui", "sound")
LOADING_SCREEN_AUDIO = os.path.join(_SOUND_DIR, "loading screen audio.mp3")
BACKGROUND_MUSIC = os.path.join(
    _SOUND_DIR,
    "hitslab-magic-mystery-harry-potter-music-320643.mp3",
)
BACKGROUND_MUSIC_VOLUME = 0.45  # loading + default gameplay bed
# Subtle reduction on the game screen (~12%) so narration stays clear.
BACKGROUND_MUSIC_VOLUME_GAME = round(BACKGROUND_MUSIC_VOLUME * 0.88, 3)  # ≈ 0.396
NARRATOR_BOARD_AWAITS = os.path.join(_SOUND_DIR, "the board awaits.mp3")
NARRATOR_FIRST_MOVE = os.path.join(_SOUND_DIR, "player makes first move.mp3")
NARRATOR_PLAYERS_TURN = os.path.join(_SOUND_DIR, "player's turn.mp3")
NARRATOR_OPPOSING_STIR = os.path.join(_SOUND_DIR, "the opposing pieces stir.mp3")
NARRATOR_INVALID_MOVE = os.path.join(_SOUND_DIR, "invalid move.mp3")
NARRATOR_PIECE_FALLEN = os.path.join(_SOUND_DIR, "piece fallen.mp3")
NARRATOR_TAKES_TOO_LONG = os.path.join(_SOUND_DIR, "player takes too long.mp3")
NARRATOR_PLAYER_CHECKMATE = os.path.join(_SOUND_DIR, "player checkmate.mp3")
NARRATOR_OPPONENT_CHECKMATE = os.path.join(_SOUND_DIR, "opponent checkmate.mp3")
NARRATOR_PLAYER_WINS = os.path.join(_SOUND_DIR, "player wins.mp3")
NARRATOR_OPPONENT_WINS = os.path.join(_SOUND_DIR, "oponnent wins.mp3")
NARRATOR_VOLUME = 0.95
PLAYER_TURN_TIMEOUT_SECONDS = 20.0

# --- Palette (RGB / RGBA) ---------------------------------------------------
# Dark shadows
THEME_SHADOW = (11, 13, 15)          # #0B0D0F
THEME_SHADOW_MID = (21, 23, 25)      # #151719
THEME_SHADOW_LIFT = (32, 35, 39)     # #202327
# Ancient stone
THEME_STONE = (59, 58, 54)           # #3B3A36
THEME_STONE_MID = (85, 80, 71)       # #555047
THEME_STONE_LIGHT = (115, 107, 94)   # #736B5E
# Warm parchment
THEME_PARCHMENT = (214, 197, 160)    # #D6C5A0
THEME_PARCHMENT_DIM = (191, 167, 122)  # #BFA77A
# Antique gold
THEME_GOLD = (184, 155, 94)          # #B89B5E
THEME_GOLD_BRIGHT = (208, 179, 106)  # #D0B36A
THEME_GOLD_DARK = (140, 115, 63)     # #8C733F
# Dark burgundy
THEME_BURGUNDY = (84, 31, 38)        # #541F26
THEME_BURGUNDY_LIGHT = (114, 43, 53)  # #722B35
# Deep magical blue
THEME_BLUE = (27, 40, 56)            # #1B2838
THEME_BLUE_LIGHT = (38, 59, 80)      # #263B50

# Status bar (translucent stone panel — not bright green/red fills)
COLOR_STATUS_BG = (*THEME_SHADOW, 210)
COLOR_STATUS_BORDER = THEME_GOLD_DARK
COLOR_STATUS_TEXT = THEME_PARCHMENT
COLOR_STATUS_SUB = THEME_PARCHMENT_DIM
COLOR_YOUR_TURN = THEME_GOLD
COLOR_OPPONENT_TURN = THEME_PARCHMENT_DIM
COLOR_WAIT = THEME_STONE_LIGHT
COLOR_INVALID = THEME_BURGUNDY_LIGHT
COLOR_VICTORY = THEME_GOLD_BRIGHT
COLOR_CHECK = THEME_BURGUNDY_LIGHT

# Board squares — muted stone
LIGHT_SQUARE = (138, 129, 115)       # #8A8173
DARK_SQUARE = (52, 53, 54)           # #343536
BOARD_FRAME = THEME_GOLD_DARK
BOARD_FRAME_INNER = THEME_STONE
BOARD_SHADOW = (0, 0, 0, 90)

# Highlights (RGBA overlays)
COLOR_SELECTED_SQUARE = (*THEME_GOLD, 110)
COLOR_LEGAL_MOVE = (*THEME_GOLD_BRIGHT, 90)
COLOR_LEGAL_CAPTURE = (*THEME_BURGUNDY_LIGHT, 140)
COLOR_ILLEGAL_FLASH = (*THEME_BURGUNDY, 160)
HIGHLIGHT_LAST_MOVE = (*THEME_PARCHMENT, 70)

# Controls
COLOR_INPUT_TOGGLE_ON = THEME_GOLD_DARK
COLOR_INPUT_TOGGLE_OFF = THEME_SHADOW_LIFT
COLOR_BUTTON_BG = (*THEME_SHADOW_MID, 220)
COLOR_BUTTON_BORDER = THEME_GOLD_DARK
COLOR_BUTTON_HOVER = THEME_GOLD
COLOR_ESTOP = THEME_BURGUNDY
COLOR_ESTOP_PRESSED = THEME_BURGUNDY_LIGHT
COLOR_ESTOP_TEXT = THEME_PARCHMENT
COLOR_ESTOP_BORDER = THEME_GOLD_DARK

ESTOP_BUTTON_WIDTH = 52
ESTOP_BUTTON_HEIGHT = 52
INPUT_TOGGLE_WIDTH = 64
INPUT_TOGGLE_HEIGHT = 28
MIC_BUTTON_SIZE = 52
MIC_HIT_PADDING = 10
STATUS_FONT_SIZE = 24
STATUS_SUB_FONT_SIZE = 16
ESTOP_FONT_SIZE = 12

# Label text on each square
LABEL_COLOR_LIGHT = (60, 55, 48)
LABEL_COLOR_DARK = THEME_PARCHMENT_DIM
LABEL_FONT_SIZE = 11
PIECE_FONT_SIZE = 48
PIECE_COLOR_LIGHT = (235, 225, 205)
PIECE_COLOR_DARK = (18, 16, 14)
PIECE_OUTLINE = (0, 0, 0)

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
# UI messages (visual only — no voice / no SFX)
# ---------------------------------------------------------------------------
ENGINE_THINKING_MESSAGE = "Your opponent is considering their move…"
ROBOT_MOVING_MESSAGE = "The pieces stir upon the board — please wait."
SPEAK_NOW_HINT = "Speak a move, or silence the mic (🎤 / M) for mouse play"
MOUSE_MODE_HINT = "Mic silenced — click a piece, then its destination (M restores voice)"
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