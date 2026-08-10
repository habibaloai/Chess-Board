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
from chess_voice_robot.utils import audio


def _create_robot() -> RobotInterface:
    if config.USE_ROBOT_SIMULATOR:
        from chess_voice_robot.robot.simulator import RobotSimulator

        return RobotSimulator()

    from chess_voice_robot.robot.serial_robot import SerialRobot

    return SerialRobot()


def main() -> None:
    game = ChessGame()
    gui = BoardGUI()
    audio.start_background_music()
    gui.show_loading_screen()
    audio.ensure_background_music()
    # Keep the gameplay wallpaper visible while engines and speech start up.
    gui.show_game_backdrop()
    audio.ensure_background_music()

    robot = _create_robot()
    gui.show_game_backdrop()
    audio.ensure_background_music()
    stockfish = StockfishEngine()

    try:
        stockfish.start()
    except FileNotFoundError:
        audio.stop_background_music()
        gui.quit()
        sys.exit(1)

    gui.show_game_backdrop()
    audio.ensure_background_music()
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
    audio.ensure_background_music()
    controller.initial_draw()

    running = True
    try:
        while running:
            audio.ensure_background_music()
            running = gui.pump_events(
                on_estop=controller.emergency_stop,
                on_board_click=controller.handle_board_click,
                on_mic_toggle=controller.toggle_speech_mode,
            )
            controller.tick()
            controller.refresh_display()
            gui.tick()
    except KeyboardInterrupt:
        pass
    finally:
        speech.stop()
        stockfish.stop()
        controller.shutdown_robot()
        robot.go_home()
        if hasattr(robot, "close"):
            robot.close()
        audio.stop_background_music()
        gui.quit()


if __name__ == "__main__":
    main()
