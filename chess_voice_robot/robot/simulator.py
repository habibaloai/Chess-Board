"""
Robot simulator — no hardware; moves are no-ops.
"""

from chess_voice_robot.robot.interface import RobotInterface


class RobotSimulator(RobotInterface):
    """Stand-in for a physical chess robot."""

    def move(self, from_square: str, to_square: str) -> None:
        self.pick_up(from_square)
        self.drop(to_square)

    def pick_up(self, square: str) -> None:
        pass

    def drop(self, square: str) -> None:
        pass

    def emergency_stop(self) -> None:
        pass
