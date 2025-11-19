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

    SCENE_LABEL = "campaign_opening"

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

    # ------------------------------------------------------------------
    # Earth rendering (lat/long strips, sharper features)
    def _draw_earth(self, center: Vec2, radius: float) -> None:
        """
        Draw Earth as a latitude/longitude grid so continents and oceans
        appear as actual shapes, with sharper surface detail.
        """
        # Higher tessellation for crisper features
        lat_segments = 72
        lon_segments = 144

        # 3D light direction for nicer shading
        light_dir = self._normalized3((-0.4, -0.2, 0.4))

        # Palette with stronger contrast
        deep_ocean = (0.02, 0.05, 0.18)
        shallow_ocean = (0.05, 0.18, 0.33)
        lowland = (0.09, 0.42, 0.18)
        highland = (0.32, 0.35, 0.20)
        mountain = (0.70, 0.70, 0.72)
        ice_color = (0.96, 0.98, 1.0)

        for lat_i in range(lat_segments):
            lat0 = -0.5 * math.pi + (lat_i / lat_segments) * math.pi
            lat1 = -0.5 * math.pi + ((lat_i + 1) / lat_segments) * math.pi

            gl.glBegin(gl.GL_TRIANGLE_STRIP)
            for lon_i in range(lon_segments + 1):
                lon = (lon_i / lon_segments) * math.tau

                for lat_angle in (lat0, lat1):
                    sin_lat = math.sin(lat_angle)
                    cos_lat = math.cos(lat_angle)
                    cos_lon = math.cos(lon)
                    sin_lon = math.sin(lon)

                    # 3D normal on sphere
                    nx = cos_lat * cos_lon
                    ny = sin_lat
                    nz = cos_lat * sin_lon
                    normal3 = (nx, ny, nz)

                    # 2D projection (slight vertical squish)
                    vx = center[0] + nx * radius
                    vy = center[1] + ny * radius * 0.98

                    # Parameters for surface functions
                    angle = lon
                    lat = sin_lat
                    abs_lat = abs(lat)

                    # Lighting
                    shade = max(0.0, self._dot3(normal3, light_dir))

                    # Base continent "height"
                    height_raw = self._earth_continent_mask(angle, lat)
                    # Sharpen land/ocean separation and add subtle edge noise
                    # so coastlines are more defined.
                    height = height_raw
                    height = (height - 0.15) / 0.85  # push small values towards ocean
                    height = max(0.0, min(1.0, height))
                    # Edge noise – small, so we don't flicker
                    edge_noise = 0.05 * math.sin(angle * 8.3 + lat * 17.1)
                    height = max(0.0, min(1.0, height + edge_noise))

                    # Classify terrain bands more aggressively for crisp biomes
                    if height < 0.08:
                        # deep ocean
                        base_r, base_g, base_b = deep_ocean
                    elif height < 0.25:
                        # shallow ocean / coastal shelf
                        t = (height - 0.08) / (0.25 - 0.08)
                        base_r = self._lerp(deep_ocean[0], shallow_ocean[0], t)
                        base_g = self._lerp(deep_ocean[1], shallow_ocean[1], t)
                        base_b = self._lerp(deep_ocean[2], shallow_ocean[2], t)
                    elif height < 0.45:
                        # lush lowlands
                        t = (height - 0.25) / (0.45 - 0.25)
                        base_r = self._lerp(shallow_ocean[0], lowland[0], t)
                        base_g = self._lerp(shallow_ocean[1], lowland[1], t)
                        base_b = self._lerp(shallow_ocean[2], lowland[2], t)
                    elif height < 0.7:
                        # highlands
                        t = (height - 0.45) / (0.7 - 0.45)
                        base_r = self._lerp(lowland[0], highland[0], t)
                        base_g = self._lerp(lowland[1], highland[1], t)
                        base_b = self._lerp(lowland[2], highland[2], t)
                    else:
                        # mountains
                        t = min(1.0, (height - 0.7) / 0.3)
                        base_r = self._lerp(highland[0], mountain[0], t)
                        base_g = self._lerp(highland[1], mountain[1], t)
                        base_b = self._lerp(highland[2], mountain[2], t)

                    # A bit of drier tint near equator on land only
                    if height >= 0.25:
                        dryness = max(0.0, 1.0 - abs_lat * 3.0)
                        desert_tint = (0.60, 0.50, 0.30)
                        desert_strength = 0.35 * dryness * (height - 0.25)
                        base_r = self._lerp(base_r, desert_tint[0], desert_strength)
                        base_g = self._lerp(base_g, desert_tint[1], desert_strength)
                        base_b = self._lerp(base_b, desert_tint[2], desert_strength)

                    # Polar ice caps – narrower and sharper
                    ice = self._smoothstep(0.78, 0.9, abs_lat)
                    base_r = self._lerp(base_r, ice_color[0], ice)
                    base_g = self._lerp(base_g, ice_color[1], ice)
                    base_b = self._lerp(base_b, ice_color[2], ice)

                    # Clouds – keep them, but less washing
                    cloud_cover = self._earth_cloud_cover(angle, lat)
                    if cloud_cover > 0.0:
                        cloud_intensity = cloud_cover * 0.55
                        base_r = self._lerp(base_r, 1.0, cloud_intensity * 0.5)
                        base_g = self._lerp(base_g, 1.0, cloud_intensity * 0.6)
                        base_b = self._lerp(base_b, 1.0, cloud_intensity * 0.7)

                    # Specular highlight on oceans – small, sharp glint
                    if height < 0.25:
                        spec = max(0.0, shade - 0.85) * 5.0
                        base_r += spec * 0.28
                        base_g += spec * 0.32
                        base_b += spec * 0.40

                    base_r = self._clamp01(base_r)
                    base_g = self._clamp01(base_g)
                    base_b = self._clamp01(base_b)

                    brightness = 0.32 + 0.68 * shade
                    r = base_r * brightness
                    g = base_g * brightness
                    b = base_b * brightness

                    gl.glColor4f(
                        self._clamp01(r),
                        self._clamp01(g),
                        self._clamp01(b),
                        1.0,
                    )
                    gl.glVertex2f(vx, vy)
            gl.glEnd()

        # Cloud wisps overlay (kept subtle)
        ring_segments = 240
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(1.0, 1.0, 1.0, 0.0)
        gl.glVertex2f(*center)
        for index in range(ring_segments + 1):
            angle = (index / ring_segments) * math.tau
            normal = (math.cos(angle), math.sin(angle))
            cover = self._earth_cloud_cover(angle * 1.07 + 0.4, normal[1] * 0.9)
            cover *= 0.16 + 0.10 * math.sin(self._elapsed * 0.4 + angle * 2.0)
            gl.glColor4f(1.0, 1.0, 1.0, cover)
            gl.glVertex2f(
                center[0] + normal[0] * radius * 1.005,
                center[1] + normal[1] * radius * 0.99,
            )
        gl.glEnd()

        # Atmospheric glow
        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        for index in range(ring_segments + 1):
            angle = (index / ring_segments) * math.tau
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            outer = 1.06
            inner = 1.02
            falloff = 0.2 + 0.15 * (1.0 - abs(sin_a))
            gl.glColor4f(0.35, 0.65, 1.0, 0.02)
            gl.glVertex2f(
                center[0] + cos_a * radius * inner,
                center[1] + sin_a * radius * inner,
            )
            gl.glColor4f(0.35, 0.75, 1.0, falloff)
            gl.glVertex2f(
                center[0] + cos_a * radius * outer,
                center[1] + sin_a * radius * outer,
            )
        gl.glEnd()

    # ------------------------------------------------------------------
    # Mars rendering (lat/long strips, sharper features)
    def _draw_mars(self, center: Vec2, radius: float, visibility: float) -> None:
        lat_segments = 64
        lon_segments = 128

        light_dir = self._normalized3((-0.35, -0.05, 0.3))

        for lat_i in range(lat_segments):
            lat0 = -0.5 * math.pi + (lat_i / lat_segments) * math.pi
            lat1 = -0.5 * math.pi + ((lat_i + 1) / lat_segments) * math.pi

            gl.glBegin(gl.GL_TRIANGLE_STRIP)
            for lon_i in range(lon_segments + 1):
                lon = (lon_i / lon_segments) * math.tau

                for lat_angle in (lat0, lat1):
                    sin_lat = math.sin(lat_angle)
                    cos_lat = math.cos(lat_angle)
                    cos_lon = math.cos(lon)
                    sin_lon = math.sin(lon)

                    nx = cos_lat * cos_lon
                    ny = sin_lat
                    nz = cos_lat * sin_lon
                    normal3 = (nx, ny, nz)

                    vx = center[0] + nx * radius
                    vy = center[1] + ny * radius * 0.96

                    angle = lon
                    lat = sin_lat

                    shade = max(0.0, self._dot3(normal3, light_dir))
                    r, g, b = self._mars_albedo(angle, lat)

                    brightness = 0.26 + 0.74 * shade
                    r *= brightness
                    g *= brightness
                    b *= brightness

                    gl.glColor4f(
                        self._clamp01(r),
                        self._clamp01(g),
                        self._clamp01(b),
                        visibility,
                    )
                    gl.glVertex2f(vx, vy)
            gl.glEnd()

        # Thin Martian atmosphere
        ring_segments = 200
        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        for index in range(ring_segments + 1):
            angle = (index / ring_segments) * math.tau
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

    @staticmethod
    def _dot3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _normalized3(
        vec: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        length = math.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])
        if length <= 0.0:
            return (0.0, 0.0, 0.0)
        return (vec[0] / length, vec[1] / length, vec[2] / length)

    @staticmethod
    def _clamp01(value: float) -> float:
        if value <= 0.0:
            return 0.0
        if value >= 1.0:
            return 1.0
        return value

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        t = CampaignOpeningCutscene._clamp01(t)
        return a + (b - a) * t

    @staticmethod
    def _smoothstep(edge0: float, edge1: float, x: float) -> float:
        if edge0 == edge1:
            return 0.0
        t = (x - edge0) / (edge1 - edge0)
        t = CampaignOpeningCutscene._clamp01(t)
        return t * t * (3.0 - 2.0 * t)

    # ------------------------------------------------------------------
    # Planet surface helpers
    def _earth_continent_mask(self, angle: float, lat: float) -> float:
        """
        Large-scale "height" map for continents; still smooth, but we
        sharpen it when mapping to colors.
        """
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
        rotating_pattern = 0.5 + 0.5 * math.sin(
            angle * 3.8 + self._elapsed * 0.65 + lat * 6.0
        )
        turbulence = 0.5 + 0.5 * math.sin(angle * 6.2 - self._elapsed * 0.5)
        cover = equatorial_band * rotating_pattern * 0.6 + turbulence * 0.25
        return max(0.0, min(1.0, cover))

    def _mars_albedo(self, angle: float, lat: float) -> Tuple[float, float, float]:
        """
        Sharper albedo features for Mars: dark basins, bright highlands,
        canyon band, polar caps, and dust storms with more contrast.
        """
        # Base palettes
        dark_basin = (0.35, 0.17, 0.10)      # Mare-like basalt
        bright_highland = (0.80, 0.43, 0.24)  # Dusty highlands
        mid_tone = (0.55, 0.28, 0.15)

        # Large-scale basins
        basin_strength = 0.0
        for center_angle, center_lat, angular_width, strength in self.MARS_ALBEDO_FEATURES:
            ang_dist = self._wrapped_angle_distance(angle, center_angle)
            lat_dist = abs(lat - center_lat)
            ang_falloff = max(0.0, 1.0 - (ang_dist / angular_width) ** 2)
            lat_falloff = max(0.0, 1.0 - (lat_dist / 0.75) ** 2)
            basin_strength += ang_falloff * lat_falloff * strength
        basin_strength = max(0.0, min(1.0, basin_strength))

        # Local detail
        noise = math.sin(angle * 9.0 + lat * 15.0) * 0.25
        # Highland factor – sharpened vs basins
        highland_factor = self._clamp01((1.0 - basin_strength) * 1.2 + noise * 0.4)

        r = mid_tone[0]
        g = mid_tone[1]
        b = mid_tone[2]

        # Blend towards dark basins
        r = self._lerp(r, dark_basin[0], basin_strength * 0.9)
        g = self._lerp(g, dark_basin[1], basin_strength * 0.9)
        b = self._lerp(b, dark_basin[2], basin_strength * 0.9)

        # Blend towards bright dusty highlands
        r = self._lerp(r, bright_highland[0], highland_factor * 0.9)
        g = self._lerp(g, bright_highland[1], highland_factor * 0.9)
        b = self._lerp(b, bright_highland[2], highland_factor * 0.9)

        # Canyon band near equator
        canyon_lat_band = max(0.0, 1.0 - abs(lat + 0.05) * 7.0)
        canyon_long_wave = max(0.0, math.sin(angle * 3.1 - 0.4))
        canyon = canyon_lat_band * canyon_long_wave
        if canyon > 0.0:
            r -= canyon * 0.22
            g -= canyon * 0.14
            b -= canyon * 0.10

        # Time-varying dust storms (bright patches)
        dust = 0.5 + 0.5 * math.sin(angle * 4.5 + self._elapsed * 0.7 + lat * 3.7)
        dust *= 0.30
        r += dust * 0.16
        g += dust * 0.10
        b += dust * 0.06

        # Polar caps
        ice = self._smoothstep(0.8, 0.93, abs(lat))
        ice_color = (0.96, 0.97, 1.0)
        r = self._lerp(r, ice_color[0], ice)
        g = self._lerp(g, ice_color[1], ice)
        b = self._lerp(b, ice_color[2], ice)

        r = self._clamp01(r)
        g = self._clamp01(g)
        b = self._clamp01(b)
        return (r, g, b)

    @staticmethod
    def _wrapped_angle_distance(angle: float, reference: float) -> float:
        distance = (angle - reference + math.pi) % math.tau - math.pi
        return abs(distance)


# ---------------------------------------------------------------------------
# Additional fully 3D-rendered opening scene


@dataclass
class ForestTree:
    """Single conifer-like tree for the 3D rendered forest opening scene."""

    position: Vec2  # normalized (0-1) clearing coordinates
    height: float
    sway_speed: float
    sway_amplitude: float


class OpeningSceneCutscene:
    """Opening scene featuring two sequential vignettes."""

    SCENE_LABEL = "opening_scene"

    SCENE1_FADE_IN_DURATION = 2.5
    SCENE1_LINGER_DURATION = 4.0
    SCENE1_ZOOM_DURATION = 6.0
    SCENE1_OUTRO_DURATION = 2.0
    SCENE1_TOTAL_DURATION = (
        SCENE1_FADE_IN_DURATION
        + SCENE1_LINGER_DURATION
        + SCENE1_ZOOM_DURATION
        + SCENE1_OUTRO_DURATION
    )

    SCENE2_FADE_IN_DURATION = 1.0
    SCENE2_INTERVIEW_SWITCHES = 5
    SCENE2_SWITCH_INTERVAL = 1.5
    SCENE2_TV_FOCUS_DURATION = SCENE2_SWITCH_INTERVAL * (SCENE2_INTERVIEW_SWITCHES + 1) + 1.0
    SCENE2_PAN_DELAY = 0.6
    SCENE2_WINDOW_PAN_DURATION = 3.0
    SCENE2_FLASH_DURATION = 1.8
    SCENE2_OUTRO_DURATION = 1.4
    SCENE2_TOTAL_DURATION = (
        SCENE2_TV_FOCUS_DURATION
        + SCENE2_PAN_DELAY
        + SCENE2_WINDOW_PAN_DURATION
        + SCENE2_FLASH_DURATION
        + SCENE2_OUTRO_DURATION
    )

    TOTAL_DURATION = SCENE1_TOTAL_DURATION + SCENE2_TOTAL_DURATION

    def __init__(self, viewport_size: Tuple[int, int]) -> None:
        pygame.font.init()
        self._viewport_size = viewport_size
        self._elapsed = 0.0
        self._stars: List[Star] = self._generate_starfield(250)
        self._trees: List[ForestTree] = self._generate_trees(45)
        self._camera_jitter_phase = random.random() * math.tau
        self._flicker_offsets = (
            random.random() * math.tau,
            random.random() * math.tau,
        )
        self._scene2_tv_scan_phase = random.random() * math.tau
        self._scene2_lamp_phase = random.random() * math.tau

    # ------------------------------------------------------------------
    # Lifecycle
    def reset(self) -> None:
        self._elapsed = 0.0

    def update(self, dt: float) -> None:
        self._elapsed = min(self._elapsed + dt, self.TOTAL_DURATION)

    def draw(self) -> None:
        width, height = self._viewport_size
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        if self._elapsed < self.SCENE1_TOTAL_DURATION:
            self._draw_scene1()
            self._draw_scene1_fade_overlay()
        else:
            scene2_time = min(
                self._elapsed - self.SCENE1_TOTAL_DURATION, self.SCENE2_TOTAL_DURATION
            )
            self._draw_scene2(scene2_time)
            self._draw_scene2_fade_overlay(scene2_time)

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

    def _draw_scene1(self) -> None:
        width, height = self._viewport_size
        camera_scale = 1.0 + 0.35 * self._scene1_zoom_progress()
        camera_offset = math.sin(self._elapsed * 0.4 + self._camera_jitter_phase) * 3.0

        gl.glPushMatrix()
        gl.glTranslatef(width / 2 + camera_offset, height / 2, 0.0)
        gl.glScalef(camera_scale, camera_scale, 1.0)
        gl.glTranslatef(-width / 2, -height / 2, 0.0)

        self._draw_scene1_background()
        self._draw_scene1_forest_floor()
        self._draw_scene1_trees()
        self._draw_scene1_house()

        gl.glPopMatrix()

    def _draw_scene2(self, scene_time: float) -> None:
        width, height = self._viewport_size
        zoom = 1.0 + 0.18 * self._scene2_zoom_progress(scene_time)
        pan_amount = self._scene2_pan_progress(scene_time) * width * 0.28

        gl.glPushMatrix()
        gl.glTranslatef(width / 2 + pan_amount, height / 2, 0.0)
        gl.glScalef(zoom, zoom, 1.0)
        gl.glTranslatef(-width / 2, -height / 2, 0.0)

        self._draw_scene2_room_base(scene_time)
        self._draw_scene2_furniture(scene_time)
        self._draw_scene2_tv(scene_time)
        self._draw_scene2_window(scene_time)

        gl.glPopMatrix()

    def update_viewport(self, viewport_size: Tuple[int, int]) -> None:
        self._viewport_size = viewport_size

    def is_finished(self) -> bool:
        return self._elapsed >= self.TOTAL_DURATION

    # ------------------------------------------------------------------
    # Scene 1 helpers
    def _draw_scene1_background(self) -> None:
        width, height = self._viewport_size
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.01, 0.01, 0.08, 1.0)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glColor4f(0.0, 0.0, 0.02, 1.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

        gl.glPointSize(2.0)
        gl.glBegin(gl.GL_POINTS)
        for star in self._stars:
            twinkle = math.sin(self._elapsed * star.twinkle_speed + star.phase)
            brightness = max(0.0, min(1.0, star.base_brightness + twinkle * 0.35))
            gl.glColor4f(brightness, brightness, brightness * 1.2, 1.0)
            gl.glVertex2f(star.position[0] * width, star.position[1] * height * 0.55)
        gl.glEnd()

    def _draw_scene1_forest_floor(self) -> None:
        width, height = self._viewport_size
        horizon = height * 0.55
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.02, 0.08, 0.03, 1.0)
        gl.glVertex2f(0.0, horizon)
        gl.glVertex2f(width, horizon)
        gl.glColor4f(0.03, 0.16, 0.05, 1.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.2, 0.3, 0.25, 0.3)
        gl.glVertex2f(0.0, horizon - 20)
        gl.glVertex2f(width, horizon - 20)
        gl.glColor4f(0.02, 0.05, 0.04, 0.0)
        gl.glVertex2f(width, horizon + 80)
        gl.glVertex2f(0.0, horizon + 80)
        gl.glEnd()

    def _draw_scene1_trees(self) -> None:
        width, height = self._viewport_size
        horizon = height * 0.55
        for tree in sorted(self._trees, key=lambda t: t.position[1]):
            depth = tree.position[1]
            sway = math.sin(self._elapsed * tree.sway_speed + tree.height) * tree.sway_amplitude
            scale = 0.6 + depth * 0.4
            tree_height = height * 0.85 * tree.height * scale
            base_x = (tree.position[0] - 0.5) * width * 0.9 + width / 2 + sway * 8.0 * (1.0 - depth)
            base_y = horizon + depth * (height - horizon) * 0.35
            crown_width = tree_height * 0.38

            gl.glBegin(gl.GL_QUADS)
            trunk_color = 0.08 + 0.25 * depth
            gl.glColor4f(trunk_color * 0.6, trunk_color * 0.4, trunk_color * 0.3, 1.0)
            gl.glVertex2f(base_x - crown_width * 0.08, base_y)
            gl.glVertex2f(base_x + crown_width * 0.08, base_y)
            gl.glVertex2f(base_x + crown_width * 0.05, base_y - tree_height * 0.45)
            gl.glVertex2f(base_x - crown_width * 0.05, base_y - tree_height * 0.45)
            gl.glEnd()

            layers = 4
            for i in range(layers):
                layer_ratio = i / layers
                width_factor = 1.0 - layer_ratio * 0.65
                layer_height = base_y - tree_height * (0.15 + layer_ratio * 0.8)
                brightness = 0.08 + 0.4 * depth + layer_ratio * 0.1
                gl.glBegin(gl.GL_TRIANGLES)
                gl.glColor4f(0.02 + brightness, 0.08 + brightness, 0.04 + brightness * 0.5, 1.0)
                gl.glVertex2f(base_x, layer_height - tree_height * 0.18)
                gl.glVertex2f(base_x - crown_width * width_factor, layer_height + tree_height * 0.1)
                gl.glVertex2f(base_x + crown_width * width_factor, layer_height + tree_height * 0.1)
                gl.glEnd()

    def _draw_scene1_house(self) -> None:
        width, height = self._viewport_size
        horizon = height * 0.55
        base_x = width / 2
        base_y = horizon + height * 0.12
        house_width = width * 0.2
        house_height = height * 0.18
        roof_height = house_height * 0.5

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.12, 0.11, 0.13, 1.0)
        gl.glVertex2f(base_x - house_width / 2, base_y)
        gl.glVertex2f(base_x + house_width / 2, base_y)
        gl.glVertex2f(base_x + house_width / 2, base_y - house_height)
        gl.glVertex2f(base_x - house_width / 2, base_y - house_height)
        gl.glEnd()

        gl.glBegin(gl.GL_TRIANGLES)
        gl.glColor4f(0.08, 0.08, 0.09, 1.0)
        gl.glVertex2f(base_x, base_y - house_height - roof_height)
        gl.glVertex2f(base_x - house_width / 2 - 20.0, base_y - house_height)
        gl.glVertex2f(base_x + house_width / 2 + 20.0, base_y - house_height)
        gl.glEnd()

        flicker = 0.65
        flicker += 0.25 * math.sin(self._elapsed * 8.7 + self._flicker_offsets[0])
        flicker += 0.15 * math.sin(self._elapsed * 15.3 + self._flicker_offsets[1])
        flicker += 0.1 * math.sin(self._elapsed * 24.1 + self._camera_jitter_phase * 0.5)
        flicker = self._clamp01(flicker)
        window_color = (0.1 * flicker, 0.3 * flicker, 0.9 * flicker, 0.9)
        window_width = house_width * 0.18
        window_height = house_height * 0.3
        spacing = house_width * 0.25
        for offset in (-spacing, spacing):
            gl.glBegin(gl.GL_QUADS)
            gl.glColor4f(*window_color)
            gl.glVertex2f(base_x + offset - window_width / 2, base_y - house_height * 0.35)
            gl.glVertex2f(base_x + offset + window_width / 2, base_y - house_height * 0.35)
            gl.glVertex2f(
                base_x + offset + window_width / 2,
                base_y - house_height * 0.35 - window_height,
            )
            gl.glVertex2f(
                base_x + offset - window_width / 2,
                base_y - house_height * 0.35 - window_height,
            )
            gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.05, 0.04, 0.04, 1.0)
        gl.glVertex2f(base_x - window_width * 0.75, base_y)
        gl.glVertex2f(base_x + window_width * 0.75, base_y)
        gl.glVertex2f(base_x + window_width * 0.75, base_y - house_height * 0.55)
        gl.glVertex2f(base_x - window_width * 0.75, base_y - house_height * 0.55)
        gl.glEnd()

    def _draw_scene1_fade_overlay(self) -> None:
        scene_time = min(self._elapsed, self.SCENE1_TOTAL_DURATION)
        fade_in = 1.0 - min(1.0, scene_time / self.SCENE1_FADE_IN_DURATION)
        outro_start = self.SCENE1_TOTAL_DURATION - self.SCENE1_OUTRO_DURATION
        fade_out = 0.0
        if scene_time > outro_start:
            fade_out = min(
                1.0,
                (scene_time - outro_start)
                / max(0.001, self.SCENE1_OUTRO_DURATION),
            )
        fade_amount = max(fade_in, fade_out)
        if fade_amount <= 0.0:
            return
        width, height = self._viewport_size
        gl.glColor4f(0.0, 0.0, 0.0, fade_amount)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

    # ------------------------------------------------------------------
    # Scene 2 helpers
    def _draw_scene2_room_base(self, scene_time: float) -> None:
        width, height = self._viewport_size
        floor_y = height * 0.66
        lamp_intensity = 0.35 + 0.25 * math.sin(scene_time * 2.0 + self._scene2_lamp_phase)
        lamp_intensity = self._clamp01(lamp_intensity)

        top_color = (
            0.07 + lamp_intensity * 0.15,
            0.08 + lamp_intensity * 0.12,
            0.15 + lamp_intensity * 0.2,
            1.0,
        )
        bottom_color = (
            0.02 + lamp_intensity * 0.08,
            0.02 + lamp_intensity * 0.06,
            0.05 + lamp_intensity * 0.12,
            1.0,
        )
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(*top_color)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glColor4f(*bottom_color)
        gl.glVertex2f(width, floor_y)
        gl.glVertex2f(0.0, floor_y)
        gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.12, 0.09, 0.07, 1.0)
        gl.glVertex2f(0.0, floor_y)
        gl.glVertex2f(width, floor_y)
        gl.glColor4f(0.06, 0.04, 0.03, 1.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.1, 0.08, 0.06, 1.0)
        gl.glVertex2f(0.0, floor_y - 6)
        gl.glVertex2f(width, floor_y - 6)
        gl.glVertex2f(width, floor_y)
        gl.glVertex2f(0.0, floor_y)
        gl.glEnd()

        plank_count = 18
        gl.glBegin(gl.GL_LINES)
        gl.glColor4f(0.08, 0.05, 0.03, 0.35)
        for index in range(plank_count + 1):
            x = width * (index / plank_count)
            gl.glVertex2f(x, floor_y)
            gl.glVertex2f(x, height)
        gl.glEnd()

        rug_radius_x = width * 0.22
        rug_radius_y = height * 0.08
        rug_center_x = width * 0.45
        rug_center_y = floor_y + height * 0.16
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.08, 0.05, 0.12, 0.8)
        gl.glVertex2f(rug_center_x, rug_center_y)
        for angle in range(0, 361, 10):
            rad = math.radians(angle)
            gl.glColor4f(0.14, 0.09, 0.24, 0.6)
            gl.glVertex2f(
                rug_center_x + math.cos(rad) * rug_radius_x,
                rug_center_y + math.sin(rad) * rug_radius_y,
            )
        gl.glEnd()

        frame_top = floor_y * 0.45
        frame_height = floor_y * 0.22
        for i in range(3):
            frame_width = width * 0.11
            gap = width * 0.02
            x = width * 0.08 + i * (frame_width + gap)
            gl.glBegin(gl.GL_QUADS)
            gl.glColor4f(0.25, 0.2, 0.15, 1.0)
            gl.glVertex2f(x, frame_top)
            gl.glVertex2f(x + frame_width, frame_top)
            gl.glVertex2f(x + frame_width, frame_top + frame_height)
            gl.glVertex2f(x, frame_top + frame_height)
            gl.glEnd()

            gl.glBegin(gl.GL_QUADS)
            gl.glColor4f(0.12 + 0.02 * i, 0.14, 0.18 + 0.02 * i, 0.6)
            gl.glVertex2f(x + 8, frame_top + 8)
            gl.glVertex2f(x + frame_width - 8, frame_top + 8)
            gl.glVertex2f(x + frame_width - 8, frame_top + frame_height - 8)
            gl.glVertex2f(x + 8, frame_top + frame_height - 8)
            gl.glEnd()

    def _draw_scene2_furniture(self, scene_time: float) -> None:
        width, height = self._viewport_size
        floor_y = height * 0.66

        sofa_width = width * 0.4
        sofa_height = height * 0.14
        sofa_x = width * 0.12
        sofa_y = floor_y - sofa_height * 0.4

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.18, 0.22, 0.32, 1.0)
        gl.glVertex2f(sofa_x, sofa_y)
        gl.glVertex2f(sofa_x + sofa_width, sofa_y)
        gl.glVertex2f(sofa_x + sofa_width, sofa_y + sofa_height)
        gl.glVertex2f(sofa_x, sofa_y + sofa_height)
        gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.14, 0.17, 0.25, 1.0)
        gl.glVertex2f(sofa_x, sofa_y - sofa_height * 0.4)
        gl.glVertex2f(sofa_x + sofa_width, sofa_y - sofa_height * 0.4)
        gl.glVertex2f(sofa_x + sofa_width, sofa_y)
        gl.glVertex2f(sofa_x, sofa_y)
        gl.glEnd()

        cushion_colors = (
            (0.95, 0.75, 0.35),
            (0.6, 0.75, 0.9),
        )
        for index, color in enumerate(cushion_colors):
            offset = sofa_width * 0.2 * index
            gl.glBegin(gl.GL_QUADS)
            gl.glColor4f(color[0], color[1], color[2], 1.0)
            gl.glVertex2f(sofa_x + sofa_width * 0.15 + offset, sofa_y - sofa_height * 0.25)
            gl.glVertex2f(
                sofa_x + sofa_width * 0.28 + offset,
                sofa_y - sofa_height * 0.25,
            )
            gl.glVertex2f(
                sofa_x + sofa_width * 0.28 + offset,
                sofa_y - sofa_height * 0.05,
            )
            gl.glVertex2f(sofa_x + sofa_width * 0.15 + offset, sofa_y - sofa_height * 0.05)
            gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.22, 0.15, 0.08, 1.0)
        table_width = width * 0.22
        table_height = height * 0.02
        table_x = width * 0.42
        table_y = floor_y + height * 0.08
        gl.glVertex2f(table_x, table_y)
        gl.glVertex2f(table_x + table_width, table_y)
        gl.glVertex2f(table_x + table_width, table_y + table_height)
        gl.glVertex2f(table_x, table_y + table_height)
        gl.glEnd()

        leg_width = table_width * 0.05
        gl.glBegin(gl.GL_QUADS)
        for offset in (0.08, 0.92):
            x = table_x + table_width * offset - leg_width / 2
            gl.glColor4f(0.12, 0.08, 0.05, 1.0)
            gl.glVertex2f(x, table_y + table_height)
            gl.glVertex2f(x + leg_width, table_y + table_height)
            gl.glVertex2f(x + leg_width, table_y + table_height + height * 0.08)
            gl.glVertex2f(x, table_y + table_height + height * 0.08)
        gl.glEnd()

        vase_center_x = table_x + table_width * 0.5
        vase_center_y = table_y - height * 0.01
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.74, 0.76, 0.9, 0.9)
        gl.glVertex2f(vase_center_x, vase_center_y)
        for angle in range(0, 361, 20):
            rad = math.radians(angle)
            gl.glVertex2f(
                vase_center_x + math.cos(rad) * width * 0.02,
                vase_center_y - height * 0.04 + math.sin(rad) * height * 0.02,
            )
        gl.glEnd()

        stem_top = vase_center_y - height * 0.12
        gl.glBegin(gl.GL_LINES)
        gl.glColor4f(0.3, 0.55, 0.3, 1.0)
        gl.glVertex2f(vase_center_x, vase_center_y - height * 0.02)
        gl.glVertex2f(vase_center_x - width * 0.01, stem_top)
        gl.glVertex2f(vase_center_x, vase_center_y - height * 0.02)
        gl.glVertex2f(vase_center_x + width * 0.008, stem_top * 0.99)
        gl.glEnd()

        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.95, 0.6, 0.2, 0.9)
        gl.glVertex2f(vase_center_x - width * 0.008, stem_top)
        for angle in range(0, 361, 30):
            rad = math.radians(angle)
            gl.glVertex2f(
                vase_center_x - width * 0.008 + math.cos(rad) * width * 0.02,
                stem_top + math.sin(rad) * width * 0.02,
            )
        gl.glEnd()

    def _draw_scene2_tv(self, scene_time: float) -> None:
        width, height = self._viewport_size
        tv_width = width * 0.34
        tv_height = height * 0.26
        tv_center_x = width * 0.42
        tv_x = tv_center_x - tv_width / 2
        tv_y = height * 0.2

        panel_padding = width * 0.015
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.05, 0.05, 0.07, 0.85)
        gl.glVertex2f(tv_x - panel_padding, tv_y - panel_padding)
        gl.glVertex2f(tv_x + tv_width + panel_padding, tv_y - panel_padding)
        gl.glVertex2f(tv_x + tv_width + panel_padding, tv_y + tv_height + panel_padding)
        gl.glVertex2f(tv_x - panel_padding, tv_y + tv_height + panel_padding)
        gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.08, 0.08, 0.1, 1.0)
        gl.glVertex2f(tv_x, tv_y)
        gl.glVertex2f(tv_x + tv_width, tv_y)
        gl.glVertex2f(tv_x + tv_width, tv_y + tv_height)
        gl.glVertex2f(tv_x, tv_y + tv_height)
        gl.glEnd()

        screen_margin = width * 0.01
        screen_rect = (
            tv_x + screen_margin,
            tv_y + screen_margin,
            tv_width - screen_margin * 2,
            tv_height - screen_margin * 2,
        )

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.02, 0.04, 0.09, 1.0)
        gl.glVertex2f(screen_rect[0], screen_rect[1])
        gl.glVertex2f(screen_rect[0] + screen_rect[2], screen_rect[1])
        gl.glColor4f(0.05, 0.08, 0.14, 1.0)
        gl.glVertex2f(screen_rect[0] + screen_rect[2], screen_rect[1] + screen_rect[3])
        gl.glVertex2f(screen_rect[0], screen_rect[1] + screen_rect[3])
        gl.glEnd()

        tv_time = min(scene_time, self.SCENE2_TV_FOCUS_DURATION)
        speaker_index, talk_phase = self._scene2_current_speaker(tv_time)
        chatter = math.sin(max(0.0, min(1.0, talk_phase)) * math.pi)
        chatter *= 0.7 + 0.3 * math.sin(self._elapsed * 8.0 + self._scene2_tv_scan_phase)
        chatter = self._clamp01(chatter)

        if speaker_index == 0:
            self._draw_scene2_portrait_reporter(screen_rect, chatter)
        else:
            self._draw_scene2_portrait_host(screen_rect, chatter)

        scanlines = 18
        gl.glBegin(gl.GL_LINES)
        for i in range(scanlines):
            y = screen_rect[1] + (i / scanlines) * screen_rect[3]
            alpha = 0.08 + 0.05 * math.sin(self._elapsed * 12.0 + i * 0.5)
            gl.glColor4f(0.9, 0.9, 1.0, alpha)
            gl.glVertex2f(screen_rect[0], y)
            gl.glVertex2f(screen_rect[0] + screen_rect[2], y)
        gl.glEnd()

        noise_alpha = 0.03 + 0.04 * math.sin(self._elapsed * 20.0)
        gl.glColor4f(1.0, 1.0, 1.0, noise_alpha)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(screen_rect[0], screen_rect[1])
        gl.glVertex2f(screen_rect[0] + screen_rect[2], screen_rect[1])
        gl.glVertex2f(screen_rect[0] + screen_rect[2], screen_rect[1] + screen_rect[3])
        gl.glVertex2f(screen_rect[0], screen_rect[1] + screen_rect[3])
        gl.glEnd()

    def _draw_scene2_window(self, scene_time: float) -> None:
        width, height = self._viewport_size
        window_width = width * 0.26
        window_height = height * 0.38
        window_x = width * 0.68
        window_y = height * 0.18

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.2, 0.16, 0.12, 1.0)
        gl.glVertex2f(window_x - 10, window_y - 10)
        gl.glVertex2f(window_x + window_width + 10, window_y - 10)
        gl.glVertex2f(window_x + window_width + 10, window_y + window_height + 10)
        gl.glVertex2f(window_x - 10, window_y + window_height + 10)
        gl.glEnd()

        inner_x = window_x
        inner_y = window_y
        inner_w = window_width
        inner_h = window_height

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.04, 0.07, 0.13, 1.0)
        gl.glVertex2f(inner_x, inner_y)
        gl.glVertex2f(inner_x + inner_w, inner_y)
        gl.glColor4f(0.01, 0.02, 0.05, 1.0)
        gl.glVertex2f(inner_x + inner_w, inner_y + inner_h)
        gl.glVertex2f(inner_x, inner_y + inner_h)
        gl.glEnd()

        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.0, 0.0, 0.0, 0.5)
        gl.glVertex2f(inner_x, inner_y + inner_h * 0.7)
        gl.glVertex2f(inner_x + inner_w, inner_y + inner_h * 0.7)
        gl.glVertex2f(inner_x + inner_w, inner_y + inner_h)
        gl.glVertex2f(inner_x, inner_y + inner_h)
        gl.glEnd()

        gl.glBegin(gl.GL_LINES)
        gl.glColor4f(0.28, 0.22, 0.18, 1.0)
        gl.glVertex2f(inner_x + inner_w / 2, inner_y)
        gl.glVertex2f(inner_x + inner_w / 2, inner_y + inner_h)
        gl.glVertex2f(inner_x, inner_y + inner_h / 2)
        gl.glVertex2f(inner_x + inner_w, inner_y + inner_h / 2)
        gl.glEnd()

        meteor_time = scene_time - (self.SCENE2_TV_FOCUS_DURATION + self.SCENE2_PAN_DELAY)
        if meteor_time > 0.0:
            flight_duration = self.SCENE2_WINDOW_PAN_DURATION * 0.85
            flight_progress = self._clamp01(
                meteor_time / max(0.001, flight_duration)
            )
            meteor_x = inner_x + inner_w * (0.95 - 0.8 * flight_progress)
            meteor_y = inner_y + inner_h * (0.05 + 0.85 * flight_progress)
            tail_dx = -inner_w * 0.15
            tail_dy = -inner_h * 0.08
            gl.glBegin(gl.GL_LINES)
            gl.glColor4f(1.0, 0.72, 0.25, 0.9)
            gl.glVertex2f(meteor_x, meteor_y)
            gl.glVertex2f(meteor_x - tail_dx, meteor_y - tail_dy)
            gl.glEnd()

            gl.glBegin(gl.GL_TRIANGLE_FAN)
            gl.glColor4f(1.0, 0.8, 0.3, 0.8)
            gl.glVertex2f(meteor_x, meteor_y)
            for angle in range(0, 361, 45):
                rad = math.radians(angle)
                gl.glVertex2f(
                    meteor_x + math.cos(rad) * width * 0.01,
                    meteor_y + math.sin(rad) * width * 0.01,
                )
            gl.glEnd()

        flash_intensity = self._scene2_flash_strength(scene_time)
        if flash_intensity > 0.0:
            gl.glBegin(gl.GL_QUADS)
            gl.glColor4f(1.0, 0.55, 0.12, 0.4 + 0.5 * flash_intensity)
            gl.glVertex2f(inner_x, inner_y)
            gl.glVertex2f(inner_x + inner_w, inner_y)
            gl.glColor4f(1.0, 0.65, 0.2, 0.6 * flash_intensity)
            gl.glVertex2f(inner_x + inner_w, inner_y + inner_h)
            gl.glVertex2f(inner_x, inner_y + inner_h)
            gl.glEnd()

    def _draw_scene2_portrait_reporter(self, rect: Tuple[float, float, float, float], chatter: float) -> None:
        x, y, w, h = rect
        face_center = (x + w * 0.58, y + h * 0.45)
        radius = w * 0.18

        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.72, 0.28, 0.42, 0.95)
        gl.glVertex2f(face_center[0], face_center[1])
        for angle in range(0, 361, 15):
            rad = math.radians(angle)
            offset = 1.0 + 0.2 * math.sin(angle * 2.0)
            gl.glVertex2f(
                face_center[0] - radius * 0.3 + math.cos(rad) * radius * 1.15,
                face_center[1] + math.sin(rad) * radius * 1.25 * offset,
            )
        gl.glEnd()

        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.98, 0.85, 0.78, 1.0)
        gl.glVertex2f(face_center[0], face_center[1])
        for angle in range(0, 361, 12):
            rad = math.radians(angle)
            gl.glVertex2f(
                face_center[0] + math.cos(rad) * radius,
                face_center[1] + math.sin(rad) * radius * 1.1,
            )
        gl.glEnd()

        shoulder_y = y + h * 0.75
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.55, 0.35, 0.6, 1.0)
        gl.glVertex2f(x + w * 0.25, shoulder_y)
        gl.glVertex2f(x + w * 0.9, shoulder_y)
        gl.glVertex2f(x + w * 0.9, shoulder_y + h * 0.2)
        gl.glVertex2f(x + w * 0.25, shoulder_y + h * 0.2)
        gl.glEnd()

        gl.glBegin(gl.GL_LINES)
        gl.glColor4f(0.2, 0.08, 0.06, 1.0)
        eye_y = face_center[1] - radius * 0.15
        eye_x = face_center[0] + radius * 0.2
        gl.glVertex2f(eye_x - radius * 0.1, eye_y)
        gl.glVertex2f(eye_x + radius * 0.05, eye_y - radius * 0.05)
        gl.glVertex2f(eye_x - radius * 0.35, eye_y + radius * 0.02)
        gl.glVertex2f(eye_x - radius * 0.18, eye_y - radius * 0.04)
        gl.glEnd()

        mouth_height = radius * 0.05 + chatter * radius * 0.08
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.8, 0.2, 0.3, 1.0)
        gl.glVertex2f(face_center[0] - radius * 0.1, face_center[1] + radius * 0.25)
        gl.glVertex2f(face_center[0] + radius * 0.15, face_center[1] + radius * 0.2)
        gl.glVertex2f(
            face_center[0] + radius * 0.15,
            face_center[1] + radius * 0.2 + mouth_height,
        )
        gl.glVertex2f(
            face_center[0] - radius * 0.1,
            face_center[1] + radius * 0.25 + mouth_height,
        )
        gl.glEnd()

    def _draw_scene2_portrait_host(self, rect: Tuple[float, float, float, float], chatter: float) -> None:
        x, y, w, h = rect
        face_center = (x + w * 0.42, y + h * 0.46)
        radius = w * 0.2

        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.82, 0.82, 0.88, 0.95)
        gl.glVertex2f(face_center[0], face_center[1] - radius * 0.1)
        for angle in range(0, 361, 15):
            rad = math.radians(angle)
            gl.glVertex2f(
                face_center[0] + math.cos(rad) * radius * 1.2,
                face_center[1] + math.sin(rad) * radius * 0.8,
            )
        gl.glEnd()

        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(0.9, 0.82, 0.74, 1.0)
        gl.glVertex2f(face_center[0], face_center[1])
        for angle in range(0, 361, 12):
            rad = math.radians(angle)
            gl.glVertex2f(
                face_center[0] + math.cos(rad) * radius * 0.95,
                face_center[1] + math.sin(rad) * radius * 1.05,
            )
        gl.glEnd()

        suit_y = y + h * 0.78
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.12, 0.16, 0.22, 1.0)
        gl.glVertex2f(x + w * 0.05, suit_y)
        gl.glVertex2f(x + w * 0.82, suit_y)
        gl.glVertex2f(x + w * 0.82, suit_y + h * 0.22)
        gl.glVertex2f(x + w * 0.05, suit_y + h * 0.22)
        gl.glEnd()

        gl.glBegin(gl.GL_TRIANGLES)
        gl.glColor4f(0.85, 0.85, 0.9, 1.0)
        gl.glVertex2f(x + w * 0.28, suit_y)
        gl.glVertex2f(x + w * 0.45, suit_y)
        gl.glVertex2f(x + w * 0.36, suit_y - h * 0.15)
        gl.glEnd()

        gl.glBegin(gl.GL_LINES)
        gl.glColor4f(0.18, 0.08, 0.05, 1.0)
        eye_y = face_center[1] - radius * 0.18
        gl.glVertex2f(face_center[0] - radius * 0.05, eye_y)
        gl.glVertex2f(face_center[0] + radius * 0.1, eye_y + radius * 0.02)
        gl.glVertex2f(face_center[0] - radius * 0.28, eye_y + radius * 0.04)
        gl.glVertex2f(face_center[0] - radius * 0.12, eye_y + radius * 0.02)
        gl.glEnd()

        moustache_height = h * 0.01 + chatter * h * 0.01
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.3, 0.2, 0.15, 1.0)
        gl.glVertex2f(face_center[0] - radius * 0.25, face_center[1] + radius * 0.15)
        gl.glVertex2f(face_center[0] - radius * 0.05, face_center[1] + radius * 0.1)
        gl.glVertex2f(
            face_center[0] - radius * 0.05,
            face_center[1] + radius * 0.1 + moustache_height,
        )
        gl.glVertex2f(
            face_center[0] - radius * 0.25,
            face_center[1] + radius * 0.15 + moustache_height,
        )
        gl.glEnd()

        mouth_width = radius * 0.2
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.7, 0.2, 0.25, 1.0)
        gl.glVertex2f(face_center[0] - mouth_width, face_center[1] + radius * 0.2)
        gl.glVertex2f(face_center[0] - mouth_width * 0.2, face_center[1] + radius * 0.18)
        gl.glVertex2f(
            face_center[0] - mouth_width * 0.2,
            face_center[1] + radius * 0.18 + chatter * radius * 0.1,
        )
        gl.glVertex2f(
            face_center[0] - mouth_width,
            face_center[1] + radius * 0.2 + chatter * radius * 0.1,
        )
        gl.glEnd()

    def _draw_scene2_fade_overlay(self, scene_time: float) -> None:
        fade_in = 1.0 - min(1.0, scene_time / self.SCENE2_FADE_IN_DURATION)
        outro_start = self.SCENE2_TOTAL_DURATION - self.SCENE2_OUTRO_DURATION
        fade_out = 0.0
        if scene_time > outro_start:
            fade_out = min(
                1.0,
                (scene_time - outro_start)
                / max(0.001, self.SCENE2_OUTRO_DURATION),
            )
        fade_amount = max(fade_in, fade_out)
        if fade_amount <= 0.0:
            return
        width, height = self._viewport_size
        gl.glColor4f(0.0, 0.0, 0.0, fade_amount)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(0.0, 0.0)
        gl.glVertex2f(width, 0.0)
        gl.glVertex2f(width, height)
        gl.glVertex2f(0.0, height)
        gl.glEnd()

    # ------------------------------------------------------------------
    # Utilities
    def _scene1_zoom_progress(self) -> float:
        t = self._elapsed - (
            self.SCENE1_FADE_IN_DURATION + self.SCENE1_LINGER_DURATION
        )
        if t <= 0.0:
            return 0.0
        return max(0.0, min(1.0, t / self.SCENE1_ZOOM_DURATION))

    def _scene2_zoom_progress(self, scene_time: float) -> float:
        if scene_time <= 0.0:
            return 0.0
        return max(0.0, min(1.0, scene_time / self.SCENE2_TV_FOCUS_DURATION))

    def _scene2_pan_progress(self, scene_time: float) -> float:
        pan_time = scene_time - (self.SCENE2_TV_FOCUS_DURATION + self.SCENE2_PAN_DELAY)
        if pan_time <= 0.0:
            return 0.0
        return max(0.0, min(1.0, pan_time / self.SCENE2_WINDOW_PAN_DURATION))

    def _scene2_flash_strength(self, scene_time: float) -> float:
        flash_start = (
            self.SCENE2_TV_FOCUS_DURATION
            + self.SCENE2_PAN_DELAY
            + self.SCENE2_WINDOW_PAN_DURATION * 0.85
        )
        if scene_time <= flash_start:
            return 0.0
        normalized = (scene_time - flash_start) / max(0.001, self.SCENE2_FLASH_DURATION)
        if normalized <= 0.0:
            return 0.0
        rise = min(1.0, normalized * 2.2)
        decay = max(0.0, 1.0 - max(0.0, normalized - 0.35))
        return self._clamp01(rise * decay)

    def _scene2_current_speaker(self, tv_time: float) -> Tuple[int, float]:
        interval = self.SCENE2_SWITCH_INTERVAL
        max_switch_time = self.SCENE2_INTERVIEW_SWITCHES * interval
        if tv_time >= max_switch_time:
            switch_index = self.SCENE2_INTERVIEW_SWITCHES
            time_in_segment = min(interval, tv_time - max_switch_time)
        else:
            switch_index = int(tv_time // interval)
            time_in_segment = tv_time - switch_index * interval
        switch_index = min(switch_index, self.SCENE2_INTERVIEW_SWITCHES)
        talk_phase = time_in_segment / max(0.001, interval)
        talk_phase = self._clamp01(talk_phase)
        speaker_index = switch_index % 2
        return speaker_index, talk_phase

    def _generate_starfield(self, count: int) -> List[Star]:
        stars: List[Star] = []
        for _ in range(count):
            stars.append(
                Star(
                    position=(random.random(), random.random()),
                    base_brightness=random.uniform(0.2, 0.8),
                    twinkle_speed=random.uniform(0.8, 1.5),
                    phase=random.uniform(0.0, math.tau),
                )
            )
        return stars

    def _generate_trees(self, count: int) -> List[ForestTree]:
        trees: List[ForestTree] = []
        while len(trees) < count:
            x = random.uniform(0.08, 0.92)
            if abs(x - 0.5) < 0.18:
                continue  # Leave a clearing around the house footprint.
            trees.append(
                ForestTree(
                    position=(x, random.random()),
                    height=random.uniform(0.85, 1.15),
                    sway_speed=random.uniform(0.3, 0.8),
                    sway_amplitude=random.uniform(0.01, 0.04),
                )
            )
        return trees


Cutscene = OpeningSceneCutscene
"""Alias used by external callers when referencing the default cutscene."""
