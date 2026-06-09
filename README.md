# Voice-Controlled Chess (vs Stockfish)

Desktop chess where you **speak moves**, see a **live pygame board**, and play against **Stockfish**. Architecture is modular so a **physical chess robot** can plug in later without changing game logic.

## Features

- Voice input → UCI moves (`e2e4`) via natural speech ("e two e four", "move e2 to e4", "e2 e4")
- Full rules via **python-chess** (castling, en passant, promotion)
- Pygame board with **square labels** (a1–h8) and Unicode pieces
- **Stockfish** replies after each valid move
- Invalid input: error beep + auto re-listen; valid move: short success chime (no voice)
- **Physical robot** via GRBL/Arduino (`SerialRobot`) or **simulator** for testing without hardware

## Project layout

```
chess_voice_robot/
├── main.py
├── config.py
├── speech/speech_recognizer.py
├── chess_engine/game.py
├── ai/stockfish_engine.py
├── ui/board_gui.py
├── core/controller.py
├── robot/interface.py, serial_robot.py, simulator.py
└── utils/audio.py, move_parser.py
```

## Setup

### 1. Python 3.10+

```bash
cd /Users/habiba/Desktop/Chess-board
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. PyAudio (microphone)

**macOS:**

```bash
brew install portaudio
pip install PyAudio
```

### 3. Stockfish

**macOS:**

```bash
brew install stockfish
```

**Linux:**

```bash
sudo apt install stockfish
```

Optional custom path:

```bash
export STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

### 4. Microphone & internet

Speech uses Google Web Speech API (`speech_recognition`) — **internet required**.

## Run

Always start from the project root with the virtual environment active:

```bash
cd /Users/habiba/Desktop/Chess-board
source venv/bin/activate
```

### Without Arduino (simulator — virtual board only)

Use this when the Arduino is unplugged or you only want to test speech, chess rules, and the GUI. Robot moves are printed to the terminal instead of driving motors.

```bash
cd /Users/habiba/Desktop/Chess-board
source venv/bin/activate
USE_ROBOT_SIMULATOR=1 python -m chess_voice_robot.main
```

You should see `[Robot] Using simulator (no hardware).` in the terminal.

### With Arduino connected (real motors)

1. Plug in the Arduino running **GRBL** firmware.
2. Close **UGS** or any other app using the serial port.
3. Set the correct port in `chess_voice_robot/config.py` (`SERIAL_PORT`) or pass it at runtime:

```bash
# Default port from config.py
cd /Users/habiba/Desktop/Chess-board
source venv/bin/activate
python -m chess_voice_robot.main
# or with a custom port:
SERIAL_PORT=/dev/tty.usbmodemXXXX python -m chess_voice_robot.main

# Or override the port for this session
SERIAL_PORT=/dev/tty.usbmodemXXXX python -m chess_voice_robot.main
```

Find your port on macOS:

```bash
ls /dev/tty.usb*
```

You should see `[Robot] Connecting to GRBL on ...` in the terminal. When you speak a move or Stockfish replies, the carriage moves to the source square then the destination square.

**Quick motor test** (no speech/GUI — just sends `e2 → e4`):

```bash
python -m chess_voice_robot.robot.serial_robot
```

### Gameplay

Speak as **White** when prompted. Examples:

- "e two e four"
- "e2 e4"
- "move e2 to e4"
- Promotion: "e seven e eight queen"

Close the pygame window to exit.

### In-game UI

- **Status bar** at the top: green = your turn (mic pulses — speak now), orange = opponent thinking
- Computer waits **1 second** before playing (config: `ENGINE_MOVE_DELAY`)
- After an invalid move, the mic pauses briefly so old phrases are not replayed as errors
- Window icon: white chess king

## Robot hardware config

Tune physical setup in `chess_voice_robot/config.py`:

| Variable | Purpose |
|----------|---------|
| `SERIAL_PORT` | Arduino serial port |
| `SQUARE_SIZE_MM` | Distance between square centers (mm) |
| `BOARD_ORIGIN_X_MM` / `BOARD_ORIGIN_Y_MM` | Machine coordinates of square `a1` |
| `X_AXIS_DIRECTION` / `Y_AXIS_DIRECTION` | `1` or `-1` to flip axis direction |
| `MOVE_FEED_RATE` | Speed in mm/min (`0` = GRBL default) |
| `MOVE_SETTLE_TIME` | Seconds to wait after each move |

Environment overrides:

```bash
export SERIAL_PORT=/dev/tty.usbmodemXXXX
export USE_ROBOT_SIMULATOR=1   # force simulator mode
```
