"""
GRBL serial robot — moves the physical carriage when the game calls move().
"""

import time
from typing import Optional

import serial

from chess_voice_robot import config
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
        time.sleep(config.SERIAL_OPEN_DELAY)
        self._init_grbl()

    def _init_grbl(self) -> None:
        self.ser.write(b"\r\n")
        if config.GRBL_UNLOCK_ON_START:
            self.send("$X")  # unlock after alarm/homing

    def send(self, cmd: str) -> None:
        cmd = cmd.strip() + "\n"
        self.ser.write(cmd.encode())
        if config.GRBL_WAIT_FOR_OK:
            self._wait_for_ok()

    def _wait_for_ok(self) -> None:
        deadline = time.monotonic() + config.GRBL_RESPONSE_TIMEOUT
        while time.monotonic() < deadline:
            line = self._readline()
            if not line:
                continue
            if line == "ok":
                return
            if line.startswith("error"):
                print(f"[GRBL] {line}")
                return
        print("[GRBL] Timed out waiting for ok")

    def _readline(self) -> Optional[str]:
        raw = self.ser.readline()
        if not raw:
            return None
        return raw.decode(errors="ignore").strip()

    def close(self) -> None:
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
        self._current_square = config.HOME_SQUARE

    def move(self, from_square: str, to_square: str) -> None:
        print(f"[Robot] Moving {from_square} -> {to_square}")

        self._goto_square(from_square)
        self.pick_up(from_square)
        self._goto_square(to_square)
        self.drop(to_square)

        self._current_square = to_square

    def pick_up(self, square: str) -> None:
        print(f"[Robot] Pick up at {square}")
        # Hook for electromagnet / gripper later

    def drop(self, square: str) -> None:
        print(f"[Robot] Drop at {square}")
        # Hook for electromagnet / gripper later

    def _goto_square(self, square: str) -> None:
        x_mm, y_mm = self._square_to_mm(square)
        print(f"[Robot] Goto {square} -> X{x_mm:.2f} Y{y_mm:.2f}")

        self.grbl.send("G90")  # absolute positioning
        if self.feed_rate > 0:
            self.grbl.send(f"G0 X{x_mm:.3f} Y{y_mm:.3f} F{self.feed_rate}")
        else:
            self.grbl.send(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")

        time.sleep(config.MOVE_SETTLE_TIME)

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
        bot.close()
