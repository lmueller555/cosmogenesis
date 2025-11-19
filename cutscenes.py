"""Story cutscene definitions for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import List, Tuple

import pygame
from OpenGL import GL as gl

Vec2 = Tuple[float, float]


@dataclass
class Star:
    """Single star used for the backdrop of the opening cutscene."""

    position: Vec2
    base_brightness: float
    twinkle_speed: float
    phase: float


class CampaignOpeningCutscene:
    """Opening cinematic shown before the campaign begins."""

    FADE_IN_DURATION = 3.0
    EARTH_HOLD_DURATION = 10.0
    PAN_DURATION = 8.0
    TOTAL_DURATION = FADE_IN_DURATION + EARTH_HOLD_DURATION + PAN_DURATION + 2.0
    MARS_REVEAL_DELAY = 2.5

    def __init__(self, viewport_size: Tuple[int, int]) -> None:
        pygame.font.init()
        self._viewport_size = viewport_size
        self._elapsed = 0.0
        self._stars: List[Star] = self._generate_starfield(320)
        self._caption_font = pygame.font.SysFont("Consolas", 36)
        self._caption_text = "2150 A.D."

    # ------------------------------------------------------------------
    # Public API
    def reset(self) -> None:
        self._elapsed = 0.0

    def update(self, dt: float) -> None:
        self._elapsed = min(self._elapsed + dt, self.TOTAL_DURATION)

    def draw(self) -> None:
        width, height = self._viewport_size
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self._draw_background()
        self._draw_planets()
        self._draw_caption()
        self._draw_fade_overlay()

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

    def update_viewport(self, viewport_size: Tuple[int, int]) -> None:
        self._viewport_size = viewport_size

    def is_finished(self) -> bool:
        return self._elapsed >= self.TOTAL_DURATION

    # ------------------------------------------------------------------
    # Rendering helpers
    def _draw_background(self) -> None:
        width, height = self._viewport_size
        # Deep space gradient
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.01, 0.01, 0.025, 1.0)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glColor4f(0.0, 0.0, 0.0, 1.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

        # Subtle nebula haze
        gl.glColor4f(0.09, 0.06, 0.18, 0.25)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex2f(width * 0.75, height * 0.35)
        haze_radius = max(width, height) * 0.8
        for angle in range(0, 361, 5):
            rad = math.radians(angle)
            gl.glVertex2f(
                width * 0.75 + math.cos(rad) * haze_radius,
                height * 0.35 + math.sin(rad) * haze_radius * 0.6,
            )
        gl.glEnd()

        gl.glPointSize(2.0)
        gl.glBegin(gl.GL_POINTS)
        for star in self._stars:
            twinkle = math.sin(self._elapsed * star.twinkle_speed + star.phase)
            brightness = max(0.0, min(1.0, star.base_brightness + twinkle * 0.25))
            gl.glColor4f(brightness, brightness, brightness, 1.0)
            gl.glVertex2f(star.position[0] * width, star.position[1] * height)
        gl.glEnd()

    def _draw_planets(self) -> None:
        width, height = self._viewport_size
        earth_radius = min(width, height) * 0.32
        pan_progress = self._pan_progress()

        earth_center = (
            width * (0.55 - 0.45 * pan_progress),
            height * 0.55,
        )
        self._draw_earth(earth_center, earth_radius)

        mars_visibility = self._mars_visibility(pan_progress)
        if mars_visibility <= 0.0:
            return

        mars_radius = earth_radius * 0.38
        mars_center = (
            width * (1.1 - 0.65 * pan_progress),
            height * 0.45,
        )
        self._draw_mars(mars_center, mars_radius, mars_visibility)

    def _draw_earth(self, center: Vec2, radius: float) -> None:
        segments = 240
        light_dir = self._normalized((-0.4, -0.2))
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.12, 0.24, 0.52, 1.0)
        gl.glVertex2f(*center)
        for index in range(segments + 1):
            angle = (index / segments) * math.tau
            normal = (math.cos(angle), math.sin(angle))
            shade = max(0.0, self._dot(normal, light_dir))
            land_mask = 0.5 + 0.5 * math.sin(angle * 3.7 + center[1] * 0.01)
            ocean_color = (0.05, 0.15, 0.4)
            land_color = (0.12, 0.45, 0.22)
            cloud_factor = 0.15 + 0.1 * math.sin(angle * 6.0 + self._elapsed * 0.8)
            r = ocean_color[0] * (1 - land_mask) + land_color[0] * land_mask
            g = ocean_color[1] * (1 - land_mask) + land_color[1] * land_mask
            b = ocean_color[2] * (1 - land_mask) + land_color[2] * land_mask
            r += cloud_factor * 0.5
            g += cloud_factor * 0.5
            b += cloud_factor * 0.5
            brightness = 0.35 + 0.65 * shade
            gl.glColor4f(r * brightness, g * brightness, b * brightness, 1.0)
            gl.glVertex2f(
                center[0] + normal[0] * radius,
                center[1] + normal[1] * radius * 0.98,
            )
        gl.glEnd()

        # Atmospheric glow
        gl.glColor4f(0.3, 0.6, 1.0, 0.18)
        gl.glBegin(gl.GL_LINE_LOOP)
        for index in range(segments):
            angle = (index / segments) * math.tau
            gl.glVertex2f(
                center[0] + math.cos(angle) * radius * 1.04,
                center[1] + math.sin(angle) * radius * 1.02,
            )
        gl.glEnd()

    def _draw_mars(self, center: Vec2, radius: float, visibility: float) -> None:
        segments = 200
        light_dir = self._normalized((-0.35, -0.05))
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.4, 0.15, 0.05, visibility)
        gl.glVertex2f(*center)
        for index in range(segments + 1):
            angle = (index / segments) * math.tau
            normal = (math.cos(angle), math.sin(angle))
            shade = max(0.0, self._dot(normal, light_dir))
            dust_variation = 0.55 + 0.45 * math.sin(angle * 5.0 + self._elapsed * 0.6)
            r = 0.55 * dust_variation
            g = 0.2 * dust_variation
            b = 0.1 + 0.05 * dust_variation
            brightness = 0.25 + 0.75 * shade
            gl.glColor4f(r * brightness, g * brightness, b * brightness, visibility)
            gl.glVertex2f(
                center[0] + normal[0] * radius,
                center[1] + normal[1] * radius * 0.96,
            )
        gl.glEnd()

        gl.glColor4f(0.85, 0.45, 0.2, 0.45 * visibility)
        gl.glBegin(gl.GL_LINE_LOOP)
        for index in range(segments):
            angle = (index / segments) * math.tau
            gl.glVertex2f(
                center[0] + math.cos(angle) * radius * 1.05,
                center[1] + math.sin(angle) * radius * 1.02,
            )
        gl.glEnd()

    def _draw_caption(self) -> None:
        width, height = self._viewport_size
        surface = self._caption_font.render(self._caption_text, True, (235, 235, 240))
        data = pygame.image.tostring(surface, "RGBA", True)
        text_width = surface.get_width()
        x = (width - text_width) * 0.5
        y = height - surface.get_height() - 32
        gl.glRasterPos2f(x, y)
        gl.glDrawPixels(
            surface.get_width(),
            surface.get_height(),
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            data,
        )

    def _draw_fade_overlay(self) -> None:
        fade = self._fade_factor()
        if fade >= 1.0:
            return
        width, height = self._viewport_size
        gl.glColor4f(0.0, 0.0, 0.0, 1.0 - fade)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

    # ------------------------------------------------------------------
    # Timing helpers
    def _fade_factor(self) -> float:
        return min(1.0, self._elapsed / self.FADE_IN_DURATION)

    def _pan_progress(self) -> float:
        pan_start = self.FADE_IN_DURATION + self.EARTH_HOLD_DURATION
        if self._elapsed <= pan_start:
            return 0.0
        progress = (self._elapsed - pan_start) / self.PAN_DURATION
        return max(0.0, min(1.0, progress))

    def _mars_visibility(self, pan_progress: float) -> float:
        if pan_progress <= 0.0:
            return 0.0
        appear_threshold = self.MARS_REVEAL_DELAY / self.PAN_DURATION
        if pan_progress <= appear_threshold:
            return 0.0
        normalized = (pan_progress - appear_threshold) / (
            max(0.001, 1.0 - appear_threshold)
        )
        return max(0.0, min(1.0, normalized))

    # ------------------------------------------------------------------
    # Utility helpers
    def _generate_starfield(self, count: int) -> List[Star]:
        rng = random.Random(4150)
        stars: List[Star] = []
        for _ in range(count):
            position = (rng.random(), rng.random())
            base = rng.uniform(0.2, 0.95)
            speed = rng.uniform(0.6, 2.8)
            phase = rng.uniform(0.0, math.tau)
            stars.append(Star(position, base, speed, phase))
        return stars

    @staticmethod
    def _dot(a: Vec2, b: Vec2) -> float:
        return a[0] * b[0] + a[1] * b[1]

    @staticmethod
    def _normalized(vec: Vec2) -> Vec2:
        length = math.hypot(vec[0], vec[1])
        if length <= 0.0:
            return (0.0, 0.0)
        return (vec[0] / length, vec[1] / length)


Cutscene = CampaignOpeningCutscene
"""Alias used by external callers when referencing the default cutscene."""
