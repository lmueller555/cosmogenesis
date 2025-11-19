"""Story cutscene definitions for Cosmogenesis."""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import List, Optional, Sequence, Tuple

import pygame
from OpenGL import GL as gl

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]


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

    # Shared scene-two room dimensions so the couch, TV, and window align
    # precisely on their respective walls.
    SCENE2_ROOM_WIDTH = 11.0
    SCENE2_ROOM_DEPTH = 7.2
    SCENE2_ROOM_HEIGHT = 4.2

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


@dataclass
class SceneCamera:
    """Simple perspective camera used for the 3D vignette rendering."""

    position: Vec3
    target: Vec3
    fov: float


class OpeningSceneCutscene:
    """Opening scene featuring two sequential vignettes."""

    SCENE_LABEL = "opening_scene"

    # Scene two reuses the same living-room dimensions as the campaign
    # opening so all furniture placement math stays in sync.
    SCENE2_ROOM_WIDTH = 11.0
    SCENE2_ROOM_DEPTH = 7.2
    SCENE2_ROOM_HEIGHT = 4.2

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
        camera = self._scene1_camera()
        self._draw_scene1_background()
        self._draw_scene1_forest_floor(camera)
        self._draw_scene1_trees(camera)
        self._draw_scene1_house(camera)

    def _draw_scene2(self, scene_time: float) -> None:
        camera = self._scene2_camera(scene_time)
        self._draw_scene2_room_base(scene_time, camera)
        self._draw_scene2_furniture(scene_time, camera)
        self._draw_scene2_tv(scene_time, camera)
        self._draw_scene2_window(scene_time, camera)

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

    def _draw_scene1_forest_floor(self, camera: SceneCamera) -> None:
        light_dir = self._normalized3((-0.35, -0.8, -0.45))
        tile_count_x = 9
        tile_count_z = 10
        tile_size_x = 1.8
        tile_size_z = 1.6
        start_x = -tile_count_x * tile_size_x * 0.5
        start_z = -3.8
        faces = []
        for ix in range(tile_count_x):
            for iz in range(tile_count_z):
                x0 = start_x + ix * tile_size_x
                x1 = x0 + tile_size_x
                z0 = start_z + iz * tile_size_z
                z1 = z0 + tile_size_z
                undulation = math.sin(ix * 0.7 + iz * 0.9) * 0.1
                moss = math.sin(ix * 1.2 + self._elapsed * 0.4) * 0.04
                vertices = [
                    (x0, undulation * 0.5 + moss, z0),
                    (x1, undulation * 0.2 + moss * 0.5, z0),
                    (x1, undulation * 0.1 + moss * 0.2, z1),
                    (x0, undulation * 0.4 + moss * 0.9, z1),
                ]
                base_color = (
                    0.05 + ix * 0.005,
                    0.14 + iz * 0.008,
                    0.07 + undulation * 0.2,
                )
                wire_color = (0.28, 0.45, 0.3, 0.7)
                faces.append((vertices, base_color, 0.92, wire_color))
        self._render_face_batch(faces, camera, light_dir)

    def _draw_scene1_trees(self, camera: SceneCamera) -> None:
        light_dir = self._normalized3((-0.25, -0.75, -0.35))
        faces: List[Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]] = []
        for tree in self._trees:
            depth = tree.position[1]
            base_x = (tree.position[0] - 0.5) * 10.0
            base_z = -1.8 + depth * 7.5
            trunk_height = 2.4 * tree.height
            trunk_center = (base_x, trunk_height * 0.5, base_z)
            trunk_size = (0.35 * (0.8 + depth * 0.4), trunk_height, 0.35 * (0.8 + depth * 0.4))
            trunk_color = (0.1 + depth * 0.2, 0.06 + depth * 0.1, 0.04 + depth * 0.08)
            self._append_prism_faces(
                faces,
                trunk_center,
                trunk_size,
                trunk_color,
                (0.65, 0.5, 0.4, 0.9),
                0.95,
            )

            canopy_layers = 3
            canopy_base = trunk_height * 0.5
            for layer in range(canopy_layers):
                layer_height = trunk_height * (0.5 + layer * 0.35)
                radius = 1.2 - layer * 0.35
                color_scale = 0.35 + 0.2 * depth + layer * 0.05
                center = (base_x, canopy_base + layer_height, base_z)
                self._append_cone_faces(
                    faces,
                    center,
                    radius,
                    1.0,
                    6,
                    (0.05 + color_scale, 0.25 + color_scale * 0.5, 0.08 + color_scale * 0.3),
                    (0.4, 0.75, 0.4, 0.8),
                )
        self._render_face_batch(faces, camera, light_dir)

    def _draw_scene1_house(self, camera: SceneCamera) -> None:
        light_dir = self._normalized3((-0.35, -0.7, -0.4))
        body_center = (0.0, 1.4, 0.2)
        body_size = (4.8, 2.6, 3.4)
        faces: List[Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]] = []
        self._append_prism_faces(
            faces,
            body_center,
            body_size,
            (0.16, 0.12, 0.18),
            (0.9, 0.8, 0.95, 0.9),
            0.98,
        )

        half_w = body_size[0] / 2 + 0.1
        half_d = body_size[2] / 2 + 0.1
        top_y = body_center[1] + body_size[1] / 2
        ridge_y = top_y + 1.5
        ridge_front = (0.0, ridge_y, half_d)
        ridge_back = (0.0, ridge_y, -half_d)
        roof_vertices = [
            (-half_w, top_y, half_d),
            (half_w, top_y, half_d),
            (half_w, top_y, -half_d),
            (-half_w, top_y, -half_d),
        ]
        faces.append((
            [roof_vertices[0], roof_vertices[1], ridge_front],
            (0.11, 0.09, 0.12),
            0.97,
            (0.85, 0.7, 0.6, 0.9),
        ))
        faces.append((
            [roof_vertices[1], roof_vertices[2], ridge_back, ridge_front],
            (0.09, 0.07, 0.1),
            0.97,
            (0.85, 0.7, 0.6, 0.9),
        ))
        faces.append((
            [roof_vertices[2], roof_vertices[3], ridge_back],
            (0.11, 0.09, 0.12),
            0.97,
            (0.85, 0.7, 0.6, 0.9),
        ))
        faces.append((
            [roof_vertices[3], roof_vertices[0], ridge_front, ridge_back],
            (0.09, 0.07, 0.1),
            0.97,
            (0.85, 0.7, 0.6, 0.9),
        ))

        flicker = 0.65
        flicker += 0.25 * math.sin(self._elapsed * 8.7 + self._flicker_offsets[0])
        flicker += 0.15 * math.sin(self._elapsed * 15.3 + self._flicker_offsets[1])
        flicker += 0.1 * math.sin(self._elapsed * 24.1 + self._camera_jitter_phase * 0.5)
        flicker = self._clamp01(flicker)
        window_light = (0.1 * flicker, 0.35 * flicker, 0.9 * flicker)
        window_width = 0.7
        window_height = 0.9
        front_z = body_center[2] + body_size[2] / 2 + 0.01
        for offset in (-1.25, 1.25):
            frame = [
                (offset - window_width / 2, top_y - 0.6, front_z),
                (offset + window_width / 2, top_y - 0.6, front_z),
                (offset + window_width / 2, top_y - window_height - 0.6, front_z),
                (offset - window_width / 2, top_y - window_height - 0.6, front_z),
            ]
            faces.append((frame, window_light, 0.95, (0.4, 0.6, 0.95, 0.8)))

        door_width = 1.0
        door_height = 1.7
        door = [
            (-door_width / 2, body_center[1] - body_size[1] / 2 + door_height, front_z),
            (door_width / 2, body_center[1] - body_size[1] / 2 + door_height, front_z),
            (door_width / 2, body_center[1] - body_size[1] / 2, front_z),
            (-door_width / 2, body_center[1] - body_size[1] / 2, front_z),
        ]
        faces.append((door, (0.2, 0.12, 0.08), 0.98, (0.9, 0.7, 0.5, 0.9)))

        walkway = [
            (-1.2, 0.02, body_center[2] + body_size[2] / 2 + 0.6),
            (1.2, 0.02, body_center[2] + body_size[2] / 2 + 0.6),
            (1.6, 0.0, body_center[2] + body_size[2] / 2 + 2.4),
            (-1.6, 0.0, body_center[2] + body_size[2] / 2 + 2.4),
        ]
        faces.append((walkway, (0.25, 0.2, 0.15), 0.85, (0.6, 0.45, 0.3, 0.7)))

        self._render_face_batch(faces, camera, light_dir)

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
    def _draw_scene2_room_base(self, scene_time: float, camera: SceneCamera) -> None:
        lamp_intensity = 0.35 + 0.25 * math.sin(scene_time * 2.0 + self._scene2_lamp_phase)
        lamp_intensity = self._clamp01(lamp_intensity)
        room_width = self.SCENE2_ROOM_WIDTH
        room_depth = self.SCENE2_ROOM_DEPTH
        room_height = self.SCENE2_ROOM_HEIGHT
        front_z = 2.0
        back_z = -room_depth
        light_dir = self._normalized3((-0.2, -0.6, -0.8))
        faces: List[
            Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]
        ] = []

        floor = [
            (-room_width / 2, 0.0, front_z),
            (room_width / 2, 0.0, front_z),
            (room_width / 2, 0.0, back_z),
            (-room_width / 2, 0.0, back_z),
        ]
        floor_color = (0.16 + lamp_intensity * 0.1, 0.11 + lamp_intensity * 0.08, 0.08)
        faces.append((floor, floor_color, 0.95, (0.7, 0.5, 0.35, 0.8)))

        ceiling = [
            (-room_width / 2, room_height, front_z * 0.2),
            (room_width / 2, room_height, front_z * 0.2),
            (room_width / 2, room_height, back_z),
            (-room_width / 2, room_height, back_z),
        ]
        faces.append(
            (
                ceiling,
                (0.1 + lamp_intensity * 0.2, 0.12 + lamp_intensity * 0.18, 0.18 + lamp_intensity * 0.25),
                0.9,
                (0.4, 0.4, 0.5, 0.6),
            )
        )

        back_wall = [
            (-room_width / 2, room_height, back_z),
            (room_width / 2, room_height, back_z),
            (room_width / 2, 0.0, back_z),
            (-room_width / 2, 0.0, back_z),
        ]
        faces.append(
            (
                back_wall,
                (0.07 + lamp_intensity * 0.12, 0.08 + lamp_intensity * 0.12, 0.14 + lamp_intensity * 0.2),
                0.95,
                (0.45, 0.4, 0.35, 0.8),
            )
        )

        left_wall = [
            (-room_width / 2, room_height, front_z),
            (-room_width / 2, room_height, back_z),
            (-room_width / 2, 0.0, back_z),
            (-room_width / 2, 0.0, front_z),
        ]
        right_wall = [
            (room_width / 2, room_height, back_z),
            (room_width / 2, room_height, front_z),
            (room_width / 2, 0.0, front_z),
            (room_width / 2, 0.0, back_z),
        ]
        wall_color = (0.06 + lamp_intensity * 0.1, 0.05 + lamp_intensity * 0.08, 0.09 + lamp_intensity * 0.16)
        faces.append((left_wall, wall_color, 0.9, (0.4, 0.35, 0.3, 0.7)))
        faces.append((right_wall, wall_color, 0.9, (0.4, 0.35, 0.3, 0.7)))

        rug = [
            (-0.5, 0.01, -0.5),
            (3.2, 0.01, -0.3),
            (2.6, 0.01, -3.2),
            (-0.9, 0.01, -3.5),
        ]
        faces.append((rug, (0.12, 0.07, 0.18), 0.85, (0.7, 0.45, 0.9, 0.6)))

        # Baseboards along the walls reinforce depth cues for the living room.
        baseboard_height = 0.22
        baseboard_thickness = 0.08
        depth_span = front_z - back_z
        for x in (-room_width / 2 + baseboard_thickness / 2, room_width / 2 - baseboard_thickness / 2):
            center = (x, baseboard_height / 2, (front_z + back_z) / 2)
            self._append_prism_faces(
                faces,
                center,
                (baseboard_thickness, baseboard_height, depth_span),
                (0.22, 0.18, 0.14),
                (0.6, 0.5, 0.4, 0.85),
                0.9,
            )
        center = (0.0, baseboard_height / 2, back_z + baseboard_thickness / 2)
        self._append_prism_faces(
            faces,
            center,
            (room_width, baseboard_height, baseboard_thickness),
            (0.2, 0.16, 0.12),
            (0.55, 0.45, 0.35, 0.85),
            0.9,
        )

        # An accent panel behind the TV makes the centered screen feel anchored.
        panel = [
            (-1.8, room_height * 0.92, back_z + 0.01),
            (1.8, room_height * 0.92, back_z + 0.01),
            (1.8, 0.6, back_z + 0.01),
            (-1.8, 0.6, back_z + 0.01),
        ]
        faces.append((panel, (0.1, 0.12, 0.18), 0.8, (0.45, 0.5, 0.65, 0.55)))

        frame_height = 1.4
        frame_width = 0.9
        for index in range(3):
            frame_x = -room_width / 2 + 0.6
            offset_y = 1.2 + index * 0.6
            art = [
                (frame_x + 0.01, offset_y + frame_height, -room_depth + 0.02),
                (frame_x + frame_width, offset_y + frame_height, -room_depth + 0.02),
                (frame_x + frame_width, offset_y, -room_depth + 0.02),
                (frame_x + 0.01, offset_y, -room_depth + 0.02),
            ]
            faces.append((art, (0.15 + index * 0.05, 0.12, 0.18 + index * 0.03), 0.75, (0.6, 0.5, 0.4, 0.7)))

        self._render_face_batch(faces, camera, light_dir)

    def _draw_scene2_furniture(self, scene_time: float, camera: SceneCamera) -> None:
        light_dir = self._normalized3((-0.3, -0.7, -0.4))
        faces: List[
            Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]
        ] = []

        room_width = self.SCENE2_ROOM_WIDTH
        sofa_depth_offset = -0.6
        sofa_size = (4.2, 1.1, 1.6)
        sofa_center = (
            -room_width / 2 + sofa_size[0] / 2 + 0.15,
            0.9,
            sofa_depth_offset,
        )
        self._append_prism_faces(
            faces,
            sofa_center,
            sofa_size,
            (0.14, 0.19, 0.26),
            (0.5, 0.7, 0.85, 0.85),
            0.95,
        )
        back_center = (sofa_center[0], 1.65, sofa_depth_offset - sofa_size[2] / 2 + 0.15)
        back_size = (sofa_size[0], 1.15, 0.45)
        self._append_prism_faces(
            faces,
            back_center,
            back_size,
            (0.12, 0.16, 0.23),
            (0.4, 0.6, 0.8, 0.8),
            0.95,
        )

        cushion_colors = (
            (0.95, 0.75, 0.35),
            (0.6, 0.75, 0.9),
        )
        for index, color in enumerate(cushion_colors):
            center = (
                sofa_center[0] - sofa_size[0] / 2 + 1.2 + index * 1.4,
                1.4,
                sofa_depth_offset + 0.1,
            )
            size = (0.9, 0.5, 0.4)
            self._append_prism_faces(
                faces,
                center,
                size,
                color,
                (0.95, 0.95, 0.95, 0.8),
                0.9,
            )

        table_center = (1.4, 0.5, -0.3)
        table_size = (2.4, 0.4, 1.3)
        self._append_prism_faces(
            faces,
            table_center,
            table_size,
            (0.22, 0.15, 0.08),
            (0.8, 0.6, 0.4, 0.85),
            0.9,
        )
        for offset in (-0.85, 0.85):
            leg_center = (table_center[0] + offset, 0.2, table_center[2] + 0.45)
            self._append_prism_faces(
                faces,
                leg_center,
                (0.2, 0.4, 0.2),
                (0.16, 0.1, 0.06),
                (0.5, 0.35, 0.25, 0.8),
                0.9,
            )

        vase_center = (1.35, 1.0, -0.45)
        self._append_prism_faces(
            faces,
            vase_center,
            (0.3, 0.6, 0.3),
            (0.75, 0.8, 0.92),
            (0.8, 0.85, 0.95, 0.9),
            0.8,
        )
        self._append_cone_faces(
            faces,
            (vase_center[0], vase_center[1] + 0.4, vase_center[2]),
            0.25,
            0.5,
            6,
            (0.3, 0.55, 0.35),
            (0.4, 0.7, 0.45, 0.8),
        )

        self._render_face_batch(faces, camera, light_dir)

    def _draw_scene2_tv(self, scene_time: float, camera: SceneCamera) -> None:
        light_dir = self._normalized3((-0.15, -0.7, -0.3))
        room_depth = self.SCENE2_ROOM_DEPTH
        faces: List[
            Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]
        ] = []
        tv_center = (0.0, 1.45, -room_depth + 0.35)
        tv_size = (3.3, 1.85, 0.5)
        self._append_prism_faces(
            faces,
            tv_center,
            tv_size,
            (0.06, 0.06, 0.08),
            (0.6, 0.65, 0.75, 0.9),
            0.95,
        )

        stand_center = (0.0, 0.55, tv_center[2] - 0.05)
        self._append_prism_faces(
            faces,
            stand_center,
            (2.2, 0.35, 0.9),
            (0.04, 0.04, 0.05),
            (0.5, 0.5, 0.6, 0.8),
            0.9,
        )

        screen_width = 2.7
        screen_height = 1.35
        screen_z = tv_center[2] + tv_size[2] / 2 + 0.02
        screen_vertices = [
            (tv_center[0] - screen_width / 2, tv_center[1] + screen_height / 2, screen_z),
            (tv_center[0] + screen_width / 2, tv_center[1] + screen_height / 2, screen_z),
            (tv_center[0] + screen_width / 2, tv_center[1] - screen_height / 2, screen_z),
            (tv_center[0] - screen_width / 2, tv_center[1] - screen_height / 2, screen_z),
        ]
        faces.append((screen_vertices, (0.02, 0.04, 0.09), 1.0, (0.4, 0.55, 0.8, 0.95)))

        self._render_face_batch(faces, camera, light_dir)

        projected_screen = self._project_polygon(screen_vertices, camera)
        if not projected_screen:
            return
        screen_rect = self._polygon_bounding_rect(projected_screen)
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

    def _draw_scene2_window(self, scene_time: float, camera: SceneCamera) -> None:
        light_dir = self._normalized3((-0.1, -0.5, -0.9))
        room_depth = self.SCENE2_ROOM_DEPTH
        room_width = self.SCENE2_ROOM_WIDTH
        window_size = (2.8, 3.0)
        window_center = (
            room_width / 2 - window_size[0] / 2 - 0.35,
            2.0,
            -room_depth + 0.2,
        )
        frame_depth = 0.25
        faces: List[
            Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]
        ] = []

        vertical_centers = (
            window_center[0] - window_size[0] / 2 - 0.15,
            window_center[0] + window_size[0] / 2 + 0.15,
        )
        for x_center in vertical_centers:
            center = (x_center, window_center[1], window_center[2] - frame_depth / 2)
            self._append_prism_faces(
                faces,
                center,
                (0.3, window_size[1] + 0.4, frame_depth),
                (0.25, 0.18, 0.12),
                (0.8, 0.65, 0.5, 0.9),
                0.95,
            )
        horizontal_centers = (
            window_center[1] + window_size[1] / 2 + 0.15,
            window_center[1] - window_size[1] / 2 - 0.15,
        )
        for y_center in horizontal_centers:
            center = (window_center[0], y_center, window_center[2] - frame_depth / 2)
            self._append_prism_faces(
                faces,
                center,
                (window_size[0] + 0.6, 0.3, frame_depth),
                (0.24, 0.18, 0.14),
                (0.75, 0.6, 0.45, 0.9),
                0.95,
            )

        glass_vertices = [
            (
                window_center[0] - window_size[0] / 2,
                window_center[1] + window_size[1] / 2,
                window_center[2],
            ),
            (
                window_center[0] + window_size[0] / 2,
                window_center[1] + window_size[1] / 2,
                window_center[2],
            ),
            (
                window_center[0] + window_size[0] / 2,
                window_center[1] - window_size[1] / 2,
                window_center[2],
            ),
            (
                window_center[0] - window_size[0] / 2,
                window_center[1] - window_size[1] / 2,
                window_center[2],
            ),
        ]
        faces.append((glass_vertices, (0.05, 0.08, 0.12), 0.8, (0.4, 0.5, 0.7, 0.6)))

        self._render_face_batch(faces, camera, light_dir)

        mullion_top = (window_center[0], window_center[1] + window_size[1] / 2, window_center[2] + 0.01)
        mullion_bottom = (window_center[0], window_center[1] - window_size[1] / 2, window_center[2] + 0.01)
        mullion_left = (window_center[0] - window_size[0] / 2, window_center[1], window_center[2] + 0.01)
        mullion_right = (window_center[0] + window_size[0] / 2, window_center[1], window_center[2] + 0.01)
        mullion_color = (0.7, 0.6, 0.45, 0.9)
        self._draw_projected_line(mullion_top, mullion_bottom, camera, mullion_color)
        self._draw_projected_line(mullion_left, mullion_right, camera, mullion_color)

        glass_polygon = self._project_polygon(glass_vertices, camera)
        meteor_time = scene_time - (self.SCENE2_TV_FOCUS_DURATION + self.SCENE2_PAN_DELAY)
        if meteor_time > 0.0:
            flight_duration = self.SCENE2_WINDOW_PAN_DURATION * 0.85
            flight_progress = self._clamp01(meteor_time / max(0.001, flight_duration))
            meteor_pos = (
                window_center[0] + window_size[0] * (0.45 - 0.9 * flight_progress),
                window_center[1] + window_size[1] * (0.15 + 0.7 * flight_progress),
                window_center[2] - 0.02,
            )
            tail_pos = (
                meteor_pos[0] + window_size[0] * 0.2,
                meteor_pos[1] - window_size[1] * 0.18,
                meteor_pos[2] - 0.2,
            )
            self._draw_projected_line(tail_pos, meteor_pos, camera, (1.0, 0.72, 0.25, 0.9))
            meteor_projected = self._project_point(meteor_pos, camera)
            if meteor_projected is not None:
                glow_radius = self._viewport_size[0] * 0.012
                gl.glBegin(gl.GL_TRIANGLE_FAN)
                gl.glColor4f(1.0, 0.8, 0.3, 0.85)
                gl.glVertex2f(meteor_projected[0], meteor_projected[1])
                for angle in range(0, 361, 40):
                    rad = math.radians(angle)
                    gl.glVertex2f(
                        meteor_projected[0] + math.cos(rad) * glow_radius,
                        meteor_projected[1] + math.sin(rad) * glow_radius,
                    )
                gl.glEnd()

        flash_intensity = self._scene2_flash_strength(scene_time)
        if flash_intensity > 0.0 and glass_polygon:
            gl.glBegin(gl.GL_POLYGON)
            gl.glColor4f(1.0, 0.55, 0.12, 0.35 + 0.4 * flash_intensity)
            for x, y in glass_polygon:
                gl.glVertex2f(x, y)
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
    def _scene1_camera(self) -> SceneCamera:
        zoom = self._scene1_zoom_progress()
        distance = 9.2 - zoom * 3.2
        horizontal = math.sin(self._elapsed * 0.35 + self._camera_jitter_phase) * 0.4
        vertical = 2.4 - zoom * 0.4
        target = (0.0, 1.3, 0.0)
        return SceneCamera(position=(horizontal, vertical, distance), target=target, fov=math.radians(55.0))

    def _scene2_camera(self, scene_time: float) -> SceneCamera:
        zoom = self._scene2_zoom_progress(scene_time)
        pan = self._scene2_pan_progress(scene_time)
        base_pos = (-2.0, 2.1, 8.2)
        position = (
            base_pos[0] + pan * 2.0,
            base_pos[1] + math.sin(self._elapsed * 0.3) * 0.05,
            base_pos[2] - zoom * 2.0,
        )
        target = (0.0 + pan * 2.4, 1.3, -2.8)
        return SceneCamera(position=position, target=target, fov=math.radians(50.0))

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
                )
            )
        return trees

    @staticmethod
    def _clamp01(value: float) -> float:
        """Clamp a floating point value to the inclusive range [0, 1]."""

        if value <= 0.0:
            return 0.0
        if value >= 1.0:
            return 1.0
        return value

    # ------------------------------------------------------------------
    # 3D helpers
    def _project_point(self, point: Vec3, camera: SceneCamera) -> Optional[Tuple[float, float, float]]:
        width, height = self._viewport_size
        aspect = width / max(1.0, float(height))
        forward = self._normalized3(
            (
                camera.target[0] - camera.position[0],
                camera.target[1] - camera.position[1],
                camera.target[2] - camera.position[2],
            )
        )
        up_hint = (0.0, 1.0, 0.0)
        if abs(self._dot3(forward, up_hint)) > 0.96:
            up_hint = (0.0, 0.0, 1.0)
        right = self._normalized3(self._cross3(forward, up_hint))
        up = self._cross3(right, forward)
        relative = (
            point[0] - camera.position[0],
            point[1] - camera.position[1],
            point[2] - camera.position[2],
        )
        view_x = self._dot3(relative, right)
        view_y = self._dot3(relative, up)
        view_z = self._dot3(relative, forward)
        near = 0.1
        if view_z <= near:
            return None
        f = 1.0 / math.tan(max(0.1, camera.fov * 0.5))
        ndc_x = (view_x * f) / (view_z * aspect)
        ndc_y = (view_y * f) / view_z
        screen_x = width * (0.5 + ndc_x * 0.5)
        screen_y = height * (0.5 - ndc_y * 0.5)
        return screen_x, screen_y, view_z

    def _render_face_batch(
        self,
        faces: Sequence[Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]],
        camera: SceneCamera,
        light_dir: Vec3,
    ) -> None:
        queue: List[Tuple[float, List[Vec2], Vec3, Tuple[float, float, float], float, Tuple[float, float, float, float]]] = []
        for vertices, base_color, alpha, wire_color in faces:
            projected: List[Vec2] = []
            depths: List[float] = []
            skip = False
            for vertex in vertices:
                result = self._project_point(vertex, camera)
                if result is None:
                    skip = True
                    break
                projected.append((result[0], result[1]))
                depths.append(result[2])
            if skip:
                continue
            normal = self._face_normal(vertices)
            queue.append((sum(depths) / len(depths), projected, normal, base_color, alpha, wire_color))

        queue.sort(key=lambda entry: entry[0], reverse=True)
        for _, projected, normal, base_color, alpha, wire_color in queue:
            intensity = max(0.2, self._dot3(normal, light_dir) * 0.6 + 0.4)
            color = (
                self._clamp01(base_color[0] * intensity),
                self._clamp01(base_color[1] * intensity),
                self._clamp01(base_color[2] * intensity),
            )
            gl.glColor4f(color[0], color[1], color[2], alpha)
            gl.glBegin(gl.GL_TRIANGLE_FAN)
            for x, y in projected:
                gl.glVertex2f(x, y)
            gl.glEnd()

            gl.glColor4f(
                wire_color[0],
                wire_color[1],
                wire_color[2],
                wire_color[3] * alpha,
            )
            gl.glBegin(gl.GL_LINE_LOOP)
            for x, y in projected:
                gl.glVertex2f(x, y)
            gl.glEnd()

    def _append_prism_faces(
        self,
        face_store: List[Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]],
        center: Vec3,
        size: Vec3,
        base_color: Tuple[float, float, float],
        wire_color: Tuple[float, float, float, float],
        alpha: float,
    ) -> None:
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        vertices = [
            (center[0] - hx, center[1] - hy, center[2] - hz),
            (center[0] + hx, center[1] - hy, center[2] - hz),
            (center[0] + hx, center[1] + hy, center[2] - hz),
            (center[0] - hx, center[1] + hy, center[2] - hz),
            (center[0] - hx, center[1] - hy, center[2] + hz),
            (center[0] + hx, center[1] - hy, center[2] + hz),
            (center[0] + hx, center[1] + hy, center[2] + hz),
            (center[0] - hx, center[1] + hy, center[2] + hz),
        ]
        indices = (
            (7, 6, 5, 4),  # front
            (3, 2, 1, 0),  # back
            (3, 7, 4, 0),  # left
            (2, 6, 5, 1),  # right
            (3, 2, 6, 7),  # top
            (0, 1, 5, 4),  # bottom
        )
        for face_indices in indices:
            face_store.append(
                ([vertices[i] for i in face_indices], base_color, alpha, wire_color)
            )

    def _append_cone_faces(
        self,
        face_store: List[Tuple[Sequence[Vec3], Tuple[float, float, float], float, Tuple[float, float, float, float]]],
        center: Vec3,
        radius: float,
        height: float,
        segments: int,
        base_color: Tuple[float, float, float],
        wire_color: Tuple[float, float, float, float],
    ) -> None:
        base_y = center[1]
        apex = (center[0], center[1] + height, center[2])
        ring: List[Vec3] = []
        for index in range(segments):
            angle = (index / segments) * math.tau
            ring.append(
                (
                    center[0] + math.cos(angle) * radius,
                    base_y,
                    center[2] + math.sin(angle) * radius,
                )
            )
        for i in range(segments):
            v0 = ring[i]
            v1 = ring[(i + 1) % segments]
            face_store.append(([v0, v1, apex], base_color, 0.9, wire_color))
        face_store.append((ring, tuple(value * 0.85 for value in base_color), 0.7, wire_color))

    def _project_polygon(self, vertices: Sequence[Vec3], camera: SceneCamera) -> Optional[List[Vec2]]:
        projected: List[Vec2] = []
        for vertex in vertices:
            result = self._project_point(vertex, camera)
            if result is None:
                return None
            projected.append((result[0], result[1]))
        return projected

    @staticmethod
    def _polygon_bounding_rect(points: Sequence[Vec2]) -> Tuple[float, float, float, float]:
        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_y = max(point[1] for point in points)
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def _draw_projected_line(
        self,
        start: Vec3,
        end: Vec3,
        camera: SceneCamera,
        color: Tuple[float, float, float, float],
    ) -> None:
        start_proj = self._project_point(start, camera)
        end_proj = self._project_point(end, camera)
        if start_proj is None or end_proj is None:
            return
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(start_proj[0], start_proj[1])
        gl.glVertex2f(end_proj[0], end_proj[1])
        gl.glEnd()

    @staticmethod
    def _face_normal(vertices: Sequence[Vec3]) -> Vec3:
        if len(vertices) < 3:
            return (0.0, 0.0, 1.0)
        edge1 = (
            vertices[1][0] - vertices[0][0],
            vertices[1][1] - vertices[0][1],
            vertices[1][2] - vertices[0][2],
        )
        edge2 = (
            vertices[2][0] - vertices[0][0],
            vertices[2][1] - vertices[0][1],
            vertices[2][2] - vertices[0][2],
        )
        normal = OpeningSceneCutscene._cross3(edge1, edge2)
        return OpeningSceneCutscene._normalized3(normal)

    @staticmethod
    def _dot3(a: Vec3, b: Vec3) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _cross3(a: Vec3, b: Vec3) -> Vec3:
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    @staticmethod
    def _normalized3(vec: Vec3) -> Vec3:
        length = math.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])
        if length <= 0.0:
            return (0.0, 0.0, 1.0)
        return (vec[0] / length, vec[1] / length, vec[2] / length)


Cutscene = OpeningSceneCutscene
"""Alias used by external callers when referencing the default cutscene."""
