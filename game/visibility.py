"""Fog-of-war helpers for Cosmogenesis."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Tuple

Vec2 = Tuple[float, float]


@dataclass(frozen=True)
class VisibilityCell:
    """Represents the state of a single fog-of-war grid cell."""

    explored: bool
    visual: bool
    radar: bool


class VisibilityGrid:
    """Maintains per-frame visibility masks derived from player sensors."""

    def __init__(self, world_width: float, world_height: float, cell_size: float = 200.0) -> None:
        self.world_width = world_width
        self.world_height = world_height
        self.cell_size = max(50.0, cell_size)
        self.cols = max(1, int(math.ceil(world_width / self.cell_size)))
        self.rows = max(1, int(math.ceil(world_height / self.cell_size)))
        self._explored: List[List[bool]] = [
            [False for _ in range(self.cols)] for _ in range(self.rows)
        ]
        self._visual: List[List[bool]] = [
            [False for _ in range(self.cols)] for _ in range(self.rows)
        ]
        self._radar: List[List[bool]] = [
            [False for _ in range(self.cols)] for _ in range(self.rows)
        ]

    # ------------------------------------------------------------------
    # Frame lifecycle
    # ------------------------------------------------------------------
    def begin_frame(self) -> None:
        for row in self._visual:
            for col in range(len(row)):
                row[col] = False
        for row in self._radar:
            for col in range(len(row)):
                row[col] = False

    # ------------------------------------------------------------------
    # Marking helpers
    # ------------------------------------------------------------------
    def mark_visual(self, position: Vec2, radius: float) -> None:
        for row, col in self._cells_in_radius(position, radius):
            self._visual[row][col] = True
            self._explored[row][col] = True

    def mark_radar(self, position: Vec2, radius: float) -> None:
        for row, col in self._cells_in_radius(position, radius):
            self._radar[row][col] = True
            self._explored[row][col] = True

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def is_visual(self, position: Vec2) -> bool:
        row, col = self._cell_index(position)
        return self._visual[row][col]

    def is_radar(self, position: Vec2) -> bool:
        row, col = self._cell_index(position)
        return self._radar[row][col]

    def is_explored(self, position: Vec2) -> bool:
        row, col = self._cell_index(position)
        return self._explored[row][col]

    def cells(self) -> Iterator[Tuple[int, int, VisibilityCell]]:
        for row in range(self.rows):
            for col in range(self.cols):
                yield row, col, VisibilityCell(
                    explored=self._explored[row][col],
                    visual=self._visual[row][col],
                    radar=self._radar[row][col],
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _cell_index(self, position: Vec2) -> Tuple[int, int]:
        return (self._row_from_coord(position[1]), self._col_from_coord(position[0]))

    def _col_from_coord(self, x: float) -> int:
        origin = -self.world_width * 0.5
        index = int((x - origin) / self.cell_size)
        return max(0, min(self.cols - 1, index))

    def _row_from_coord(self, y: float) -> int:
        origin = -self.world_height * 0.5
        index = int((y - origin) / self.cell_size)
        return max(0, min(self.rows - 1, index))

    def _cells_in_radius(self, position: Vec2, radius: float) -> Iterable[Tuple[int, int]]:
        if radius <= 0.0:
            row, col = self._cell_index(position)
            yield (row, col)
            return

        min_x = position[0] - radius
        max_x = position[0] + radius
        min_y = position[1] - radius
        max_y = position[1] + radius
        start_col = self._col_from_coord(min_x)
        end_col = self._col_from_coord(max_x)
        start_row = self._row_from_coord(min_y)
        end_row = self._row_from_coord(max_y)
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                yield (row, col)

    def cell_bounds(self, row: int, col: int) -> Tuple[float, float, float, float]:
        """Return the world-space rectangle covered by ``(row, col)``."""

        min_x = -self.world_width * 0.5 + col * self.cell_size
        max_x = min(min_x + self.cell_size, self.world_width * 0.5)
        min_y = -self.world_height * 0.5 + row * self.cell_size
        max_y = min(min_y + self.cell_size, self.world_height * 0.5)
        return (min_x, max_x, min_y, max_y)
