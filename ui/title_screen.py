"""Simple animated title screen overlay for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import pygame
from OpenGL import GL as gl

Vec2 = Tuple[int, int]


@dataclass
class TitleButton:
    label: str
    action: str
    rect: pygame.Rect


class TitleScreen:
    """Fullscreen title overlay with start/exit controls."""

    def __init__(self, window_size: Tuple[int, int]) -> None:
        pygame.font.init()
        self._title_font = pygame.font.SysFont("Consolas", 72)
        self._subtitle_font = pygame.font.SysFont("Consolas", 28)
        self._button_font = pygame.font.SysFont("Consolas", 30)
        self._window_size = window_size
        self._buttons: List[TitleButton] = []
        self.update_layout(window_size)

    def update_layout(self, window_size: Tuple[int, int]) -> None:
        self._window_size = window_size
        width, height = window_size
        button_width = min(420, max(240, int(width * 0.3)))
        button_height = 64
        button_x = int((width - button_width) * 0.5)
        first_y = int(height * 0.55)
        spacing = 96
        labels: Sequence[Tuple[str, str]] = (
            ("Begin Simulation", "start"),
            ("Exit", "exit"),
        )
        buttons: List[TitleButton] = []
        for index, (label, action) in enumerate(labels):
            top = first_y + index * spacing
            buttons.append(
                TitleButton(
                    label=label,
                    action=action,
                    rect=pygame.Rect(button_x, top, button_width, button_height),
                )
            )
        self._buttons = buttons

    def handle_mouse_click(self, pos: Vec2) -> Optional[str]:
        for button in self._buttons:
            if button.rect.collidepoint(pos):
                return button.action
        return None

    def draw(self) -> None:
        width, height = self._window_size
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self._draw_background(width, height)
        self._draw_title(width)
        self._draw_buttons()

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

    def _draw_background(self, width: int, height: int) -> None:
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.02, 0.025, 0.05, 1.0)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glColor4f(0.01, 0.01, 0.02, 1.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

        gl.glColor4f(0.15, 0.32, 0.6, 0.25)
        gl.glLineWidth(2.0)
        padding = 24
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(padding, padding)
        gl.glVertex2f(width - padding, padding)
        gl.glVertex2f(width - padding, height - padding)
        gl.glVertex2f(padding, height - padding)
        gl.glEnd()

    def _draw_title(self, width: int) -> None:
        center_x = width * 0.5
        self._draw_text_centered(center_x, 160, "Cosmogenesis", self._title_font)
        self._draw_text_centered(
            center_x,
            220,
            "Prototype Fleet Command Simulation",
            self._subtitle_font,
        )

    def _draw_buttons(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for button in self._buttons:
            hovered = button.rect.collidepoint(mouse_pos)
            if hovered:
                fill = (0.18, 0.32, 0.52, 0.95)
                border = (0.65, 0.82, 1.0, 1.0)
            else:
                fill = (0.11, 0.18, 0.3, 0.92)
                border = (0.4, 0.5, 0.72, 1.0)
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
                button.rect.centery - 16,
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
