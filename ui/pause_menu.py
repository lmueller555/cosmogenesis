"""Simple pause menu overlay for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import pygame
from OpenGL import GL as gl

Vec2 = Tuple[int, int]


@dataclass
class PauseButton:
    label: str
    action: str
    rect: pygame.Rect


class PauseMenu:
    """Modal menu that appears when the game is paused."""

    def __init__(self, window_size: Tuple[int, int]) -> None:
        pygame.font.init()
        self._title_font = pygame.font.SysFont("Consolas", 48)
        self._button_font = pygame.font.SysFont("Consolas", 30)
        self._window_size = window_size
        self._menu_rect = pygame.Rect(0, 0, 0, 0)
        self._buttons: List[PauseButton] = []
        self.visible = False
        self.update_layout(window_size)

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def toggle(self) -> None:
        self.visible = not self.visible

    def update_layout(self, window_size: Tuple[int, int]) -> None:
        self._window_size = window_size
        width, height = window_size
        menu_width = min(520, max(360, int(width * 0.4)))
        menu_height = 280
        left = int((width - menu_width) * 0.5)
        top = int((height - menu_height) * 0.5)
        self._menu_rect = pygame.Rect(left, top, menu_width, menu_height)
        button_width = menu_width - 120
        button_height = 56
        button_x = left + int((menu_width - button_width) * 0.5)
        first_y = top + 110
        spacing = 80
        buttons: List[PauseButton] = []
        labels: Sequence[Tuple[str, str]] = (("Resume", "resume"), ("Quit", "quit"))
        for index, (label, action) in enumerate(labels):
            button_top = first_y + index * spacing
            rect = pygame.Rect(button_x, button_top, button_width, button_height)
            buttons.append(PauseButton(label=label, action=action, rect=rect))
        self._buttons = buttons

    def handle_mouse_click(self, pos: Vec2) -> Optional[str]:
        if not self.visible:
            return None
        for button in self._buttons:
            if button.rect.collidepoint(pos):
                return button.action
        return None

    def draw(self) -> None:
        if not self.visible:
            return
        width, height = self._window_size
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self._draw_fullscreen_overlay(width, height)
        self._draw_menu_panel()

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

    def _draw_fullscreen_overlay(self, width: int, height: int) -> None:
        gl.glColor4f(0.01, 0.01, 0.02, 0.75)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

    def _draw_menu_panel(self) -> None:
        rect = self._menu_rect
        gl.glColor4f(0.05, 0.07, 0.12, 0.95)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(rect.left, rect.top)
        gl.glVertex2f(rect.right, rect.top)
        gl.glVertex2f(rect.right, rect.bottom)
        gl.glVertex2f(rect.left, rect.bottom)
        gl.glEnd()

        gl.glColor4f(0.4, 0.45, 0.65, 1.0)
        gl.glLineWidth(2.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(rect.left + 1, rect.top + 1)
        gl.glVertex2f(rect.right - 1, rect.top + 1)
        gl.glVertex2f(rect.right - 1, rect.bottom - 1)
        gl.glVertex2f(rect.left + 1, rect.bottom - 1)
        gl.glEnd()

        self._draw_title(rect)
        self._draw_buttons()

    def _draw_title(self, rect: pygame.Rect) -> None:
        title = "Main Menu"
        subtitle = "Game paused"
        self._draw_text_centered(rect.centerx, rect.top + 48, title, self._title_font)
        self._draw_text_centered(rect.centerx, rect.top + 86, subtitle, self._button_font)

    def _draw_buttons(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for button in self._buttons:
            hovered = button.rect.collidepoint(mouse_pos)
            if hovered:
                fill = (0.2, 0.35, 0.55, 0.95)
                border = (0.65, 0.8, 1.0, 1.0)
            else:
                fill = (0.12, 0.18, 0.28, 0.92)
                border = (0.45, 0.5, 0.7, 1.0)
            gl.glColor4f(*fill)
            gl.glBegin(gl.GL_QUADS)
            gl.glVertex2f(button.rect.left, button.rect.top)
            gl.glVertex2f(button.rect.right, button.rect.top)
            gl.glVertex2f(button.rect.right, button.rect.bottom)
            gl.glVertex2f(button.rect.left, button.rect.bottom)
            gl.glEnd()
            gl.glColor4f(*border)
            gl.glBegin(gl.GL_LINE_LOOP)
            gl.glVertex2f(button.rect.left + 1, button.rect.top + 1)
            gl.glVertex2f(button.rect.right - 1, button.rect.top + 1)
            gl.glVertex2f(button.rect.right - 1, button.rect.bottom - 1)
            gl.glVertex2f(button.rect.left + 1, button.rect.bottom - 1)
            gl.glEnd()
            self._draw_text_centered(
                button.rect.centerx,
                button.rect.centery - 14,
                button.label,
                self._button_font,
            )

    def _draw_text_centered(
        self, center_x: float, y: float, text: str, font: pygame.font.Font
    ) -> None:
        surface = font.render(text, True, (230, 235, 255))
        data = pygame.image.tostring(surface, "RGBA", True)
        x = center_x - surface.get_width() * 0.5
        gl.glRasterPos2f(x, y)
        gl.glDrawPixels(
            surface.get_width(),
            surface.get_height(),
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            data,
        )
