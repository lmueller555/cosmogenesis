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

    EARTH_CONTINENT_BLOBS = (
        # (angle in radians, lat center, angular width, strength)
        (math.radians(-15.0), 0.35, 0.9, 0.95),  # North America analogue
        (math.radians(70.0), 0.15, 0.7, 0.8),  # Europe / Africa analogue
        (math.radians(170.0), -0.1, 0.8, 0.9),  # Asia
        (math.radians(-120.0), -0.35, 0.65, 0.85),  # South America
        (math.radians(120.0), -0.6, 0.55, 0.65),  # Australia like
    )

    MARS_ALBEDO_FEATURES = (
        (math.radians(-35.0), 0.15, 0.9, 0.7),
        (math.radians(65.0), -0.1, 0.7, 0.6),
        (math.radians(150.0), -0.35, 1.0, 0.8),
    )

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
            land_mask = self._earth_continent_mask(angle, normal[1])
            ocean_color = (0.045, 0.14, 0.33)
            land_color = (0.14, 0.46, 0.22)
            tundra_color = (0.65, 0.75, 0.5)
            polar_mix = max(0.0, 1.0 - abs(normal[1]) * 4.5)
            base_r = self._lerp(ocean_color[0], land_color[0], land_mask)
            base_g = self._lerp(ocean_color[1], land_color[1], land_mask)
            base_b = self._lerp(ocean_color[2], land_color[2], land_mask)
            base_r = self._lerp(base_r, tundra_color[0], polar_mix)
            base_g = self._lerp(base_g, tundra_color[1], polar_mix)
            base_b = self._lerp(base_b, tundra_color[2], polar_mix)

            cloud_cover = self._earth_cloud_cover(angle, normal[1])
            r = base_r + cloud_cover * 0.45
            g = base_g + cloud_cover * 0.45
            b = base_b + cloud_cover * 0.47
            brightness = 0.35 + 0.65 * shade
            gl.glColor4f(r * brightness, g * brightness, b * brightness, 1.0)
            gl.glVertex2f(
                center[0] + normal[0] * radius,
                center[1] + normal[1] * radius * 0.98,
            )
        gl.glEnd()

        # Cloud wisps as a translucent overlay
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(1.0, 1.0, 1.0, 0.0)
        gl.glVertex2f(*center)
        for index in range(segments + 1):
            angle = (index / segments) * math.tau
            normal = (math.cos(angle), math.sin(angle))
            cover = self._earth_cloud_cover(angle * 1.07 + 0.4, normal[1] * 0.9)
            cover *= 0.22 + 0.12 * math.sin(self._elapsed * 0.4 + angle * 2.0)
            gl.glColor4f(1.0, 1.0, 1.0, cover)
            gl.glVertex2f(
                center[0] + normal[0] * radius * 1.005,
                center[1] + normal[1] * radius * 0.99,
            )
        gl.glEnd()

        # Atmospheric glow with thickness
        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        for index in range(segments + 1):
            angle = (index / segments) * math.tau
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            outer = 1.06
            inner = 1.02
            falloff = 0.2 + 0.15 * (1.0 - abs(sin_a))
            gl.glColor4f(0.35, 0.65, 1.0, 0.02)
            gl.glVertex2f(center[0] + cos_a * radius * inner, center[1] + sin_a * radius * inner)
            gl.glColor4f(0.35, 0.75, 1.0, falloff)
            gl.glVertex2f(center[0] + cos_a * radius * outer, center[1] + sin_a * radius * outer)
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
            terrain = self._mars_albedo(angle, normal[1])
            polar_cap = max(0.0, 1.0 - abs(normal[1]) * 5.5)
            dust_storm = 0.15 + 0.15 * math.sin(angle * 7.0 + self._elapsed * 0.7)
            r = terrain[0] + polar_cap * 0.35 + dust_storm * 0.4
            g = terrain[1] + polar_cap * 0.25 + dust_storm * 0.25
            b = terrain[2] + polar_cap * 0.2 + dust_storm * 0.2
            canyon = 0.4 + 0.6 * math.sin(angle * 3.2 - 0.3)
            canyon *= max(0.0, 1.0 - abs(normal[1] + 0.15) * 6.0)
            r -= canyon * 0.1
            g -= canyon * 0.05
            brightness = 0.25 + 0.75 * shade
            gl.glColor4f(r * brightness, g * brightness, b * brightness, visibility)
            gl.glVertex2f(
                center[0] + normal[0] * radius,
                center[1] + normal[1] * radius * 0.96,
            )
        gl.glEnd()

        # Thin Martian atmosphere
        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        for index in range(segments + 1):
            angle = (index / segments) * math.tau
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            glow = 0.12 + 0.08 * (1.0 - abs(sin_a))
            gl.glColor4f(0.95, 0.55, 0.25, 0.0)
            gl.glVertex2f(
                center[0] + cos_a * radius * 1.01,
                center[1] + sin_a * radius * 1.0,
            )
            gl.glColor4f(1.0, 0.7, 0.35, glow * visibility)
            gl.glVertex2f(
                center[0] + cos_a * radius * 1.08,
                center[1] + sin_a * radius * 1.05,
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

    # ------------------------------------------------------------------
    # Planet surface helpers
    def _earth_continent_mask(self, angle: float, lat: float) -> float:
        mask = 0.0
        for center_angle, center_lat, angular_width, strength in self.EARTH_CONTINENT_BLOBS:
            ang_dist = self._wrapped_angle_distance(angle, center_angle)
            lat_dist = abs(lat - center_lat)
            ang_falloff = max(0.0, 1.0 - (ang_dist / angular_width) ** 2)
            lat_falloff = max(0.0, 1.0 - (lat_dist / 0.55) ** 2)
            mask += ang_falloff * lat_falloff * strength
        return max(0.0, min(1.0, mask))

    def _earth_cloud_cover(self, angle: float, lat: float) -> float:
        equatorial_band = math.exp(-abs(lat) * 3.5)
        rotating_pattern = 0.5 + 0.5 * math.sin(angle * 3.8 + self._elapsed * 0.65 + lat * 6.0)
        turbulence = 0.5 + 0.5 * math.sin(angle * 6.2 - self._elapsed * 0.5)
        cover = equatorial_band * rotating_pattern * 0.6 + turbulence * 0.25
        return max(0.0, min(1.0, cover))

    def _mars_albedo(self, angle: float, lat: float) -> Tuple[float, float, float]:
        base = (0.55, 0.28, 0.15)
        basalt = (0.35, 0.18, 0.13)
        highlights = (0.78, 0.45, 0.22)
        region_mix = 0.0
        for center_angle, center_lat, angular_width, strength in self.MARS_ALBEDO_FEATURES:
            ang_dist = self._wrapped_angle_distance(angle, center_angle)
            lat_dist = abs(lat - center_lat)
            ang_falloff = max(0.0, 1.0 - (ang_dist / angular_width) ** 2)
            lat_falloff = max(0.0, 1.0 - (lat_dist / 0.75) ** 2)
            region_mix += ang_falloff * lat_falloff * strength
        region_mix = max(0.0, min(1.0, region_mix))
        mix_color = (
            self._lerp(base[0], basalt[0], region_mix),
            self._lerp(base[1], basalt[1], region_mix * 0.7),
            self._lerp(base[2], basalt[2], region_mix * 0.5),
        )
        highlight_factor = 0.4 + 0.6 * math.sin(angle * 2.0 + lat * 4.0)
        mix_color = (
            self._lerp(mix_color[0], highlights[0], highlight_factor * 0.15),
            self._lerp(mix_color[1], highlights[1], highlight_factor * 0.15),
            self._lerp(mix_color[2], highlights[2], highlight_factor * 0.15),
        )
        return mix_color

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * max(0.0, min(1.0, t))

    @staticmethod
    def _wrapped_angle_distance(angle: float, reference: float) -> float:
        distance = (angle - reference + math.pi) % math.tau - math.pi
        return abs(distance)


Cutscene = CampaignOpeningCutscene
"""Alias used by external callers when referencing the default cutscene."""
