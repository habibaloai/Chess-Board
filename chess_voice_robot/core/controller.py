"""
Game controller — orchestrates speech, chess rules, GUI, AI, and robot.
Uses a turn phase state machine so timing and mic gating feel like online chess.
"""

import queue
import time
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

import chess

from chess_voice_robot import config
from chess_voice_robot.chess_engine.game import ChessGame
from chess_voice_robot.ai.stockfish_engine import StockfishEngine
from chess_voice_robot.robot.interface import RobotInterface
from chess_voice_robot.ui.board_gui import BoardGUI, StatusDisplay
from chess_voice_robot.utils import audio
from chess_voice_robot.utils.move_parser import parse_speech_to_uci

if TYPE_CHECKING:
    from chess_voice_robot.speech.speech_recognizer import SpeechRecognizer


class TurnPhase(Enum):
    """When the user may speak and when the engine may move."""

    HUMAN_TURN = auto()        # mic on — waiting for voice move
    HUMAN_PROCESSING = auto()  # applying a parsed move (brief)
    ENGINE_WAITING = auto()    # delay before Stockfish plays
    ENGINE_MOVING = auto()     # Stockfish thinking / applying
    SPEECH_COOLDOWN = auto()   # after invalid input — mic off, clear queue
    GAME_OVER = auto()


class GameController:
    """
    Receives speech → validates via python-chess → updates GUI → robot → Stockfish.
    Call tick() every frame from the pygame loop.
    """

    def __init__(
        self,
        game: ChessGame,
        gui: BoardGUI,
        robot: RobotInterface,
        stockfish: StockfishEngine,
        speech: "SpeechRecognizer",
        speech_queue: queue.Queue,
    ) -> None:
        self.game = game
        self.gui = gui
        self.robot = robot
        self.stockfish = stockfish
        self.speech = speech
        self.speech_queue = speech_queue

        self._phase = TurnPhase.HUMAN_TURN
        self._engine_ready_at: float = 0.0
        self._cooldown_until: float = 0.0
        self._busy = False

    def refresh_display(self) -> None:
        """Redraw board + status (e.g. pulsing mic indicator during your turn)."""
        self._update_status_bar()
        self.gui.draw(self.game.board)

    def tick(self) -> None:
        """Update timers, status bar, engine delay, and process at most one voice command."""
        self._update_status_bar()

        now = time.monotonic()

        if self._phase == TurnPhase.ENGINE_WAITING and now >= self._engine_ready_at:
            self._phase = TurnPhase.ENGINE_MOVING
            self._update_status_bar()
            self._execute_engine_move()

        if self._phase == TurnPhase.SPEECH_COOLDOWN and now >= self._cooldown_until:
            self._begin_human_turn()

        if self._phase == TurnPhase.HUMAN_TURN and not self._busy:
            text = self._take_latest_speech()
            if text:
                self._busy = True
                try:
                    self._handle_speech(text)
                finally:
                    self._busy = False

    def enqueue_speech(self, text: str) -> None:
        """Only accept speech during the human turn (mic is unpaused)."""
        if self._phase != TurnPhase.HUMAN_TURN:
            return
        # Keep only the newest utterance — drop stale retries
        try:
            while True:
                self.speech_queue.get_nowait()
        except queue.Empty:
            pass
        self.speech_queue.put(text)

    def _clear_speech_queue(self) -> None:
        try:
            while True:
                self.speech_queue.get_nowait()
        except queue.Empty:
            pass

    def _take_latest_speech(self) -> Optional[str]:
        latest = None
        try:
            while True:
                latest = self.speech_queue.get_nowait()
        except queue.Empty:
            pass
        return latest

    def _begin_human_turn(self) -> None:
        if self.game.is_game_over():
            self._phase = TurnPhase.GAME_OVER
            self.speech.set_paused(True)
            self._clear_speech_queue()
            return
        self._phase = TurnPhase.HUMAN_TURN
        self.speech.set_paused(False)

    def _begin_engine_turn(self) -> None:
        self._phase = TurnPhase.ENGINE_WAITING
        self.speech.set_paused(True)
        self._clear_speech_queue()
        self._engine_ready_at = time.monotonic() + config.ENGINE_MOVE_DELAY

    def _begin_invalid_cooldown(self) -> None:
        self._phase = TurnPhase.SPEECH_COOLDOWN
        self.speech.set_paused(True)
        self._clear_speech_queue()
        self._cooldown_until = time.monotonic() + config.SPEECH_COOLDOWN_AFTER_INVALID
        audio.announce_invalid_move()

    def _update_status_bar(self) -> None:
        if self._phase == TurnPhase.GAME_OVER:
            self.gui.set_status(
                StatusDisplay(
                    title="Game over",
                    subtitle=self.game.outcome_message() or "Close window to exit",
                    accent_color=config.COLOR_WAIT,
                )
            )
            return

        if self._phase == TurnPhase.HUMAN_TURN:
            self.gui.set_status(
                StatusDisplay(
                    title="Your turn — White",
                    subtitle=config.SPEAK_NOW_HINT,
                    accent_color=config.COLOR_YOUR_TURN,
                    show_mic=True,
                    pulse=True,
                )
            )
            return

        if self._phase == TurnPhase.SPEECH_COOLDOWN:
            self.gui.set_status(
                StatusDisplay(
                    title="Invalid move",
                    subtitle="Listen… then speak your move again",
                    accent_color=config.COLOR_INVALID,
                )
            )
            return

        if self._phase in (TurnPhase.ENGINE_WAITING, TurnPhase.ENGINE_MOVING):
            self.gui.set_status(
                StatusDisplay(
                    title="Black to move",
                    subtitle=config.ENGINE_THINKING_MESSAGE,
                    accent_color=config.COLOR_OPPONENT_TURN,
                )
            )
            return

        if self._phase == TurnPhase.HUMAN_PROCESSING:
            self.gui.set_status(
                StatusDisplay(
                    title="Applying your move…",
                    subtitle="",
                    accent_color=config.COLOR_WAIT,
                )
            )

    def _handle_speech(self, text: str) -> None:
        if self._phase != TurnPhase.HUMAN_TURN:
            return

        if self.game.is_game_over():
            self._phase = TurnPhase.GAME_OVER
            return

        self._phase = TurnPhase.HUMAN_PROCESSING
        self.speech.set_paused(True)
        self._update_status_bar()
        self.gui.draw(self.game.board)

        uci = parse_speech_to_uci(text)
        if uci is None or not self.game.push_uci(uci):
            self._begin_invalid_cooldown()
            self.gui.draw(self.game.board)
            return

        audio.play_valid_move()
        self._notify_robot_and_gui()
        self._after_human_move()

    def _notify_robot_and_gui(self) -> None:
        squares = self.game.last_move_squares()
        if squares:
            from_sq, to_sq = squares
            self.robot.move(from_sq, to_sq)
            self.gui.set_last_move_highlight(from_sq, to_sq)
        self.gui.draw(self.game.board)

    def _after_human_move(self) -> None:
        if self.game.is_game_over():
            self._phase = TurnPhase.GAME_OVER
            self.speech.set_paused(True)
            self.gui.draw(self.game.board)
            return

        self._begin_engine_turn()
        self.gui.draw(self.game.board)

    def _execute_engine_move(self) -> None:
        move: Optional[chess.Move] = self.stockfish.get_best_move(self.game.board)
        if move is None:
            print("[Stockfish] Engine unavailable. Check Stockfish installation.")
            self._begin_human_turn()
            self.gui.draw(self.game.board)
            return

        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)

        if not self.game.push_move(move):
            self._begin_human_turn()
            return

        self.robot.move(from_sq, to_sq)
        self.gui.set_last_move_highlight(from_sq, to_sq)
        self.gui.draw(self.game.board)

        if self.game.is_game_over():
            self._phase = TurnPhase.GAME_OVER
            self.speech.set_paused(True)
        else:
            self._begin_human_turn()

        self.gui.draw(self.game.board)

    def initial_draw(self) -> None:
        self.gui.draw(self.game.board)
        self._begin_human_turn()
        self.gui.draw(self.game.board)
