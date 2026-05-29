# Voice-Controlled Chess (vs Stockfish)

Desktop chess where you **speak moves**, see a **live pygame board**, and play against **Stockfish**. Architecture is modular so a **physical chess robot** can plug in later without changing game logic.

## Features

- Voice input → UCI moves (`e2e4`) via natural speech ("e two e four", "move e2 to e4", "e2 e4")
- Full rules via **python-chess** (castling, en passant, promotion)
- Pygame board with **square labels** (a1–h8) and Unicode pieces
- **Stockfish** replies after each valid move
- Invalid input: error beep + auto re-listen; valid move: short success chime (no voice)
- **Robot layer** abstracted (`RobotInterface`); simulator prints pick/move/drop for now

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
├── robot/interface.py, simulator.py
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

```bash
source venv/bin/activate
python -m chess_voice_robot.main
```

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

## Future robot hardware

Implement `RobotInterface` in a new class (e.g. `robot/serial_robot.py`) and pass it into `GameController` instead of `RobotSimulator`. Core controller, chess engine, speech, and GUI stay unchanged.

```python
class RobotInterface(ABC):
    def move(self, from_square: str, to_square: str) -> None: ...
```

## License

MIT — use and modify freely.
