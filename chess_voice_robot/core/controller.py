"""
Game controller — orchestrates speech, chess rules, GUI, AI, and robot.
Uses a turn phase state machine so timing and mic gating feel like online chess.
"""

import queue
import threading
import time
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Set

import chess

from chess_voice_robot import config
from chess_voice_robot.chess_engine.game import ChessGame
from chess_voice_robot.ai.stockfish_engine import StockfishEngine
from chess_voice_robot.robot.interface import RobotInterface
from chess_voice_robot.robot.capture_removal import (
    captured_square_for_move,
    occupied_square_names,
)
from chess_voice_robot.ui.board_gui import BoardGUI, StatusDisplay
from chess_voice_robot.utils import audio
from chess_voice_robot.utils.move_parser import parse_speech_to_uci

if TYPE_CHECKING:
    from chess_voice_robot.speech.speech_recognizer import SpeechRecognizer


class TurnPhase(Enum):
    """When the user may speak and when the engine may move."""

    HUMAN_TURN = auto()        # mic on — waiting for voice move
    HUMAN_PROCESSING = auto()  # applying a parsed move (brief)
    ROBOT_MOVING = auto()      # physical robot executing — mic off
    ENGINE_WAITING = auto()    # delay before Stockfish plays (after robot idle)
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
        self._robot_queue: queue.Queue = queue.Queue()
        self._robot_lock = threading.Lock()
        self._robot_moving = False
        self._robot_resume: Optional[str] = None  # "engine", "human", or "game_over"
        self._robot_thread = threading.Thread(target=self._robot_worker, daemon=True)
        self._robot_thread.start()

        self._selected_square: Optional[str] = None
        self._legal_targets: Set[str] = set()

        # Narration / long-turn state (reset on a new game session).
        self._human_turn_count = 0
        self._long_turn_deadline: Optional[float] = None
        self._long_turn_warned = False
        self._delay_long_turn_for_intro = False
        self._stir_played_this_engine_turn = False
        audio.reset_narrator_session()

    def _robot_worker(self) -> None:
        while True:
            job = self._robot_queue.get()
            from_sq = job[0]
            if from_sq is None:
                break
            to_sq, captured_sq, occupied, moving_piece = job[1], job[2], job[3], job[4]
            try:
                self.robot.move(
                    from_sq,
                    to_sq,
                    captured_square=captured_sq,
                    occupied_squares=occupied,
                    moving_piece=moving_piece,
                )
            finally:
                with self._robot_lock:
                    self._robot_moving = False

    def _is_robot_idle(self) -> bool:
        with self._robot_lock:
            return not self._robot_moving and self._robot_queue.empty()

    def _dispatch_robot_move(
        self,
        from_sq: str,
        to_sq: str,
        *,
        resume: str,
        captured_square: Optional[str] = None,
        occupied_squares: Optional[set[str]] = None,
        moving_piece: Optional[str] = None,
    ) -> None:
        """Queue a robot move; call _on_robot_idle() when resume target is reached."""
        with self._robot_lock:
            self._robot_moving = True
        self._robot_resume = resume
        self._phase = TurnPhase.ROBOT_MOVING
        self.speech.set_paused(True)
        self._clear_speech_queue()
        self._clear_selection()
        self._robot_queue.put((from_sq, to_sq, captured_square, occupied_squares, moving_piece))

    def _on_robot_idle(self) -> None:
        if not self._is_robot_idle():
            return
        resume = self._robot_resume
        self._robot_resume = None
        if resume == "engine":
            self._begin_engine_turn()
        elif resume == "human":
            self._begin_human_turn()
        elif resume == "game_over":
            self._phase = TurnPhase.GAME_OVER
            self.speech.set_paused(True)
            self._cancel_long_turn_timer()
        self.gui.draw(self.game.board)

    def emergency_stop(self) -> None:
        """Stop motors immediately and cancel any queued robot moves."""
        try:
            while True:
                self._robot_queue.get_nowait()
        except queue.Empty:
            pass
        self.robot.emergency_stop()

    def shutdown_robot(self) -> None:
        """Drain queued moves, stop the worker, and wait for in-flight motion to finish."""
        try:
            while True:
                self._robot_queue.get_nowait()
        except queue.Empty:
            pass
        self._robot_queue.put((None, None, None, None, None))
        self._robot_thread.join(timeout=config.GRBL_IDLE_TIMEOUT)

    def refresh_display(self) -> None:
        """Redraw board + status (e.g. pulsing mic indicator during your turn)."""
        self._update_status_bar()
        if self._selected_square:
            self.gui.set_selection(self._selected_square, self._legal_targets)
        self.gui.draw(self.game.board)

    def tick(self) -> None:
        """Update timers, status bar, engine delay, and process at most one voice command."""
        audio.tick_narrator()
        audio.ensure_background_music()
        self._update_status_bar()

        now = time.monotonic()

        if self._delay_long_turn_for_intro and not audio.narrator_busy():
            self._delay_long_turn_for_intro = False
            self._arm_long_turn_timer()

        if (
            self._phase == TurnPhase.HUMAN_TURN
            and self._long_turn_deadline is not None
            and not self._long_turn_warned
            and now >= self._long_turn_deadline
        ):
            self._long_turn_warned = True
            audio.play_takes_too_long()

        if self._phase == TurnPhase.ROBOT_MOVING and self._is_robot_idle():
            self._on_robot_idle()

        if self._phase == TurnPhase.ENGINE_WAITING and now >= self._engine_ready_at:
            self._phase = TurnPhase.ENGINE_MOVING
            self._update_status_bar()
            self._execute_engine_move()

        if self._phase == TurnPhase.SPEECH_COOLDOWN and now >= self._cooldown_until:
            # Same human turn continues after an invalid attempt — no new turn announcement.
            self._begin_human_turn(announce_turn=False, fresh_turn=False)

        if (
            self._phase == TurnPhase.HUMAN_TURN
            and not self._busy
            and self.gui.speech_recognition_enabled
        ):
            text = self._take_latest_speech()
            if text:
                self._busy = True
                try:
                    self._handle_speech(text)
                finally:
                    self._busy = False

    def _arm_long_turn_timer(self) -> None:
        self._long_turn_deadline = time.monotonic() + config.PLAYER_TURN_TIMEOUT_SECONDS
        self._long_turn_warned = False

    def _cancel_long_turn_timer(self) -> None:
        self._long_turn_deadline = None
        self._long_turn_warned = False
        self._delay_long_turn_for_intro = False

    def _begin_human_turn(
        self,
        *,
        announce_turn: bool = True,
        fresh_turn: bool = True,
        delay_long_timer: bool = False,
    ) -> None:
        if not self._is_robot_idle():
            self._phase = TurnPhase.ROBOT_MOVING
            self.speech.set_paused(True)
            return
        if self.game.is_game_over():
            self._phase = TurnPhase.GAME_OVER
            self.speech.set_paused(True)
            self._clear_speech_queue()
            self._cancel_long_turn_timer()
            return
        self._phase = TurnPhase.HUMAN_TURN
        if self.gui.speech_recognition_enabled:
            self.speech.set_paused(False)
        else:
            self.speech.set_paused(True)
            self._clear_speech_queue()

        if fresh_turn:
            self._human_turn_count += 1
            # First turn uses intro narration (board awaits + first move).
            if announce_turn and self._human_turn_count > 1:
                audio.play_players_turn()
            if delay_long_timer:
                self._delay_long_turn_for_intro = True
                self._long_turn_deadline = None
                self._long_turn_warned = False
            else:
                self._arm_long_turn_timer()

    def _begin_engine_turn(self) -> None:
        if not self._is_robot_idle():
            self._phase = TurnPhase.ROBOT_MOVING
            self.speech.set_paused(True)
            return
        self._cancel_long_turn_timer()
        self._phase = TurnPhase.ENGINE_WAITING
        self.speech.set_paused(True)
        self._clear_speech_queue()
        self._engine_ready_at = time.monotonic() + config.ENGINE_MOVE_DELAY
        if not self._stir_played_this_engine_turn:
            self._stir_played_this_engine_turn = True
            audio.play_opposing_stir()

    def _begin_invalid_cooldown(self) -> None:
        self._phase = TurnPhase.SPEECH_COOLDOWN
        self.speech.set_paused(True)
        self._clear_speech_queue()
        self._cooldown_until = time.monotonic() + config.SPEECH_COOLDOWN_AFTER_INVALID
        audio.announce_invalid_move()
        # Invalid attempts must not reset the long-turn timer.

    def enqueue_speech(self, text: str) -> None:
        """Only accept speech during the human turn in voice mode."""
        if self._phase != TurnPhase.HUMAN_TURN or not self.gui.speech_recognition_enabled:
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

    def _update_status_bar(self) -> None:
        if self._phase == TurnPhase.GAME_OVER:
            outcome = self.game.outcome_message() or "The match is ended."
            title = "Checkmate." if "checkmate" in outcome.lower() else "Game over"
            self.gui.set_status(
                StatusDisplay(
                    title=title,
                    subtitle=outcome,
                    accent_color=config.COLOR_VICTORY,
                )
            )
            return

        if self._phase == TurnPhase.HUMAN_TURN:
            subtitle = (
                config.MOUSE_MODE_HINT
                if not self.gui.speech_recognition_enabled
                else config.SPEAK_NOW_HINT
            )
            in_check = self.game.board.is_check()
            title = "Your king is in check." if in_check else "Your move."
            accent = config.COLOR_CHECK if in_check else config.COLOR_YOUR_TURN
            self.gui.set_status(
                StatusDisplay(
                    title=title,
                    subtitle=subtitle,
                    accent_color=accent,
                    pulse=self.gui.speech_recognition_enabled,
                )
            )
            return

        if self._phase == TurnPhase.SPEECH_COOLDOWN:
            self.gui.set_status(
                StatusDisplay(
                    title="That piece cannot move there.",
                    subtitle="Compose yourself… then speak again.",
                    accent_color=config.COLOR_INVALID,
                )
            )
            return

        if self._phase == TurnPhase.ROBOT_MOVING:
            self.gui.set_status(
                StatusDisplay(
                    title="The enchantment takes hold…",
                    subtitle=config.ROBOT_MOVING_MESSAGE,
                    accent_color=config.COLOR_WAIT,
                )
            )
            return

        if self._phase in (TurnPhase.ENGINE_WAITING, TurnPhase.ENGINE_MOVING):
            self.gui.set_status(
                StatusDisplay(
                    title="Your opponent is considering their move…",
                    subtitle=config.ENGINE_THINKING_MESSAGE,
                    accent_color=config.COLOR_OPPONENT_TURN,
                )
            )
            return

        if self._phase == TurnPhase.HUMAN_PROCESSING:
            self.gui.set_status(
                StatusDisplay(
                    title="Your move is accepted.",
                    subtitle="",
                    accent_color=config.COLOR_WAIT,
                )
            )

    def toggle_speech_mode(self) -> None:
        speech_on = self.gui.toggle_speech()
        self._clear_selection()
        if speech_on:
            if self._phase == TurnPhase.HUMAN_TURN:
                self.speech.set_paused(False)
        else:
            self.speech.set_paused(True)
            self._clear_speech_queue()
        self._update_status_bar()
        self.gui.draw(self.game.board)

    def handle_board_click(self, square: str) -> None:
        """Click-to-move when the mic is off (mouse mode)."""
        if self.gui.speech_recognition_enabled:
            return
        if self._phase != TurnPhase.HUMAN_TURN:
            return
        if self.game.is_game_over():
            return

        board = self.game.board
        sq_idx = chess.parse_square(square)
        piece = board.piece_at(sq_idx)

        if self._selected_square is None:
            if piece is None or piece.color != chess.WHITE:
                return
            legal_from_here = [
                m for m in board.legal_moves if m.from_square == sq_idx
            ]
            if not legal_from_here:
                self.gui.flash_illegal({square})
                self.gui.draw(board)
                return
            self._selected_square = square
            self._legal_targets = {chess.square_name(m.to_square) for m in legal_from_here}
            self.gui.set_selection(self._selected_square, self._legal_targets)
            self.gui.draw(board)
            return

        if square == self._selected_square:
            self._clear_selection()
            self.gui.draw(board)
            return

        if piece is not None and piece.color == chess.WHITE:
            legal_from_here = [
                m for m in board.legal_moves if m.from_square == sq_idx
            ]
            if legal_from_here:
                self._selected_square = square
                self._legal_targets = {chess.square_name(m.to_square) for m in legal_from_here}
                self.gui.set_selection(self._selected_square, self._legal_targets)
                self.gui.draw(board)
                return

        move = self._move_for_click(board, self._selected_square, square)
        if move is None:
            self.gui.flash_illegal({square, self._selected_square})
            self._clear_selection()
            audio.announce_invalid_move()
            self.gui.draw(board)
            return

        self._clear_selection()
        self._phase = TurnPhase.HUMAN_PROCESSING
        self.speech.set_paused(True)
        self._update_status_bar()
        self.gui.draw(board)

        if not self._apply_move_and_dispatch_robot(move, resume_on_continue="engine"):
            self.gui.flash_illegal({square})
            audio.announce_invalid_move()
            self.gui.draw(board)
            self._begin_human_turn(announce_turn=False, fresh_turn=False)

    def _clear_selection(self) -> None:
        self._selected_square = None
        self._legal_targets = set()
        self.gui.clear_selection()

    @staticmethod
    def _move_for_click(board: chess.Board, from_sq: str, to_sq: str) -> Optional[chess.Move]:
        from_idx = chess.parse_square(from_sq)
        to_idx = chess.parse_square(to_sq)
        candidates = [
            m for m in board.legal_moves
            if m.from_square == from_idx and m.to_square == to_idx
        ]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        return max(candidates, key=lambda m: m.promotion or chess.QUEEN)

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
        if uci is None:
            self._begin_invalid_cooldown()
            self.gui.draw(self.game.board)
            return

        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            self._begin_invalid_cooldown()
            self.gui.draw(self.game.board)
            return

        if move not in self.game.board.legal_moves:
            self._begin_invalid_cooldown()
            self.gui.draw(self.game.board)
            return

        if not self._apply_move_and_dispatch_robot(move, resume_on_continue="engine"):
            self._begin_invalid_cooldown()
            self.gui.draw(self.game.board)

    def _apply_move_and_dispatch_robot(self, move: chess.Move, *, resume_on_continue: str) -> bool:
        """Record pre-move occupancy, apply move, and queue the physical robot sequence."""
        occupied = occupied_square_names(self.game.board)
        captured = captured_square_for_move(self.game.board, move)
        piece = self.game.board.piece_at(move.from_square)
        moving_piece = piece.symbol() if piece else None

        if not self.game.push_move(move):
            return False

        self._cancel_long_turn_timer()

        if self.game.board.is_checkmate():
            # King "dies" — victory narration (priority over capture / check clips).
            outcome = self.game.board.outcome()
            if outcome is not None and outcome.winner == chess.WHITE:
                audio.play_player_wins()
            elif outcome is not None and outcome.winner == chess.BLACK:
                audio.play_opponent_wins()
        elif self.game.board.is_check():
            # King threatened only (not mate).
            if self.game.board.turn == chess.WHITE:
                audio.play_player_checkmate()
            else:
                audio.play_opponent_checkmate()
        elif captured is not None:
            audio.play_piece_fallen()

        if resume_on_continue == "engine":
            # Allow stir narration once when the opponent turn actually begins.
            self._stir_played_this_engine_turn = False

        resume = "game_over" if self.game.is_game_over() else resume_on_continue
        squares = self.game.last_move_squares()
        if squares:
            from_sq, to_sq = squares
            self._dispatch_robot_move(
                from_sq,
                to_sq,
                resume=resume,
                captured_square=captured,
                occupied_squares=occupied,
                moving_piece=moving_piece,
            )
            self.gui.set_last_move_highlight(from_sq, to_sq)
        elif self.game.is_game_over():
            self._phase = TurnPhase.GAME_OVER
            self.speech.set_paused(True)
            self._cancel_long_turn_timer()
        else:
            if resume_on_continue == "engine":
                self._begin_engine_turn()
            else:
                self._begin_human_turn()
        self.gui.draw(self.game.board)
        return True

    def _execute_engine_move(self) -> None:
        if not self._is_robot_idle():
            self._phase = TurnPhase.ROBOT_MOVING
            return

        move: Optional[chess.Move] = self.stockfish.get_best_move(self.game.board)
        if move is None:
            if self._is_robot_idle():
                self._begin_human_turn()
            self.gui.draw(self.game.board)
            return

        if move not in self.game.board.legal_moves:
            if self._is_robot_idle():
                self._begin_human_turn()
            return

        if not self._apply_move_and_dispatch_robot(move, resume_on_continue="human"):
            if self._is_robot_idle():
                self._begin_human_turn()
            self.gui.draw(self.game.board)

    def initial_draw(self) -> None:
        audio.ensure_background_music()
        audio.set_gameplay_music_volume()
        self._update_status_bar()
        # Start intro as the board fades in (awaits → first move, queued).
        audio.queue_game_intro()
        self.gui.fade_in_board(self.game.board)
        self._begin_human_turn(
            announce_turn=False,
            fresh_turn=True,
            delay_long_timer=True,
        )
