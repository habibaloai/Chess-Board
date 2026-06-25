"""
Pygame chessboard GUI — board, turn/status bar, and window icon.
"""

import os
from dataclasses import dataclass
from typing import Callable, Optional, Set, Tuple

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
    Status bar shows whose turn it is and when to speak or click.
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
        self._font_estop = pygame.font.SysFont("arial", config.ESTOP_FONT_SIZE, bold=True)
        self._font_mic = pygame.font.SysFont("arial", 22)
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
        self._board_offset_x = (config.WINDOW_WIDTH - config.BOARD_SIZE) // 2
        self._board_offset_y = (config.WINDOW_HEIGHT - config.BOARD_SIZE) // 2
        self._background = self._load_background()
        self._estop_pressed = False
        self._estop_rect = pygame.Rect(
            config.WINDOW_WIDTH - config.ESTOP_BUTTON_WIDTH - 10,
            (config.STATUS_BAR_HEIGHT - config.ESTOP_BUTTON_HEIGHT) // 2,
            config.ESTOP_BUTTON_WIDTH,
            config.ESTOP_BUTTON_HEIGHT,
        )
        self._mic_rect = pygame.Rect(
            self._estop_rect.left - config.MIC_BUTTON_SIZE - 8,
            (config.STATUS_BAR_HEIGHT - config.MIC_BUTTON_SIZE) // 2,
            config.MIC_BUTTON_SIZE,
            config.MIC_BUTTON_SIZE,
        )
        self._mic_hit_rect = self._mic_rect.inflate(
            config.MIC_HIT_PADDING, config.MIC_HIT_PADDING
        )

        self._speech_recognition_enabled = True
        self._selected_square: Optional[str] = None
        self._legal_targets: Set[str] = set()
        self._illegal_flash_squares: Set[str] = set()
        self._illegal_flash_until_ms = 0

    def _load_background(self) -> Optional[pygame.Surface]:
        path = config.BACKGROUND_IMAGE
        if not os.path.isfile(path):
            return None
        image = pygame.image.load(path).convert()
        return pygame.transform.smoothscale(
            image, (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        )

    @property
    def speech_recognition_enabled(self) -> bool:
        return self._speech_recognition_enabled

    @property
    def mouse_input_enabled(self) -> bool:
        return not self._speech_recognition_enabled

    def set_status(self, status: StatusDisplay) -> None:
        self._status = status

    def set_last_move_highlight(self, from_sq: Optional[str], to_sq: Optional[str]) -> None:
        self._highlight = (from_sq, to_sq) if from_sq and to_sq else None

    def set_selection(self, from_sq: Optional[str], legal_targets: Set[str]) -> None:
        self._selected_square = from_sq
        self._legal_targets = set(legal_targets)

    def clear_selection(self) -> None:
        self._selected_square = None
        self._legal_targets = set()

    def flash_illegal(self, squares: Set[str]) -> None:
        self._illegal_flash_squares = set(squares)
        self._illegal_flash_until_ms = pygame.time.get_ticks() + config.INVALID_MOVE_FLASH_MS

    def toggle_speech(self) -> bool:
        """Toggle speech recognition on/off. Returns new speech-enabled state."""
        self._speech_recognition_enabled = not self._speech_recognition_enabled
        self.clear_selection()
        return self._speech_recognition_enabled

    def square_at_pixel(self, pos: Tuple[int, int]) -> Optional[str]:
        x, y = pos
        if (
            x < self._board_offset_x
            or y < self._board_offset_y
            or x >= self._board_offset_x + config.BOARD_SIZE
            or y >= self._board_offset_y + config.BOARD_SIZE
        ):
            return None
        file_idx = (x - self._board_offset_x) // config.SQUARE_SIZE
        board_y = y - self._board_offset_y
        rank_idx = 7 - (board_y // config.SQUARE_SIZE)
        if 0 <= file_idx < 8 and 0 <= rank_idx < 8:
            return self._square_name(file_idx, rank_idx)
        return None

    def _square_name(self, file_idx: int, rank_idx: int) -> str:
        return f"{chr(ord('a') + file_idx)}{rank_idx + 1}"

    def _square_indices(self, square: str) -> Tuple[int, int]:
        file_idx = ord(square[0].lower()) - ord("a")
        rank_idx = int(square[1]) - 1
        return file_idx, rank_idx

    def _square_rect(self, file_idx: int, rank_idx: int) -> pygame.Rect:
        x = self._board_offset_x + file_idx * config.SQUARE_SIZE
        y = self._board_offset_y + (7 - rank_idx) * config.SQUARE_SIZE
        return pygame.Rect(x, y, config.SQUARE_SIZE, config.SQUARE_SIZE)

    def _subtitle_max_width(self) -> int:
        return max(80, self._mic_hit_rect.left - 24)

    def _clip_text(self, font: pygame.font.Font, text: str, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text
        ell = "…"
        trimmed = text
        while trimmed and font.size(trimmed + ell)[0] > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ell if trimmed else ell

    def _draw_status_bar(self) -> None:
        bar = pygame.Rect(0, 0, config.WINDOW_WIDTH, config.STATUS_BAR_HEIGHT)
        pygame.draw.rect(self.screen, config.COLOR_STATUS_BG, bar)

        strip_w = 6
        pygame.draw.rect(
            self.screen,
            self._status.accent_color,
            (0, 0, strip_w, config.STATUS_BAR_HEIGHT),
        )

        x_text = strip_w + 12
        y_title = 10
        max_text_w = self._subtitle_max_width() - x_text

        title = self._font_status.render(self._status.title, True, config.COLOR_STATUS_TEXT)
        self.screen.blit(title, (x_text, y_title))

        if self._status.subtitle:
            clipped = self._clip_text(self._font_status_sub, self._status.subtitle, max_text_w)
            sub = self._font_status_sub.render(clipped, True, config.COLOR_STATUS_SUB)
            self.screen.blit(sub, (x_text, y_title + 26))

        # Buttons drawn last so they sit on top and receive clicks reliably.
        self._draw_mic_button()
        self._draw_estop_button()

    def _draw_mic_button(self) -> None:
        if self._speech_recognition_enabled:
            if self._status.pulse:
                pulse_on = (pygame.time.get_ticks() // 600) % 2 == 0
                bg = config.COLOR_INPUT_TOGGLE_ON if pulse_on else (55, 95, 58)
            else:
                bg = (55, 95, 58)
            icon_color = config.COLOR_STATUS_TEXT
        else:
            bg = config.COLOR_INPUT_TOGGLE_OFF
            icon_color = config.COLOR_STATUS_SUB

        pygame.draw.rect(self.screen, bg, self._mic_rect, border_radius=6)
        pygame.draw.rect(self.screen, (60, 60, 65), self._mic_rect, width=1, border_radius=6)
        icon = self._font_mic.render("🎤", True, icon_color)
        icon_rect = icon.get_rect(center=self._mic_rect.center)
        self.screen.blit(icon, icon_rect)
        if not self._speech_recognition_enabled:
            strike = pygame.Rect(
                self._mic_rect.x + 6,
                self._mic_rect.centery,
                self._mic_rect.width - 12,
                2,
            )
            pygame.draw.rect(self.screen, config.COLOR_INVALID, strike)

    def _draw_estop_button(self) -> None:
        color = config.COLOR_ESTOP_PRESSED if self._estop_pressed else config.COLOR_ESTOP
        pygame.draw.rect(self.screen, color, self._estop_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 0, 0), self._estop_rect, width=1, border_radius=4)
        label = self._font_estop.render("STOP", True, config.COLOR_ESTOP_TEXT)
        label_rect = label.get_rect(center=self._estop_rect.center)
        self.screen.blit(label, label_rect)

    def _draw_square_overlay(self, file_idx: int, rank_idx: int, color: Tuple[int, ...]) -> None:
        rect = self._square_rect(file_idx, rank_idx)
        overlay = pygame.Surface((config.SQUARE_SIZE, config.SQUARE_SIZE), pygame.SRCALPHA)
        overlay.fill(color)
        self.screen.blit(overlay, rect.topleft)

    def _draw_legal_dot(self, file_idx: int, rank_idx: int, *, occupied: bool) -> None:
        rect = self._square_rect(file_idx, rank_idx)
        center = rect.center
        radius = 14 if occupied else 10
        pygame.draw.circle(self.screen, (56, 142, 60), center, radius)
        if not occupied:
            pygame.draw.circle(self.screen, (129, 199, 132), center, radius, width=2)

    def _draw_square(self, file_idx: int, rank_idx: int, is_light: bool, board: chess.Board) -> None:
        rect = self._square_rect(file_idx, rank_idx)
        color = config.LIGHT_SQUARE if is_light else config.DARK_SQUARE
        pygame.draw.rect(self.screen, color, rect)

        sq_name = self._square_name(file_idx, rank_idx)

        now = pygame.time.get_ticks()
        if self._illegal_flash_squares and now < self._illegal_flash_until_ms:
            if sq_name in self._illegal_flash_squares:
                self._draw_square_overlay(file_idx, rank_idx, config.COLOR_ILLEGAL_FLASH)
        elif self._illegal_flash_squares and now >= self._illegal_flash_until_ms:
            self._illegal_flash_squares = set()

        if sq_name == self._selected_square:
            self._draw_square_overlay(file_idx, rank_idx, config.COLOR_SELECTED_SQUARE)
        elif sq_name in self._legal_targets:
            self._draw_square_overlay(file_idx, rank_idx, config.COLOR_LEGAL_MOVE)

        if self._highlight and sq_name in self._highlight:
            highlight = pygame.Surface((config.SQUARE_SIZE, config.SQUARE_SIZE), pygame.SRCALPHA)
            highlight.fill(config.HIGHLIGHT_LAST_MOVE)
            self.screen.blit(highlight, rect.topleft)

        label_color = config.LABEL_COLOR_DARK if is_light else config.LABEL_COLOR_LIGHT
        label = self._font_label.render(sq_name, True, label_color)
        self.screen.blit(label, (rect.x + 4, rect.y + 4))

    def _draw_piece(self, square: int, piece: chess.Piece) -> None:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        symbol = config.PIECES_UNICODE.get(piece.symbol(), "?")
        rect = self._square_rect(file_idx, rank_idx)
        text = self._font_piece.render(symbol, True, (0, 0, 0))
        text_rect = text.get_rect(center=rect.center)
        self.screen.blit(text, text_rect)

    def draw(self, board: chess.Board) -> None:
        if self._background is not None:
            self.screen.blit(self._background, (0, 0))
        else:
            self.screen.fill(config.COLOR_STATUS_BG)
        self._draw_status_bar()

        for rank_idx in range(8):
            for file_idx in range(8):
                is_light = (file_idx + rank_idx) % 2 == 0
                self._draw_square(file_idx, rank_idx, is_light, board)

        for sq_name in self._legal_targets:
            file_idx, rank_idx = self._square_indices(sq_name)
            occupied = board.piece_at(chess.parse_square(sq_name)) is not None
            self._draw_legal_dot(file_idx, rank_idx, occupied=occupied)

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                self._draw_piece(square, piece)

        pygame.display.flip()

    def _mic_clicked(self, pos: Tuple[int, int]) -> bool:
        return self._mic_hit_rect.collidepoint(pos)

    def pump_events(
        self,
        on_estop: Optional[Callable[[], None]] = None,
        on_board_click: Optional[Callable[[str], None]] = None,
        on_mic_toggle: Optional[Callable[[], None]] = None,
    ) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._mic_clicked(event.pos):
                    if on_mic_toggle:
                        on_mic_toggle()
                    continue
                if self._estop_rect.collidepoint(event.pos):
                    self._estop_pressed = True
                    if on_estop:
                        on_estop()
                    continue
                square = self.square_at_pixel(event.pos)
                if square is not None and on_board_click is not None:
                    on_board_click(square)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._estop_pressed:
                    self._estop_pressed = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_m, pygame.K_F2):
                    if on_mic_toggle:
                        on_mic_toggle()
                elif event.key == pygame.K_ESCAPE:
                    if on_estop:
                        on_estop()
        return True

    def tick(self) -> None:
        self.clock.tick(30)

    def quit(self) -> None:
        pygame.quit()
