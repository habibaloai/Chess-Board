"""
Generate a Wizard Chess window icon (antique gold king).
"""

import pygame


def create_chess_icon(size: int = 64) -> pygame.Surface:
    """Draw a white-king glyph on a dark stone / gold emblem."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    r = max(4, size // 12)
    pygame.draw.rect(surface, (11, 13, 15), (0, 0, size, size), border_radius=r)
    pygame.draw.rect(surface, (32, 35, 39), (2, 2, size - 4, size - 4), border_radius=r)
    pygame.draw.rect(surface, (140, 115, 63), (2, 2, size - 4, size - 4), width=2, border_radius=r)

    font_size = int(size * 0.62)
    king = None
    for name in ("segoeuisymbol", "Apple Symbols", "DejaVu Sans"):
        path = pygame.font.match_font(name)
        if path:
            font = pygame.font.Font(path, font_size)
            king = font.render("♔", True, (214, 197, 160))
            break
    if king is None:
        font = pygame.font.SysFont("arial", font_size, bold=True)
        king = font.render("K", True, (214, 197, 160))

    rect = king.get_rect(center=(size // 2, size // 2 + 1))
    surface.blit(king, rect)
    return surface
