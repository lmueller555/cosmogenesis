"""Simple animated title screen overlay for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import math

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
        self._planet_angle = 0.0
        self._last_tick = pygame.time.get_ticks()
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
            ("Campaign", "campaign"),
            ("Free Play", "start"),
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
        current_tick = pygame.time.get_ticks()
        delta = (current_tick - self._last_tick) * 0.001
        self._last_tick = current_tick
        self._planet_angle = (self._planet_angle + delta * 0.075) % (
            math.tau if hasattr(math, "tau") else (2 * math.pi)
        )
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

        self._draw_planet(width, height)

        gl.glColor4f(0.15, 0.32, 0.6, 0.25)
        gl.glLineWidth(2.0)
        padding = 24
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(padding, padding)
        gl.glVertex2f(width - padding, padding)
        gl.glVertex2f(width - padding, height - padding)
        gl.glVertex2f(padding, height - padding)
        gl.glEnd()

    def _draw_planet(self, width: int, height: int) -> None:
        radius = min(width, height) * 0.9
        center_x = width * 0.78
        center_y = height * 0.38
        vertical_scale = 0.82

        # Soft glow behind the wireframe
        gl.glColor4f(0.06, 0.2, 0.45, 0.3)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex2f(center_x, center_y)
        glow_radius = radius * 1.1
        for i in range(361):
            angle = math.radians(i)
            x = center_x + math.cos(angle) * glow_radius
            y = center_y + math.sin(angle) * glow_radius * vertical_scale
            gl.glVertex2f(x, y)
        gl.glEnd()

        self._draw_ring_system(center_x, center_y, radius, vertical_scale)

        gl.glLineWidth(1.5)
        gl.glColor4f(0.3, 0.55, 0.95, 0.35)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(360):
            angle = math.radians(i)
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius * vertical_scale
            gl.glVertex2f(x, y)
        gl.glEnd()

        # Latitude rings
        gl.glColor4f(0.25, 0.45, 0.9, 0.25)
        latitudes = [i * 0.15 - 0.75 for i in range(11)]
        for lat in latitudes:
            lat_radius = radius * math.cos(lat)
            lat_y = center_y + math.sin(lat) * radius * vertical_scale
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(480):
                angle = math.radians(i * (360 / 480))
                x = center_x + math.cos(angle) * lat_radius
                y = lat_y + math.sin(angle) * radius * 0.02
                gl.glVertex2f(x, y)
            gl.glEnd()

        # Longitude curves rotate slowly to simulate spinning
        gl.glColor4f(0.35, 0.7, 1.0, 0.25)
        longitudes = [math.pi / 8 * i for i in range(-8, 9)]
        for lon in longitudes:
            lon_angle = lon + self._planet_angle
            gl.glBegin(gl.GL_LINE_STRIP)
            for lat_deg in range(-90, 91, 2):
                lat = math.radians(lat_deg)
                x = center_x + math.cos(lat) * math.cos(lon_angle) * radius
                y = center_y + math.sin(lat) * radius * vertical_scale
                gl.glVertex2f(x, y)
            gl.glEnd()

        # Secondary rim highlight
        gl.glColor4f(0.45, 0.8, 1.0, 0.15)
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(360):
            angle = math.radians(i)
            x = center_x + math.cos(angle) * radius * 1.03
            y = center_y + math.sin(angle) * radius * vertical_scale * 1.03
            gl.glVertex2f(x, y)
        gl.glEnd()

    def _draw_ring_system(
        self, center_x: float, center_y: float, radius: float, vertical_scale: float
    ) -> None:
        """Render a dotted halo of rings that rotates around the planet."""

        ring_tilt = math.radians(32.0)
        ring_rotation = self._planet_angle * 0.6
        gl.glPointSize(2.4)

        def draw_ring(ring_radius: float, base_alpha: float) -> None:
            gl.glBegin(gl.GL_POINTS)
            for degrees in range(0, 360, 2):
                angle = math.radians(degrees) + ring_rotation
                cos_angle = math.cos(angle)
                sin_angle = math.sin(angle)

                x = center_x + cos_angle * ring_radius
                y_offset = sin_angle * ring_radius * math.sin(ring_tilt)
                y = center_y + y_offset * vertical_scale

                depth = sin_angle * math.cos(ring_tilt)
                normalized_depth = (depth / math.cos(ring_tilt) + 1.0) * 0.5
                alpha = base_alpha * (0.45 + 0.55 * normalized_depth)
                brightness = 0.55 + 0.35 * normalized_depth
                gl.glColor4f(0.25 + 0.25 * brightness, 0.6 + 0.2 * brightness, 1.0, alpha)
                gl.glVertex2f(x, y)
            gl.glEnd()

        draw_ring(radius * 1.5, 0.28)
        draw_ring(radius * 1.35, 0.35)
        draw_ring(radius * 1.2, 0.3)
        draw_ring(radius * 1.05, 0.18)

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
