"""
Abstract robot interface — swap Simulator for real hardware later.
"""

from abc import ABC, abstractmethod


class RobotInterface(ABC):
    """
    Future physical robot must implement move().
    Core game logic only talks to this interface, never to serial/GPIO directly.
    """

    @abstractmethod
    def move(self, from_square: str, to_square: str) -> None:
        """
        Command the robot to move a piece from one square to another.
        Squares use algebraic notation: e2, e4, a1, etc.
        """
        pass

    def pick_up(self, square: str) -> None:
        """Optional: grasp piece at square (hardware may override)."""
        pass

    def drop(self, square: str) -> None:
        """Optional: release piece at square (hardware may override)."""
        pass

    def go_home(self) -> None:
        """Return carriage to the bottom-left corner of the board (park / home position)."""
        pass

    def emergency_stop(self) -> None:
        """Halt motion immediately (GRBL feed hold on real hardware)."""
        pass
