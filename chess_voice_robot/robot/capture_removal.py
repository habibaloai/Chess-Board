"""
Captured-piece removal — path planning and side selection only.

Uses the existing board-coordinate → physical-coordinate mapping (+ ORIGIN_OFFSET).
Does not modify calibration constants or normal move math.
"""

from __future__ import annotations

from typing import Literal, Optional, Set

import chess

from chess_voice_robot import config

Side = Literal["left", "right"]


def captured_square_for_move(board: chess.Board, move: chess.Move) -> Optional[str]:
    """Return the square holding the captured piece before *move* is applied."""
    if not board.is_capture(move):
        return None
    if board.is_en_passant(move):
        if board.turn == chess.WHITE:
            captured_sq = move.to_square - 8
        else:
            captured_sq = move.to_square + 8
        return chess.square_name(captured_sq)
    return chess.square_name(move.to_square)


def occupied_square_names(board: chess.Board) -> Set[str]:
    return {chess.square_name(sq) for sq in chess.SQUARES if board.piece_at(sq)}


def board_square_center_mm(square: str) -> tuple[float, float]:
    """Physical work coordinates of a square centre (same mapping as SerialRobot)."""
    file_idx = ord(square[0].lower()) - ord("a")
    rank_idx = int(square[1]) - 1
    x = config.BOARD_ORIGIN_X_MM + (file_idx * config.SQUARE_SIZE_MM * config.X_AXIS_DIRECTION)
    y = config.BOARD_ORIGIN_Y_MM + (rank_idx * config.SQUARE_SIZE_MM * config.Y_AXIS_DIRECTION)
    return x + config.ORIGIN_OFFSET_X_MM, y + config.ORIGIN_OFFSET_Y_MM


def _square_west_edge_x(file_idx: int) -> float:
    return (
        config.ORIGIN_OFFSET_X_MM
        + file_idx * config.SQUARE_SIZE_MM
        - config.SQUARE_SIZE_MM / 2.0
    )


def _square_east_edge_x(file_idx: int) -> float:
    return (
        config.ORIGIN_OFFSET_X_MM
        + file_idx * config.SQUARE_SIZE_MM
        + config.SQUARE_SIZE_MM / 2.0
    )


def _clamp_physical(x_mm: float, y_mm: float) -> tuple[float, float]:
    limit = config.PLAY_AREA_MM
    return max(0.0, min(limit, x_mm)), max(0.0, min(limit, y_mm))


def _rank_path_blocked(
    occupied: Set[str],
    rank: int,
    x_low: float,
    x_high: float,
    exclude: str,
) -> bool:
    """True if an occupied square centre on *rank* lies between the X endpoints."""
    lo, hi = (x_low, x_high) if x_low <= x_high else (x_high, x_low)
    for square in occupied:
        if square == exclude:
            continue
        if int(square[1]) != rank:
            continue
        cx, _ = board_square_center_mm(square)
        if lo < cx < hi:
            return True
    return False


def _rank_path_clear(
    occupied: Set[str],
    rank: int,
    x_low: float,
    x_high: float,
    exclude: str,
) -> bool:
    """True when no occupied square centre on *rank* lies between the X endpoints."""
    return not _rank_path_blocked(occupied, rank, x_low, x_high, exclude)


def choose_removal_side(captured_square: str, occupied: Set[str]) -> Side:
    """Pick the boundary side used for capture removal."""
    px, _ = board_square_center_mm(captured_square)
    rank = int(captured_square[1])
    right_limit = config.PLAY_AREA_MM

    left_clear = _rank_path_clear(occupied, rank, 0.0, px, captured_square)
    right_clear = _rank_path_clear(occupied, rank, px, right_limit, captured_square)

    if left_clear and not right_clear:
        return "left"
    if right_clear and not left_clear:
        return "right"
    return "left" if px <= right_limit - px else "right"


def plan_capture_removal(
    captured_square: str,
    occupied: Set[str],
) -> list[tuple[float, float]]:
    """
    Physical waypoints after pickup.

    - One side clear to the boundary: move horizontally on the current rank.
    - Both sides blocked: rise half a square to the top edge, then move horizontally
      to the nearer boundary.
    """
    px, py = board_square_center_mm(captured_square)
    rank = int(captured_square[1])
    right_limit = config.PLAY_AREA_MM

    left_clear = _rank_path_clear(occupied, rank, 0.0, px, captured_square)
    right_clear = _rank_path_clear(occupied, rank, px, right_limit, captured_square)

    if left_clear and not right_clear:
        return [_clamp_physical(0.0, py)]
    if right_clear and not left_clear:
        return [_clamp_physical(right_limit, py)]
    if left_clear and right_clear:
        if px <= right_limit - px:
            return [_clamp_physical(0.0, py)]
        return [_clamp_physical(right_limit, py)]

    top_y = min(py + config.SQUARE_SIZE_MM / 2.0, right_limit)
    if px <= right_limit - px:
        return [
            _clamp_physical(px, top_y),
            _clamp_physical(0.0, top_y),
        ]
    return [
        _clamp_physical(px, top_y),
        _clamp_physical(right_limit, top_y),
    ]


def removal_waypoints(captured_square: str, side: Side) -> list[tuple[float, float]]:
    """Legacy helper — horizontal path on the current rank via square edge."""
    file_idx = ord(captured_square[0].lower()) - ord("a")
    _, py = board_square_center_mm(captured_square)

    if side == "left":
        points = [(_square_west_edge_x(file_idx), py), (0.0, py)]
    else:
        points = [(_square_east_edge_x(file_idx), py), (config.PLAY_AREA_MM, py)]

    return [_clamp_physical(x, y) for x, y in points]
