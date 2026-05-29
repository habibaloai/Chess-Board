"""
Generate a chess-piece window icon (white king) for pygame.
"""

import pygame


def create_chess_icon(size: int = 64) -> pygame.Surface:
    """Draw a simple white-king logo on a dark green board-style background."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    # Board-green background with rounded feel
    r = max(4, size // 12)
    pygame.draw.rect(surface, (46, 82, 54), (0, 0, size, size), border_radius=r)
    pygame.draw.rect(surface, (240, 217, 181), (2, 2, size - 4, size - 4), width=2, border_radius=r)

    # King glyph — try Unicode, else simple shapes
    font_size = int(size * 0.62)
    king = None
    for name in ("segoeuisymbol", "Apple Symbols", "DejaVu Sans"):
        path = pygame.font.match_font(name)
        if path:
            font = pygame.font.Font(path, font_size)
            king = font.render("♔", True, (30, 30, 30))
            break
    if king is None:
        font = pygame.font.SysFont("arial", font_size, bold=True)
        king = font.render("K", True, (30, 30, 30))

    rect = king.get_rect(center=(size // 2, size // 2 + 1))
    surface.blit(king, rect)
    return surface
