"""
GRBL serial robot — moves the physical carriage when the game calls move().
"""

import re
import threading
import time
from typing import AbstractSet, Callable, Optional

import serial

from chess_voice_robot import config
from chess_voice_robot.robot.capture_removal import plan_capture_removal
from chess_voice_robot.robot.knight_path import (
    is_knight_move,
    log_knight_plan,
    plan_knight_transport,
)
from chess_voice_robot.robot.grbl_log import log_command
from chess_voice_robot.robot.interface import RobotInterface


class GRBLController:
    """Low-level serial communication with a GRBL-based Arduino."""

    def __init__(
        self,
        port: str = config.SERIAL_PORT,
        baud: int = config.SERIAL_BAUD,
        timeout: float = config.SERIAL_TIMEOUT,
    ) -> None:
        self.ser = serial.Serial(port, baud, timeout=timeout)
        self._lock = threading.Lock()
        time.sleep(config.SERIAL_OPEN_DELAY)
        self._init_grbl()

    def _init_grbl(self) -> None:
        with self._lock:
            self.ser.write(b"\r\n")
        if config.GRBL_UNLOCK_ON_START:
            self.send("$X")  # unlock after alarm/homing

    def send(self, cmd: str, *, abort_check: Optional[Callable[[], bool]] = None) -> bool:
        """Send a G-code line. Returns False if aborted before completion."""
        if abort_check and abort_check():
            return False
        with self._lock:
            if abort_check and abort_check():
                return False
            line = cmd.strip()
            log_command(line)
            self.ser.write((line + "\n").encode())
        if config.GRBL_WAIT_FOR_OK:
            return self._wait_for_ok(abort_check=abort_check)
        return True

    def feed_hold(self) -> None:
        """GRBL real-time feed hold — decelerate and stop motion immediately."""
        with self._lock:
            self.ser.write(b"!")
            self.ser.flush()

    def query_status(self) -> Optional[str]:
        """Request a real-time status report (send ?). Returns e.g. '<Idle|MPos:...>'."""
        with self._lock:
            self.ser.write(b"?")
            self.ser.flush()
            deadline = time.monotonic() + config.GRBL_RESPONSE_TIMEOUT
            buf = ""
            while time.monotonic() < deadline:
                if self.ser.in_waiting:
                    buf += self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                    match = re.search(r"<[^>]+>", buf)
                    if match:
                        return match.group(0)
                time.sleep(config.GRBL_IDLE_POLL_INTERVAL)
        return None

    @staticmethod
    def _status_state(status: str) -> Optional[str]:
        if not status.startswith("<") or "|" not in status:
            return None
        return status[1:].split("|", 1)[0]

    def wait_until_idle(
        self,
        *,
        timeout: Optional[float] = None,
        abort_check: Optional[Callable[[], bool]] = None,
    ) -> bool:
        """Block until GRBL reports Idle (motors finished) or timeout."""
        if not config.GRBL_WAIT_FOR_IDLE:
            return True

        deadline = time.monotonic() + (timeout or config.GRBL_IDLE_TIMEOUT)
        while time.monotonic() < deadline:
            if abort_check and abort_check():
                return False
            status = self.query_status()
            if status:
                state = self._status_state(status)
                if state in ("Idle", "Hold"):
                    return True
            time.sleep(config.GRBL_IDLE_POLL_INTERVAL)

        return False

    def _wait_for_ok(self, *, abort_check: Optional[Callable[[], bool]] = None) -> bool:
        deadline = time.monotonic() + config.GRBL_RESPONSE_TIMEOUT
        while time.monotonic() < deadline:
            if abort_check and abort_check():
                return False
            line = self._readline()
            if not line:
                continue
            if line.startswith("<"):
                continue
            if line == "ok":
                return True
            if line.startswith("error"):
                return False
        return False

    def _readline(self) -> Optional[str]:
        with self._lock:
            raw = self.ser.readline()
        if not raw:
            return None
        return raw.decode(errors="ignore").strip()

    def close(self) -> None:
        with self._lock:
            self.ser.close()


class SerialRobot(RobotInterface):
    """
    Chess robot driver: converts algebraic squares (e2, e4) to GRBL coordinates.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        square_size_mm: Optional[float] = None,
        origin_x_mm: Optional[float] = None,
        origin_y_mm: Optional[float] = None,
    ) -> None:
        self.port = port or config.SERIAL_PORT
        self.square_size_mm = square_size_mm or config.SQUARE_SIZE_MM
        self.origin_x_mm = origin_x_mm if origin_x_mm is not None else config.BOARD_ORIGIN_X_MM
        self.origin_y_mm = origin_y_mm if origin_y_mm is not None else config.BOARD_ORIGIN_Y_MM
        self.x_direction = config.X_AXIS_DIRECTION
        self.y_direction = config.Y_AXIS_DIRECTION
        self.feed_rate = config.MOVE_FEED_RATE

        self.grbl = GRBLController(port=self.port)
        self._current_square: Optional[str] = None
        self._abort = False
        self._zero_work_coordinates()

    def _zero_work_coordinates(self) -> None:
        """Set GRBL work coordinates to the park position at the current carriage position."""
        if not config.GRBL_ZERO_ON_START:
            return
        cmd = (
            f"G92 X{config.HOME_WORK_X_MM:.3f} Y{config.HOME_WORK_Y_MM:.3f}"
        )
        if not self.grbl.send(cmd):
            print(f"[Robot] Warning: work zero failed ({cmd})")

    def emergency_stop(self) -> None:
        self._abort = True
        self.grbl.feed_hold()

    def _aborted(self) -> bool:
        return self._abort

    def move(
        self,
        from_square: str,
        to_square: str,
        *,
        captured_square: Optional[str] = None,
        occupied_squares: Optional[AbstractSet[str]] = None,
        moving_piece: Optional[str] = None,
    ) -> None:
        self._abort = False

        if captured_square:
            if not self._remove_captured_piece(captured_square, occupied_squares or set()):
                return
            if self._aborted():
                return

        if not self._goto_square(from_square):
            return
        if self._aborted():
            return
        self.pick_up(from_square)
        if self._aborted():
            return
        if not self._goto_transport(
            from_square,
            to_square,
            occupied_squares,
            moving_piece,
        ):
            return
        if self._aborted():
            return
        self.drop(to_square)

        if not self._aborted():
            self._current_square = to_square

    def _remove_captured_piece(
        self,
        captured_square: str,
        occupied_squares: AbstractSet[str],
    ) -> bool:
        """Pick up a captured piece and slide it off the board along a rank edge."""
        if not self._goto_square(captured_square):
            return False
        if self._aborted():
            return False
        self.pick_up(captured_square)
        if self._aborted():
            return False

        for x_mm, y_mm in plan_capture_removal(captured_square, set(occupied_squares)):
            if not self._goto_mm(x_mm, y_mm):
                return False
            if self._aborted():
                return False

        self.drop(captured_square)
        return not self._aborted()

    def _goto_transport(
        self,
        from_square: str,
        to_square: str,
        occupied_squares: Optional[AbstractSet[str]],
        moving_piece: Optional[str],
    ) -> bool:
        if (
            moving_piece in ("N", "n")
            and is_knight_move(from_square, to_square)
        ):
            occupied = set(occupied_squares or ())
            waypoints, mode, occupied_detected, long_dir, side_dir = plan_knight_transport(
                from_square, to_square, occupied
            )
            log_knight_plan(
                from_square, to_square, mode, waypoints, occupied_detected, long_dir, side_dir
            )
            for x_mm, y_mm in waypoints:
                if not self._goto_mm(x_mm, y_mm):
                    return False
                if self._aborted():
                    return False
            return True
        return self._goto_square(to_square)

    def go_home(self) -> None:
        self._abort = False
        self.grbl.send("M5", abort_check=self._aborted)
        if not self._goto_mm(config.HOME_WORK_X_MM, config.HOME_WORK_Y_MM):
            return
        if not self._aborted():
            self._current_square = "a1"

    def pick_up(self, square: str) -> None:
        """Engage electromagnet at the piece's start square (after carriage arrives)."""
        if self._aborted():
            return
        self.grbl.send("M3S1000", abort_check=self._aborted)

    def drop(self, square: str) -> None:
        """Release electromagnet at the piece's destination square (after carriage arrives)."""
        if self._aborted():
            return
        self.grbl.send("M5", abort_check=self._aborted)

    def _goto_mm(self, x_mm: float, y_mm: float) -> bool:
        if self._aborted():
            return False

        if not self.grbl.send("G90", abort_check=self._aborted):
            return False
        if self.feed_rate > 0:
            cmd = f"G0 X{x_mm:.3f} Y{y_mm:.3f} F{self.feed_rate}"
        else:
            cmd = f"G0 X{x_mm:.3f} Y{y_mm:.3f}"
        if not self.grbl.send(cmd, abort_check=self._aborted):
            return False
        if not self.grbl.wait_until_idle(abort_check=self._aborted):
            return False

        if config.MOVE_SETTLE_TIME > 0:
            deadline = time.monotonic() + config.MOVE_SETTLE_TIME
            while time.monotonic() < deadline:
                if self._aborted():
                    return False
                time.sleep(0.05)
        return True

    def _goto_square(self, square: str) -> bool:
        x_mm, y_mm = self._square_to_mm(square)
        x_mm += config.ORIGIN_OFFSET_X_MM
        y_mm += config.ORIGIN_OFFSET_Y_MM
        return self._goto_mm(x_mm, y_mm)

    def _square_to_mm(self, square: str) -> tuple[float, float]:
        file = ord(square[0].lower()) - ord("a")  # a=0 ... h=7
        rank = int(square[1]) - 1                  # 1=0 ... 8=7

        x = self.origin_x_mm + (file * self.square_size_mm * self.x_direction)
        y = self.origin_y_mm + (rank * self.square_size_mm * self.y_direction)
        return x, y

    def close(self) -> None:
        self.grbl.close()


if __name__ == "__main__":
    bot = SerialRobot()
    try:
        bot.move("e2", "e4")
    finally:
        bot.go_home()
        bot.close()
