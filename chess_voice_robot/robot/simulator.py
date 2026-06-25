"""
Robot simulator — no hardware; logs G-code to the terminal like the real robot.
"""

from typing import AbstractSet, Optional

from chess_voice_robot import config
from chess_voice_robot.robot.capture_removal import board_square_center_mm, plan_capture_removal
from chess_voice_robot.robot.grbl_log import log_command
from chess_voice_robot.robot.interface import RobotInterface
from chess_voice_robot.robot.knight_path import (
    is_knight_move,
    log_knight_plan,
    plan_knight_transport,
)


class RobotSimulator(RobotInterface):
    """Stand-in for a physical chess robot."""

    def move(
        self,
        from_square: str,
        to_square: str,
        *,
        captured_square: Optional[str] = None,
        occupied_squares: Optional[AbstractSet[str]] = None,
        moving_piece: Optional[str] = None,
    ) -> None:
        if captured_square:
            self._goto_square(captured_square)
            log_command("M3S1000")
            for x_mm, y_mm in plan_capture_removal(
                captured_square, set(occupied_squares or ())
            ):
                log_command(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")
            log_command("M5")
        self._goto_square(from_square)
        log_command("M3S1000")
        self._goto_transport(from_square, to_square, occupied_squares, moving_piece)
        log_command("M5")

    def _goto_transport(
        self,
        from_square: str,
        to_square: str,
        occupied_squares: Optional[AbstractSet[str]],
        moving_piece: Optional[str],
    ) -> None:
        if moving_piece in ("N", "n") and is_knight_move(from_square, to_square):
            waypoints, mode, occupied_detected, long_dir, side_dir = plan_knight_transport(
                from_square, to_square, set(occupied_squares or ())
            )
            log_knight_plan(
                from_square, to_square, mode, waypoints, occupied_detected, long_dir, side_dir
            )
            for x_mm, y_mm in waypoints:
                log_command(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")
            return
        self._goto_square(to_square)

    @staticmethod
    def _goto_square(square: str) -> None:
        x_mm, y_mm = board_square_center_mm(square)
        log_command("G90")
        log_command(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")

    def pick_up(self, square: str) -> None:
        pass

    def drop(self, square: str) -> None:
        pass

    def emergency_stop(self) -> None:
        pass

    def go_home(self) -> None:
        log_command("M5")
        log_command(f"G0 X{config.HOME_WORK_X_MM:.3f} Y{config.HOME_WORK_Y_MM:.3f}")
