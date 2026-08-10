"""
Pygame chessboard GUI — Wizard Chess theme, responsive layout.
"""

import math
import os
from dataclasses import dataclass
from typing import Callable, Optional, Set, Tuple

import chess
import pygame

from chess_voice_robot import config
from chess_voice_robot.ui.icon import create_chess_icon
from chess_voice_robot.utils import audio


@dataclass
class StatusDisplay:
    """What to show in the top status bar."""

    title: str = "Wizard Chess"
    subtitle: str = ""
    accent_color: Tuple[int, int, int] = config.COLOR_WAIT
    show_mic: bool = False
    pulse: bool = False


class BoardGUI:
    """
    Renders the board from a python-chess Board object.
    Backgrounds use cover scaling; the board stays square and scales with the window.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)
        icon = create_chess_icon(64)
        pygame.display.set_icon(icon)

        self._fullscreen = False
        self._windowed_size = self._default_window_size(config.BACKGROUND_IMAGE)
        self._window_width, self._window_height = self._windowed_size
        self.screen = pygame.display.set_mode(
            (self._window_width, self._window_height),
            pygame.RESIZABLE,
        )
        real_w, real_h = self.screen.get_size()
        self._window_width, self._window_height = real_w, real_h
        self._windowed_size = (real_w, real_h)
        self.clock = pygame.time.Clock()

        self._font_status = pygame.font.SysFont("georgia", config.STATUS_FONT_SIZE, bold=True)
        self._font_status_sub = pygame.font.SysFont("georgia", config.STATUS_SUB_FONT_SIZE)
        self._font_estop = pygame.font.SysFont("georgia", config.ESTOP_FONT_SIZE, bold=True)
        self._font_mic = pygame.font.SysFont("arial", 22)
        self._font_label = pygame.font.SysFont("georgia", config.LABEL_FONT_SIZE)
        self._piece_font_names = ["segoeuisymbol", "Apple Symbols", "DejaVu Sans", "arial"]
        self._font_piece = self._make_piece_font(config.PIECE_FONT_SIZE)

        self._highlight: Optional[Tuple[str, str]] = None
        self._status = StatusDisplay()
        self._background_source = self._load_image(config.BACKGROUND_IMAGE)
        if os.path.normpath(config.LOADING_SCREEN_IMAGE) == os.path.normpath(config.BACKGROUND_IMAGE):
            self._loading_source = self._background_source
        else:
            self._loading_source = self._load_image(config.LOADING_SCREEN_IMAGE)
        self._background: Optional[pygame.Surface] = None
        self._loading_scaled: Optional[pygame.Surface] = None
        self._scaled_size: Optional[Tuple[int, int]] = None
        self._font_loading = pygame.font.SysFont("georgia", 16, bold=True)
        self._square_size = config.SQUARE_SIZE
        self._board_size = config.BOARD_SIZE
        self._board_offset_x = 0
        self._board_offset_y = 0
        self._estop_pressed = False
        self._update_layout()

        self._speech_recognition_enabled = True
        self._selected_square: Optional[str] = None
        self._legal_targets: Set[str] = set()
        self._illegal_flash_squares: Set[str] = set()
        self._illegal_flash_until_ms = 0

    def _make_piece_font(self, size: int) -> pygame.font.Font:
        for name in self._piece_font_names:
            path = pygame.font.match_font(name)
            if path:
                return pygame.font.Font(path, size)
        return pygame.font.SysFont("arial", size)

    @staticmethod
    def _load_image(path: str) -> Optional[pygame.Surface]:
        if not os.path.isfile(path):
            return None
        return pygame.image.load(path).convert()

    @staticmethod
    def _image_size(path: str) -> Optional[Tuple[int, int]]:
        if not os.path.isfile(path):
            return None
        return pygame.image.load(path).get_size()

    def _default_window_size(self, image_path: str) -> Tuple[int, int]:
        """Initial window size from image; free resize afterward (cover handles any ratio)."""
        size = self._image_size(image_path)
        if size is None:
            return config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        img_w, img_h = size
        info = pygame.display.Info()
        max_w = max(640, getattr(info, "current_w", 1280) or 1280)
        max_h = max(360, getattr(info, "current_h", 800) or 800)
        width, height = img_w, img_h
        if width > max_w or height > max_h:
            scale = min(max_w / width, max_h / height)
            width = max(1, int(width * scale))
            height = max(1, int(height * scale))
        return width, height

    @staticmethod
    def _scale_cover(source: pygame.Surface, width: int, height: int) -> pygame.Surface:
        """
        CSS-style background-size: cover; background-position: center.

        scale = max(window/image ratios) → proportional upscale → center-crop.
        Never distort. Never letterbox. Cropping is expected.
        """
        width = max(1, int(width))
        height = max(1, int(height))
        src_w, src_h = source.get_size()
        if src_w <= 0 or src_h <= 0:
            blank = pygame.Surface((width, height))
            blank.fill(config.THEME_SHADOW)
            return blank

        scale = max(width / src_w, height / src_h)
        scaled_w = max(width, math.ceil(src_w * scale))
        scaled_h = max(height, math.ceil(src_h * scale))
        scaled = pygame.transform.smoothscale(source, (scaled_w, scaled_h))

        left = (scaled_w - width) // 2
        top = (scaled_h - height) // 2
        crop = pygame.Rect(left, top, width, height)
        return scaled.subsurface(crop).copy()

    def _refresh_cover_surfaces(self) -> None:
        """Rebuild cached cover blits only when the window pixel size changes."""
        size = (self._window_width, self._window_height)
        if self._scaled_size == size:
            return

        if self._background_source is not None:
            self._background = self._scale_cover(
                self._background_source, self._window_width, self._window_height
            )
        else:
            self._background = None

        if self._loading_source is self._background_source:
            self._loading_scaled = self._background
        elif self._loading_source is not None:
            self._loading_scaled = self._scale_cover(
                self._loading_source, self._window_width, self._window_height
            )
        else:
            self._loading_scaled = None
        self._scaled_size = size

    def _update_layout(self) -> None:
        """
        Single source of truth for chessboard geometry.

        BACKGROUND → cover via max(scale ratios) elsewhere.
        BOARD → fit via min(available_width, available_height); always square.
        """
        margin = 16
        available_width = max(1, self._window_width - margin * 2)
        available_height = max(
            1,
            self._window_height - config.STATUS_BAR_HEIGHT - margin * 2,
        )

        # ONE size for both axes — never scale width/height independently.
        board_size = min(available_width, available_height)
        board_size = max(1, int(board_size * config.BOARD_SCALE))
        square_size = max(1, board_size // 8)
        board_size = square_size * 8

        self._square_size = square_size
        self._board_size = board_size

        free_x = max(0, self._window_width - board_size)
        # Perfectly centered in the window (status bar is above the play area).
        self._board_offset_x = free_x // 2
        self._board_offset_y = (
            config.STATUS_BAR_HEIGHT
            + max(0, (self._window_height - config.STATUS_BAR_HEIGHT - board_size) // 2)
        )

        piece_px = max(12, int(square_size * 0.72))
        self._font_piece = self._make_piece_font(piece_px)
        label_px = max(8, int(square_size * 0.14))
        self._font_label = pygame.font.SysFont("georgia", label_px)

        self._refresh_cover_surfaces()

        # Same-sized controls, vertically centered in the status bar.
        btn = config.MIC_BUTTON_SIZE
        gap = 10
        edge = 12
        bar_top = 10
        bar_h = config.STATUS_BAR_HEIGHT - 18
        btn_y = bar_top + (bar_h - btn) // 2

        self._mic_rect = pygame.Rect(
            self._window_width - btn - edge,
            btn_y,
            btn,
            btn,
        )
        self._mic_hit_rect = self._mic_rect.inflate(
            config.MIC_HIT_PADDING, config.MIC_HIT_PADDING
        )
        self._estop_rect = pygame.Rect(
            self._mic_rect.left - config.ESTOP_BUTTON_WIDTH - gap,
            btn_y,
            config.ESTOP_BUTTON_WIDTH,
            config.ESTOP_BUTTON_HEIGHT,
        )

    def _apply_window_size(self, width: int, height: int, *, fullscreen: Optional[bool] = None) -> None:
        if fullscreen is not None:
            self._fullscreen = fullscreen

        width = max(320, int(width))
        height = max(240, int(height))
        flags = pygame.FULLSCREEN if self._fullscreen else pygame.RESIZABLE

        size_changed = (width, height) != (self._window_width, self._window_height)
        was_fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)
        needs_mode = size_changed or was_fullscreen != self._fullscreen

        self._window_width = width
        self._window_height = height
        if needs_mode:
            self.screen = pygame.display.set_mode((width, height), flags)
            # HiDPI / OS may adjust the real surface size — trust the surface.
            real_w, real_h = self.screen.get_size()
            self._window_width, self._window_height = real_w, real_h
            if not self._fullscreen:
                self._windowed_size = (real_w, real_h)

        self._scaled_size = None  # force cover rebuild for the new size
        self._update_layout()

    def _handle_resize(self, width: int, height: int) -> None:
        if self._fullscreen:
            return
        self._windowed_size = (max(1, width), max(1, height))
        self._apply_window_size(width, height, fullscreen=False)

    def _toggle_fullscreen(self) -> None:
        if self._fullscreen:
            w, h = self._windowed_size
            self._apply_window_size(w, h, fullscreen=False)
        else:
            self._windowed_size = (self._window_width, self._window_height)
            info = pygame.display.Info()
            self._apply_window_size(info.current_w, info.current_h, fullscreen=True)

    def _sync_surface_size(self) -> None:
        """If the OS changed the surface (maximize/fullscreen), recompute layout once."""
        real_w, real_h = self.screen.get_size()
        if (real_w, real_h) == (self._window_width, self._window_height):
            return
        self._window_width, self._window_height = real_w, real_h
        if not self._fullscreen:
            self._windowed_size = (real_w, real_h)
        self._scaled_size = None
        self._update_layout()

    def _blit_cover_image(self, source: Optional[pygame.Surface]) -> None:
        if source is None:
            self.screen.fill(config.THEME_SHADOW)
            return
        framed = self._scale_cover(source, self._window_width, self._window_height)
        self.screen.blit(framed, (0, 0))

    def _draw_loading_bar(self, progress: float) -> None:
        """Antique gold loading bar near the bottom of the splash."""
        progress = max(0.0, min(1.0, progress))
        bar_w = max(160, int(self._window_width * 0.42))
        bar_h = max(10, int(self._window_height * 0.018))
        x = (self._window_width - bar_w) // 2
        y = self._window_height - max(36, int(self._window_height * 0.08))

        track = pygame.Rect(x, y, bar_w, bar_h)
        fill = pygame.Rect(x, y, max(0, int(bar_w * progress)), bar_h)

        # Soft shadow behind the track.
        shadow = track.move(0, 2)
        shadow_surf = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 120))
        self.screen.blit(shadow_surf, shadow.topleft)

        track_surf = pygame.Surface((track.width, track.height), pygame.SRCALPHA)
        track_surf.fill((*config.THEME_SHADOW, 200))
        self.screen.blit(track_surf, track.topleft)
        pygame.draw.rect(self.screen, config.THEME_GOLD_DARK, track, width=1, border_radius=4)

        if fill.width > 0:
            fill_surf = pygame.Surface((fill.width, fill.height), pygame.SRCALPHA)
            fill_surf.fill((*config.THEME_GOLD, 230))
            self.screen.blit(fill_surf, fill.topleft)
            pygame.draw.rect(self.screen, config.THEME_GOLD_BRIGHT, fill, width=1, border_radius=4)

        label = self._font_loading.render("Summoning the board…", True, config.THEME_PARCHMENT)
        label_rect = label.get_rect(midbottom=(self._window_width // 2, y - 8))
        # Soft text shadow for readability on bright art.
        shadow_label = self._font_loading.render("Summoning the board…", True, (0, 0, 0))
        self.screen.blit(shadow_label, label_rect.move(1, 1))
        self.screen.blit(label, label_rect)

    def _paint_loading_frame(self, progress: float, *, show_bar: bool = True) -> None:
        self._sync_surface_size()
        self._refresh_cover_surfaces()
        if self._loading_scaled is not None:
            self.screen.blit(self._loading_scaled, (0, 0))
        elif self._background is not None:
            self.screen.blit(self._background, (0, 0))
        else:
            self._blit_cover_image(self._loading_source or self._background_source)
        if show_bar:
            self._draw_loading_bar(progress)
        pygame.display.flip()

    def show_game_backdrop(self) -> None:
        """Paint the shared scene wallpaper immediately (no board / no loading bar)."""
        self._sync_surface_size()
        self._refresh_cover_surfaces()
        if self._background is not None:
            self.screen.blit(self._background, (0, 0))
        else:
            self._blit_cover_image(self._background_source)
        pygame.display.flip()
        audio.ensure_background_music()

    def show_loading_screen(self, seconds: Optional[float] = None) -> None:
        """Shared scene + progress bar; waits for bar duration AND loading VO to finish."""
        visual_ms = int((seconds if seconds is not None else config.LOADING_SCREEN_SECONDS) * 1000)
        self._update_layout()

        audio_secs = audio.play_loading_screen_audio()
        duration_ms = max(visual_ms, int(audio_secs * 1000) + 50)

        start = pygame.time.get_ticks()
        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start
            progress = 1.0 if duration_ms <= 0 else min(1.0, elapsed / duration_ms)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.show_game_backdrop()
                    return
                if event.type == pygame.VIDEORESIZE:
                    self._handle_resize(event.w, event.h)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self._fullscreen:
                    self._toggle_fullscreen()

            self._paint_loading_frame(progress, show_bar=True)
            audio.ensure_background_music()
            self.clock.tick(30)
            # Stay until the bar finishes and the loading clip has ended.
            if elapsed >= duration_ms and not audio.loading_screen_audio_busy():
                break

        # Loading complete — hide the bar; keep the same background for a seamless handoff.
        self._windowed_size = (self._window_width, self._window_height)
        self._paint_loading_frame(1.0, show_bar=False)
        audio.ensure_background_music()
        self.show_game_backdrop()
        audio.ensure_background_music()

    def _blit_scene_background(self) -> None:
        if self._background is not None:
            self.screen.blit(self._background, (0, 0))
        else:
            self.screen.fill(config.THEME_SHADOW)

    def _draw_board_contents(self, board: chess.Board) -> None:
        """Board frame, squares, markers, pieces (no status bar)."""
        self._draw_board_frame()

        for rank_idx in range(8):
            for file_idx in range(8):
                is_light = (file_idx + rank_idx) % 2 == 0
                self._draw_square(file_idx, rank_idx, is_light, board)

        for sq_name in self._legal_targets:
            file_idx, rank_idx = self._square_indices(sq_name)
            occupied = board.piece_at(chess.parse_square(sq_name)) is not None
            self._draw_legal_marker(file_idx, rank_idx, occupied=occupied)

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                self._draw_piece(square, piece)

    def fade_in_board(self, board: chess.Board, seconds: Optional[float] = None) -> None:
        """Fade the chessboard + status bar in over the shared scene background."""
        duration_ms = int(
            (seconds if seconds is not None else config.BOARD_FADE_IN_SECONDS) * 1000
        )
        start = pygame.time.get_ticks()
        audio.ensure_background_music()

        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start
            progress = 1.0 if duration_ms <= 0 else min(1.0, elapsed / duration_ms)
            alpha = max(0, min(255, int(255 * progress)))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.VIDEORESIZE:
                    self._handle_resize(event.w, event.h)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self._fullscreen:
                    self._toggle_fullscreen()

            self._sync_surface_size()
            self._refresh_cover_surfaces()
            self._blit_scene_background()

            overlay = pygame.Surface(
                (self._window_width, self._window_height), pygame.SRCALPHA
            )
            previous = self.screen
            self.screen = overlay
            try:
                self._draw_board_contents(board)
                self._draw_status_bar()
            finally:
                self.screen = previous

            overlay.set_alpha(alpha)
            self.screen.blit(overlay, (0, 0))
            pygame.display.flip()
            audio.tick_narrator()
            audio.ensure_background_music()
            self.clock.tick(30)

            if elapsed >= duration_ms:
                break

        self.draw(board)

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
            or x >= self._board_offset_x + self._board_size
            or y >= self._board_offset_y + self._board_size
        ):
            return None
        file_idx = (x - self._board_offset_x) // self._square_size
        board_y = y - self._board_offset_y
        rank_idx = 7 - (board_y // self._square_size)
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
        x = self._board_offset_x + file_idx * self._square_size
        y = self._board_offset_y + (7 - rank_idx) * self._square_size
        return pygame.Rect(x, y, self._square_size, self._square_size)

    def _subtitle_max_width(self) -> int:
        return max(80, self._estop_rect.left - 24)

    def _clip_text(self, font: pygame.font.Font, text: str, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text
        ell = "…"
        trimmed = text
        while trimmed and font.size(trimmed + ell)[0] > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ell if trimmed else ell

    def _draw_status_bar(self) -> None:
        pad = 10
        bar = pygame.Rect(
            pad,
            10,
            self._window_width - pad * 2,
            config.STATUS_BAR_HEIGHT - 18,
        )
        panel = pygame.Surface((bar.width, bar.height), pygame.SRCALPHA)
        bg = config.COLOR_STATUS_BG
        if len(bg) == 4:
            panel.fill(bg)
        else:
            panel.fill((*bg, 210))
        self.screen.blit(panel, bar.topleft)
        pygame.draw.rect(self.screen, config.COLOR_STATUS_BORDER, bar, width=1, border_radius=8)

        # Subtle accent mark (not a full bright fill).
        accent = pygame.Rect(bar.x + 12, bar.y + 14, 4, bar.height - 28)
        pygame.draw.rect(self.screen, self._status.accent_color, accent, border_radius=2)

        x_text = bar.x + 26
        y_title = bar.y + 16
        max_text_w = self._subtitle_max_width() - x_text

        title = self._font_status.render(self._status.title, True, config.COLOR_STATUS_TEXT)
        self.screen.blit(title, (x_text, y_title))

        if self._status.subtitle:
            clipped = self._clip_text(self._font_status_sub, self._status.subtitle, max_text_w)
            sub = self._font_status_sub.render(clipped, True, config.COLOR_STATUS_SUB)
            self.screen.blit(sub, (x_text, y_title + 30))

        self._draw_mic_button()
        self._draw_estop_button()

    def _draw_control_button(
        self,
        rect: pygame.Rect,
        *,
        fill: Tuple[int, ...],
        border: Tuple[int, int, int],
    ) -> None:
        if len(fill) == 4:
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            surf.fill(fill)
            self.screen.blit(surf, rect.topleft)
        else:
            pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)

    def _draw_microphone_icon(
        self,
        rect: pygame.Rect,
        color: Tuple[int, int, int],
        *,
        muted: bool,
    ) -> None:
        """Draw a simple microphone glyph centered in *rect*."""
        cx, cy = rect.centerx, rect.centery - 1
        # Capsule body
        head_w = max(8, rect.width // 4)
        head_h = max(12, int(rect.height * 0.42))
        head = pygame.Rect(0, 0, head_w, head_h)
        head.center = (cx, cy - 3)
        pygame.draw.rect(self.screen, color, head, border_radius=head_w // 2)
        # U-shaped yoke under the capsule
        yoke_r = head_w // 2 + 3
        yoke_rect = pygame.Rect(0, 0, yoke_r * 2, yoke_r + 4)
        yoke_rect.midtop = (cx, head.centery)
        pygame.draw.arc(self.screen, color, yoke_rect, 3.1416, 2 * 3.1416, 2)
        # Stem + base
        stem_top = yoke_rect.bottom - 2
        stem_bottom = min(rect.bottom - 8, stem_top + max(6, rect.height // 7))
        pygame.draw.line(self.screen, color, (cx, stem_top), (cx, stem_bottom), 2)
        base_w = max(10, head_w + 6)
        pygame.draw.line(
            self.screen,
            color,
            (cx - base_w // 2, stem_bottom),
            (cx + base_w // 2, stem_bottom),
            2,
        )
        if muted:
            x1, y1 = rect.left + 8, rect.bottom - 10
            x2, y2 = rect.right - 8, rect.top + 10
            pygame.draw.line(self.screen, config.THEME_BURGUNDY_LIGHT, (x1, y1), (x2, y2), 3)

    def _draw_mic_button(self) -> None:
        if self._speech_recognition_enabled:
            if self._status.pulse:
                pulse_on = (pygame.time.get_ticks() // 700) % 2 == 0
                border = config.THEME_GOLD_BRIGHT if pulse_on else config.COLOR_BUTTON_BORDER
            else:
                border = config.COLOR_BUTTON_BORDER
            fill = config.COLOR_BUTTON_BG
            icon_color = config.THEME_PARCHMENT
        else:
            fill = (*config.THEME_SHADOW_LIFT, 230)
            border = config.THEME_STONE_MID
            icon_color = config.THEME_STONE_LIGHT

        self._draw_control_button(self._mic_rect, fill=fill, border=border)
        self._draw_microphone_icon(
            self._mic_rect,
            icon_color,
            muted=not self._speech_recognition_enabled,
        )

    def _draw_estop_button(self) -> None:
        fill = config.COLOR_ESTOP_PRESSED if self._estop_pressed else config.COLOR_ESTOP
        self._draw_control_button(
            self._estop_rect,
            fill=fill,
            border=config.COLOR_ESTOP_BORDER,
        )
        label = self._font_estop.render("STOP", True, config.COLOR_ESTOP_TEXT)
        label_rect = label.get_rect(center=self._estop_rect.center)
        self.screen.blit(label, label_rect)

    def _draw_board_frame(self) -> None:
        frame = 6
        outer = pygame.Rect(
            self._board_offset_x - frame,
            self._board_offset_y - frame,
            self._board_size + frame * 2,
            self._board_size + frame * 2,
        )
        shadow = outer.move(3, 4)
        shadow_surf = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        shadow_surf.fill(config.BOARD_SHADOW)
        self.screen.blit(shadow_surf, shadow.topleft)
        pygame.draw.rect(self.screen, config.BOARD_FRAME_INNER, outer, border_radius=4)
        pygame.draw.rect(self.screen, config.BOARD_FRAME, outer, width=2, border_radius=4)

    def _draw_square_overlay(self, file_idx: int, rank_idx: int, color: Tuple[int, ...]) -> None:
        rect = self._square_rect(file_idx, rank_idx)
        overlay = pygame.Surface((self._square_size, self._square_size), pygame.SRCALPHA)
        overlay.fill(color)
        self.screen.blit(overlay, rect.topleft)

    def _draw_legal_marker(self, file_idx: int, rank_idx: int, *, occupied: bool) -> None:
        rect = self._square_rect(file_idx, rank_idx)
        center = rect.center
        if occupied:
            # Capture: restrained burgundy ring.
            radius = max(8, self._square_size // 2 - 4)
            pygame.draw.circle(self.screen, config.THEME_BURGUNDY_LIGHT, center, radius, width=3)
            pygame.draw.circle(self.screen, config.THEME_GOLD_DARK, center, radius, width=1)
        else:
            radius = max(5, self._square_size // 7)
            pygame.draw.circle(self.screen, config.THEME_GOLD, center, radius)
            pygame.draw.circle(self.screen, config.THEME_GOLD_BRIGHT, center, radius, width=1)

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
            pygame.draw.rect(self.screen, config.THEME_GOLD_BRIGHT, rect, width=2)
        elif sq_name in self._legal_targets:
            self._draw_square_overlay(file_idx, rank_idx, config.COLOR_LEGAL_MOVE)

        if self._highlight and sq_name in self._highlight:
            highlight = pygame.Surface((self._square_size, self._square_size), pygame.SRCALPHA)
            highlight.fill(config.HIGHLIGHT_LAST_MOVE)
            self.screen.blit(highlight, rect.topleft)

        label_color = config.LABEL_COLOR_DARK if is_light else config.LABEL_COLOR_LIGHT
        # Prefer readable labels: light text on dark squares, dark text on light.
        if is_light:
            label_color = config.LABEL_COLOR_LIGHT
        else:
            label_color = config.LABEL_COLOR_DARK
        label = self._font_label.render(sq_name, True, label_color)
        self.screen.blit(label, (rect.x + 3, rect.y + 2))

    def _draw_piece(self, square: int, piece: chess.Piece) -> None:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        symbol = config.PIECES_UNICODE.get(piece.symbol(), "?")
        rect = self._square_rect(file_idx, rank_idx)
        color = config.PIECE_COLOR_LIGHT if piece.color == chess.WHITE else config.PIECE_COLOR_DARK
        # Soft outline for readability on stone squares.
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            outline = self._font_piece.render(symbol, True, config.PIECE_OUTLINE)
            outline_rect = outline.get_rect(center=(rect.centerx + dx, rect.centery + dy))
            self.screen.blit(outline, outline_rect)
        text = self._font_piece.render(symbol, True, color)
        text_rect = text.get_rect(center=rect.center)
        self.screen.blit(text, text_rect)

    def draw(self, board: chess.Board) -> None:
        self._sync_surface_size()
        self._refresh_cover_surfaces()
        self._blit_scene_background()
        self._draw_board_contents(board)
        self._draw_status_bar()
        pygame.display.flip()

    def _mic_clicked(self, pos: Tuple[int, int]) -> bool:
        return self._mic_hit_rect.collidepoint(pos)

    def pump_events(
        self,
        on_estop: Optional[Callable[[], None]] = None,
        on_board_click: Optional[Callable[[str], None]] = None,
        on_mic_toggle: Optional[Callable[[], None]] = None,
    ) -> bool:
        self._sync_surface_size()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.VIDEORESIZE:
                self._handle_resize(event.w, event.h)
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
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                elif event.key in (pygame.K_m, pygame.K_F2):
                    if on_mic_toggle:
                        on_mic_toggle()
                elif event.key == pygame.K_ESCAPE:
                    if self._fullscreen:
                        self._toggle_fullscreen()
                    elif on_estop:
                        on_estop()
        return True

    def tick(self) -> None:
        self.clock.tick(30)

    def quit(self) -> None:
        pygame.quit()
