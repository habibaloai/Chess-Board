"""
Voice-controlled chess vs Stockfish — entry point.

Run from the project root (Chess-board folder):
    python -m chess_voice_robot.main

Requirements: microphone, internet (Google speech API), Stockfish installed.
"""

import queue
import sys

from chess_voice_robot import config
from chess_voice_robot.ai.stockfish_engine import StockfishEngine
from chess_voice_robot.chess_engine.game import ChessGame
from chess_voice_robot.core.controller import GameController
from chess_voice_robot.robot.interface import RobotInterface
from chess_voice_robot.speech.speech_recognizer import SpeechRecognizer
from chess_voice_robot.ui.board_gui import BoardGUI


def _create_robot() -> RobotInterface:
    if config.USE_ROBOT_SIMULATOR:
        from chess_voice_robot.robot.simulator import RobotSimulator

        print("[Robot] Using simulator (no hardware).")
        return RobotSimulator()

    from chess_voice_robot.robot.serial_robot import SerialRobot

    print(f"[Robot] Connecting to GRBL on {config.SERIAL_PORT} ...")
    return SerialRobot()


def main() -> None:
    print("=" * 50)
    print("  Voice Chess — speak moves like 'e2 e4'")
    print("  Close the window to quit.")
    print("=" * 50)

    game = ChessGame()
    gui = BoardGUI()
    robot = _create_robot()
    stockfish = StockfishEngine()

    try:
        stockfish.start()
    except FileNotFoundError:
        print(
            "\n[ERROR] Stockfish not found. Install it:\n"
            "  macOS:  brew install stockfish\n"
            "  Linux:  sudo apt install stockfish\n"
            "  Or set STOCKFISH_PATH=/path/to/stockfish\n"
        )
        gui.quit()
        sys.exit(1)

    speech = SpeechRecognizer()
    speech_queue: queue.Queue = queue.Queue()
    controller = GameController(
        game=game,
        gui=gui,
        robot=robot,
        stockfish=stockfish,
        speech=speech,
        speech_queue=speech_queue,
    )

    speech.start_listening(controller.enqueue_speech)
    controller.initial_draw()

    running = True
    try:
        while running:
            running = gui.pump_events()
            controller.tick()
            controller.refresh_display()
            gui.tick()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        speech.stop()
        stockfish.stop()
        if hasattr(robot, "close"):
            robot.close()
        gui.quit()
        print("Goodbye.")


if __name__ == "__main__":
    main()
