"""
Stockfish AI opponent via python-chess engine protocol.
"""

from typing import Optional

import chess
import chess.engine

from chess_voice_robot import config


class StockfishEngine:
    """
    Wraps Stockfish as a UCI engine.
    Call get_best_move(board) when it is the engine's turn.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or config.STOCKFISH_PATH
        self._engine: Optional[chess.engine.SimpleEngine] = None

    def start(self) -> None:
        """Open the Stockfish process."""
        if self._engine is not None:
            return
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        self._engine.configure({"Skill Level": config.STOCKFISH_SKILL_LEVEL})

    def stop(self) -> None:
        """Close the engine process."""
        if self._engine is not None:
            self._engine.quit()
            self._engine = None

    def get_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Ask Stockfish for the best move in the given position.
        Returns None if the engine is unavailable or has no legal move.
        """
        if self._engine is None:
            self.start()
        try:
            limit = chess.engine.Limit(time=config.STOCKFISH_TIME_LIMIT)
            result = self._engine.play(board, limit)
            return result.move
        except (chess.engine.EngineError, FileNotFoundError, OSError) as exc:
            print(f"[Stockfish] Engine error: {exc}")
            print(f"[Stockfish] Install Stockfish and/or set STOCKFISH_PATH in config.")
            return None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
