"""
Chess game logic — python-chess Board is the ONLY source of truth.
"""

from typing import List, Optional

import chess


class ChessGame:
    """
    Wraps a python-chess Board.
    All move validation uses board.legal_moves (castling, en passant, promotion).
    """

    def __init__(self) -> None:
        self.board = chess.Board()

    def reset(self) -> None:
        """Return to starting position."""
        self.board.reset()

    def is_white_to_move(self) -> bool:
        return self.board.turn == chess.WHITE

    def is_human_turn(self) -> bool:
        """Human plays white in this app."""
        return self.is_white_to_move()

    def is_game_over(self) -> bool:
        return self.board.is_game_over()

    def outcome_message(self) -> str:
        """Short spoken-friendly game result."""
        if not self.is_game_over():
            return ""
        outcome = self.board.outcome()
        if outcome is None:
            return "Game over"
        if outcome.winner is None:
            return "Draw"
        if outcome.winner:
            return "White wins"
        return "Black wins"

    def push_uci(self, uci: str) -> bool:
        """
        Apply a UCI move (e.g. e2e4, e7e8q) if legal.
        Returns True on success, False if illegal or malformed.
        """
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return False

        if move not in self.board.legal_moves:
            return False

        self.board.push(move)
        return True

    def push_move(self, move: chess.Move) -> bool:
        """Apply a chess.Move if it is legal (used by Stockfish)."""
        if move not in self.board.legal_moves:
            return False
        self.board.push(move)
        return True

    def last_move_uci(self) -> Optional[str]:
        """UCI of the most recent move, or None."""
        if self.board.move_stack:
            return self.board.peek().uci()
        return None

    def last_move_squares(self) -> Optional[tuple[str, str]]:
        """(from_square, to_square) names like e2, e4 for the last move."""
        if not self.board.move_stack:
            return None
        move = self.board.peek()
        return chess.square_name(move.from_square), chess.square_name(move.to_square)

    def fen(self) -> str:
        return self.board.fen()

    def legal_moves_uci(self) -> List[str]:
        return [m.uci() for m in self.board.legal_moves]
