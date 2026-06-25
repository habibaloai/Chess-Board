"""
Knight transport path planning — physical travel only (chess rules unchanged).

Deterministic rule:
  IF either square on the 2-square leg of the L-move is occupied:
    half-square side offset → long leg (2 squares) → half-square side offset
  ELSE:
    direct centre-to-centre path along the long leg first.
"""

from __future__ import annotations

from typing import Literal, Set

from chess_voice_robot import config
from chess_voice_robot.robot.capture_removal import board_square_center_mm

PathMode = Literal["direct", "offset"]

HALF_SQUARE_MM = config.SQUARE_SIZE_MM / 2.0  # 2.5 cm
LONG_LEG_MM = 2.0 * config.SQUARE_SIZE_MM  # 10 cm (two square centres)


def _square_indices(square: str) -> tuple[int, int]:
    return ord(square[0].lower()) - ord("a"), int(square[1]) - 1


def _square_name(file_idx: int, rank_idx: int) -> str:
    return f"{chr(ord('a') + file_idx)}{rank_idx + 1}"


def _clamp_physical(x_mm: float, y_mm: float) -> tuple[float, float]:
    limit = config.PLAY_AREA_MM
    return max(0.0, min(limit, x_mm)), max(0.0, min(limit, y_mm))


def is_knight_move(from_square: str, to_square: str) -> bool:
    ff, fr = _square_indices(from_square)
    tf, tr = _square_indices(to_square)
    df, dr = abs(tf - ff), abs(tr - fr)
    return (df == 1 and dr == 2) or (df == 2 and dr == 1)


def _knight_axes(from_square: str, to_square: str) -> tuple[str, str, int, int, int, int]:
    """
    Return (long_direction, side_direction, long_file_step, long_rank_step,
            side_file_step, side_rank_step).
    """
    ff, fr = _square_indices(from_square)
    tf, tr = _square_indices(to_square)
    df, dr = tf - ff, tr - fr

    if abs(dr) == 2:
        long_file_step, long_rank_step = 0, (1 if dr > 0 else -1)
        side_file_step, side_rank_step = (1 if df > 0 else -1), 0
        long_direction = "forward" if dr > 0 else "backward"
        side_direction = "right" if df > 0 else "left"
    else:
        long_file_step, long_rank_step = (1 if df > 0 else -1), 0
        side_file_step, side_rank_step = 0, (1 if dr > 0 else -1)
        long_direction = "right" if df > 0 else "left"
        side_direction = "up" if dr > 0 else "down"

    return (
        long_direction,
        side_direction,
        long_file_step,
        long_rank_step,
        side_file_step,
        side_rank_step,
    )


def _long_leg_squares(
    from_square: str,
    long_file_step: int,
    long_rank_step: int,
) -> tuple[str, str]:
    ff, fr = _square_indices(from_square)
    first = _square_name(ff + long_file_step, fr + long_rank_step)
    second = _square_name(ff + 2 * long_file_step, fr + 2 * long_rank_step)
    return first, second


def _occupied_on_long_leg(
    from_square: str,
    to_square: str,
    occupied: Set[str],
    long_file_step: int,
    long_rank_step: int,
) -> list[str]:
    skip = {from_square, to_square}
    sq1, sq2 = _long_leg_squares(from_square, long_file_step, long_rank_step)
    found: list[str] = []
    for sq in (sq1, sq2):
        if sq in occupied and sq not in skip and sq not in found:
            found.append(sq)
    return found


def _delta_mm(direction: str, distance_mm: float) -> tuple[float, float]:
    x_dir = config.X_AXIS_DIRECTION
    y_dir = config.Y_AXIS_DIRECTION
    if direction == "left":
        return (-distance_mm * x_dir, 0.0)
    if direction == "right":
        return (distance_mm * x_dir, 0.0)
    if direction in ("forward", "up"):
        return (0.0, distance_mm * y_dir)
    if direction in ("backward", "down"):
        return (0.0, -distance_mm * y_dir)
    raise ValueError(f"unknown direction: {direction}")


def _add_mm(x: float, y: float, dx: float, dy: float) -> tuple[float, float]:
    return _clamp_physical(x + dx, y + dy)


def _direct_waypoints_mm(from_square: str, to_square: str) -> list[tuple[float, float]]:
    """Centre-to-centre L-route: long leg first, then short leg."""
    ff, fr = _square_indices(from_square)
    tf, tr = _square_indices(to_square)
    df, dr = tf - ff, tr - fr

    squares = [from_square]
    if abs(dr) == 2:
        step_r = 1 if dr > 0 else -1
        squares.append(_square_name(ff, fr + step_r))
        squares.append(_square_name(ff, fr + 2 * step_r))
        step_f = 1 if df > 0 else -1
        squares.append(_square_name(tf, fr + 2 * step_r))
    else:
        step_f = 1 if df > 0 else -1
        squares.append(_square_name(ff + step_f, fr))
        squares.append(_square_name(ff + 2 * step_f, fr))
        step_r = 1 if dr > 0 else -1
        squares.append(_square_name(ff + 2 * step_f, tr))

    if squares[-1] != to_square:
        squares.append(to_square)

    mm = [_clamp_physical(*board_square_center_mm(sq)) for sq in squares]
    return mm[1:]


def _offset_waypoints_mm(
    from_square: str,
    to_square: str,
    *,
    long_direction: str,
    side_direction: str,
) -> list[tuple[float, float]]:
    """
    half-square side offset → long leg (2 squares) → half-square side offset → dest centre.
    """
    start_x, start_y = board_square_center_mm(from_square)
    side_dx, side_dy = _delta_mm(side_direction, HALF_SQUARE_MM)
    long_dx, long_dy = _delta_mm(long_direction, LONG_LEG_MM)
    dest_x, dest_y = board_square_center_mm(to_square)

    p1 = _add_mm(start_x, start_y, side_dx, side_dy)
    p2 = _add_mm(p1[0], p1[1], long_dx, long_dy)
    p3 = _clamp_physical(dest_x, dest_y)
    return [p1, p2, p3]


def plan_knight_transport(
    from_square: str,
    to_square: str,
    occupied: Set[str],
) -> tuple[list[tuple[float, float]], PathMode, list[str], str, str]:
    """
    Plan physical waypoints after pickup at *from_square*.

    Returns (waypoints_mm, mode, occupied_on_long_leg, long_direction, side_direction).
    """
    long_dir, side_dir, lf, lr, _, _ = _knight_axes(from_square, to_square)
    blocked = _occupied_on_long_leg(from_square, to_square, occupied, lf, lr)

    if blocked:
        waypoints = _offset_waypoints_mm(
            from_square,
            to_square,
            long_direction=long_dir,
            side_direction=side_dir,
        )
        return waypoints, "offset", blocked, long_dir, side_dir

    waypoints = _direct_waypoints_mm(from_square, to_square)
    return waypoints, "direct", [], long_dir, side_dir


def log_knight_plan(
    from_square: str,
    to_square: str,
    mode: PathMode,
    waypoints: list[tuple[float, float]],
    occupied_detected: list[str],
    long_direction: str,
    side_direction: str,
) -> None:
    print(f"[Knight] start={from_square} target={to_square}", flush=True)
    print(f"[Knight] long_direction={long_direction} side_direction={side_direction}", flush=True)
    print(f"[Knight] mode={mode}", flush=True)
    if occupied_detected:
        print(
            f"[Knight] occupied squares detected: {', '.join(sorted(occupied_detected))}",
            flush=True,
        )
    else:
        print("[Knight] occupied squares detected: (none)", flush=True)
    for i, (x, y) in enumerate(waypoints, start=1):
        print(f"[Knight]   waypoint {i}: X{x:.3f} Y{y:.3f}", flush=True)
