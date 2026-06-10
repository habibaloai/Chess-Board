"""
Voice-controlled chess vs Stockfish — entry point.

Run from the project root (Chess-board folder):
    python -m chess_voice_robot.main

Requirements: microphone, Stockfish installed. Speech uses local faster-whisper (offline).
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

        return RobotSimulator()

    from chess_voice_robot.robot.serial_robot import SerialRobot

    return SerialRobot()


def main() -> None:
    game = ChessGame()
    gui = BoardGUI()
    robot = _create_robot()
    stockfish = StockfishEngine()

    try:
        stockfish.start()
    except FileNotFoundError:
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
            running = gui.pump_events(on_estop=controller.emergency_stop)
            controller.tick()
            controller.refresh_display()
            gui.tick()
    except KeyboardInterrupt:
        pass
    finally:
        speech.stop()
        stockfish.stop()
        if hasattr(robot, "close"):
            robot.close()
        gui.quit()


if __name__ == "__main__":
    main()
