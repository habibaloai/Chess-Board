"""
Pygame chessboard GUI — board, turn/status bar, and window icon.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import chess
import pygame

from chess_voice_robot import config
from chess_voice_robot.ui.icon import create_chess_icon


@dataclass
class StatusDisplay:
    """What to show in the top status bar (online-chess style)."""

    title: str = "Voice Chess"
    subtitle: str = ""
    accent_color: Tuple[int, int, int] = config.COLOR_WAIT
    show_mic: bool = False
    pulse: bool = False


class BoardGUI:
    """
    Renders the board from a python-chess Board object.
    Each square shows its coordinate (a1–h8).
    Status bar shows whose turn it is and when to speak.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)
        icon = create_chess_icon(64)
        pygame.display.set_icon(icon)

        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self._font_label = pygame.font.SysFont("arial", config.LABEL_FONT_SIZE)
        self._font_status = pygame.font.SysFont("arial", config.STATUS_FONT_SIZE, bold=True)
        self._font_status_sub = pygame.font.SysFont("arial", config.STATUS_SUB_FONT_SIZE)
        piece_font_names = ["segoeuisymbol", "Apple Symbols", "DejaVu Sans", "arial"]
        self._font_piece = None
        for name in piece_font_names:
            path = pygame.font.match_font(name)
            if path:
                self._font_piece = pygame.font.Font(path, config.PIECE_FONT_SIZE)
                break
        if self._font_piece is None:
            self._font_piece = pygame.font.SysFont("arial", config.PIECE_FONT_SIZE)

        self._highlight: Optional[Tuple[str, str]] = None
        self._status = StatusDisplay()
        self._board_offset_y = config.STATUS_BAR_HEIGHT

    def set_status(self, status: StatusDisplay) -> None:
        self._status = status

    def set_last_move_highlight(self, from_sq: Optional[str], to_sq: Optional[str]) -> None:
        self._highlight = (from_sq, to_sq) if from_sq and to_sq else None

    def _square_name(self, file_idx: int, rank_idx: int) -> str:
        return f"{chr(ord('a') + file_idx)}{rank_idx + 1}"

    def _draw_status_bar(self) -> None:
        bar = pygame.Rect(0, 0, config.WINDOW_WIDTH, config.STATUS_BAR_HEIGHT)
        pygame.draw.rect(self.screen, config.COLOR_STATUS_BG, bar)

        # Accent strip on the left (turn color)
        strip_w = 6
        pygame.draw.rect(
            self.screen,
            self._status.accent_color,
            (0, 0, strip_w, config.STATUS_BAR_HEIGHT),
        )

        x_text = strip_w + 12
        y_title = 10

        # Pulsing mic indicator when user should speak
        if self._status.show_mic:
            pulse_on = True
            if self._status.pulse:
                pulse_on = (pygame.time.get_ticks() // 600) % 2 == 0
            mic_color = self._status.accent_color if pulse_on else config.COLOR_STATUS_SUB
            mic = self._font_status.render("🎤", True, mic_color)
            self.screen.blit(mic, (config.WINDOW_WIDTH - 40, 14))

        title = self._font_status.render(self._status.title, True, config.COLOR_STATUS_TEXT)
        self.screen.blit(title, (x_text, y_title))

        if self._status.subtitle:
            sub = self._font_status_sub.render(self._status.subtitle, True, config.COLOR_STATUS_SUB)
            self.screen.blit(sub, (x_text, y_title + 26))

    def _draw_square(self, file_idx: int, rank_idx: int, is_light: bool) -> None:
        x = file_idx * config.SQUARE_SIZE
        y = self._board_offset_y + (7 - rank_idx) * config.SQUARE_SIZE
        color = config.LIGHT_SQUARE if is_light else config.DARK_SQUARE
        rect = pygame.Rect(x, y, config.SQUARE_SIZE, config.SQUARE_SIZE)
        pygame.draw.rect(self.screen, color, rect)

        sq_name = self._square_name(file_idx, rank_idx)
        if self._highlight and sq_name in self._highlight:
            highlight = pygame.Surface((config.SQUARE_SIZE, config.SQUARE_SIZE), pygame.SRCALPHA)
            highlight.fill(config.HIGHLIGHT_LAST_MOVE)
            self.screen.blit(highlight, rect.topleft)

        label_color = config.LABEL_COLOR_DARK if is_light else config.LABEL_COLOR_LIGHT
        label = self._font_label.render(sq_name, True, label_color)
        self.screen.blit(label, (x + 4, y + 4))

    def _draw_piece(self, square: int, piece: chess.Piece) -> None:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        symbol = config.PIECES_UNICODE.get(piece.symbol(), "?")
        x = file_idx * config.SQUARE_SIZE
        y = self._board_offset_y + (7 - rank_idx) * config.SQUARE_SIZE
        text = self._font_piece.render(symbol, True, (0, 0, 0))
        text_rect = text.get_rect(
            center=(x + config.SQUARE_SIZE // 2, y + config.SQUARE_SIZE // 2)
        )
        self.screen.blit(text, text_rect)

    def draw(self, board: chess.Board) -> None:
        self.screen.fill(config.COLOR_STATUS_BG)
        self._draw_status_bar()

        for rank_idx in range(8):
            for file_idx in range(8):
                is_light = (file_idx + rank_idx) % 2 == 0
                self._draw_square(file_idx, rank_idx, is_light)

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                self._draw_piece(square, piece)

        pygame.display.flip()

    def pump_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    def tick(self) -> None:
        self.clock.tick(30)

    def quit(self) -> None:
        pygame.quit()
