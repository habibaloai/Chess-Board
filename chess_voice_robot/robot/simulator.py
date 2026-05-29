"""
Robot simulator — prints actions to the console (no hardware).
Replace this class with a serial/Arduino implementation later.
"""

from chess_voice_robot.robot.interface import RobotInterface


class RobotSimulator(RobotInterface):
    """Stand-in for a physical chess robot; logs pick/move/drop steps."""

    def move(self, from_square: str, to_square: str) -> None:
        print(f"Moving piece from {from_square} to {to_square}")
        self.pick_up(from_square)
        self.drop(to_square)

    def pick_up(self, square: str) -> None:
        print(f"Picking up piece at {square}")

    def drop(self, square: str) -> None:
        print(f"Dropping piece at {square}")
