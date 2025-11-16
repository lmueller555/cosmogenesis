"""Layout helpers for Cosmogenesis' bottom HUD panel."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pygame


Vec2 = Tuple[float, float]
Size = Tuple[int, int]


@dataclass
class UILayout:
    """Splits the window into gameplay + UI regions per `ui_guidance`."""

    window_size: Size
    gameplay_ratio: float = 0.8
    selection_ratio: float = 0.45
    minimap_ratio: float = 0.25

    def update(self, window_size: Size) -> None:
        self.window_size = window_size

    @property
    def gameplay_rect(self) -> pygame.Rect:
        width, height = self.window_size
        gameplay_height = int(height * self.gameplay_ratio)
        return pygame.Rect(0, 0, width, gameplay_height)

    @property
    def ui_panel_rect(self) -> pygame.Rect:
        width, height = self.window_size
        gameplay_height = self.gameplay_rect.height
        return pygame.Rect(0, gameplay_height, width, height - gameplay_height)

    @property
    def minimap_column_rect(self) -> pygame.Rect:
        panel = self.ui_panel_rect
        width = int(panel.width * self.minimap_ratio)
        width = max(0, min(width, panel.width))
        return pygame.Rect(panel.right - width, panel.top, width, panel.height)

    @property
    def selection_rect(self) -> pygame.Rect:
        panel = self.ui_panel_rect
        minimap = self.minimap_column_rect
        selection_width = int(panel.width * self.selection_ratio)
        max_width = max(0, panel.width - minimap.width)
        selection_width = max(0, min(selection_width, max_width))
        return pygame.Rect(panel.left, panel.top, selection_width, panel.height)

    @property
    def context_rect(self) -> pygame.Rect:
        panel = self.ui_panel_rect
        minimap = self.minimap_column_rect
        selection = self.selection_rect
        left = selection.right
        right = minimap.left
        width = max(0, right - left)
        return pygame.Rect(left, panel.top, width, panel.height)

    @property
    def minimap_rect(self) -> pygame.Rect:
        """Return a square anchored to the bottom-right HUD corner for the minimap."""

        column = self.minimap_column_rect
        panel = self.ui_panel_rect
        padding = 12

        if panel.height <= 0 or column.width <= 0:
            return pygame.Rect(panel.right, panel.bottom, 0, 0)

        usable_width = max(0, column.width - 2 * padding)
        usable_height = max(0, column.height - 2 * padding)
        size = min(usable_width, usable_height)
        size = max(64, size)
        size = min(size, column.width, column.height)
        left = column.right - size - padding
        top = column.bottom - size - padding
        return pygame.Rect(left, top, size, size)

    def is_in_gameplay(self, point: Vec2) -> bool:
        return self.gameplay_rect.collidepoint(point)

    def is_in_minimap(self, point: Vec2) -> bool:
        return self.minimap_rect.collidepoint(point)

    def clamp_to_gameplay(self, point: Vec2) -> Vec2:
        """Restrict ``point`` to the gameplay viewport bounds."""

        rect = self.gameplay_rect
        x = min(max(point[0], rect.left), rect.right)
        y = min(max(point[1], rect.top), rect.bottom)
        return (x, y)

