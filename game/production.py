"""Ship production queue utilities for bases and facilities."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, List, Optional

from .ship_registry import ShipDefinition, get_ship_definition


@dataclass
class ProductionJob:
    """Represents a single ship currently under construction."""

    ship_definition: ShipDefinition
    remaining_time: float


class ProductionQueue:
    """Simple FIFO production queue that tracks an active build."""

    def __init__(self) -> None:
        self._pending: Deque[ProductionJob] = deque()
        self._active: Optional[ProductionJob] = None

    def queue_ship(self, ship_name: str) -> ProductionJob:
        """Append a ship build using canonical stats from `ship_guidance`."""

        definition = get_ship_definition(ship_name)
        job = ProductionJob(ship_definition=definition, remaining_time=definition.build_time)
        self._pending.append(job)
        if self._active is None:
            self._start_next_job()
        return job

    def _start_next_job(self) -> None:
        if self._active is None and self._pending:
            self._active = self._pending.popleft()

    def cancel_all(self) -> None:
        """Clear the queue entirely – used if facilities are destroyed."""

        self._pending.clear()
        self._active = None

    def update(self, dt: float) -> List[ShipDefinition]:
        """Advance timers and return any ship definitions that completed."""

        completed: List[ShipDefinition] = []
        time_remaining = dt
        while time_remaining > 0.0:
            self._start_next_job()
            if self._active is None:
                break
            job = self._active
            if job.remaining_time > time_remaining:
                job.remaining_time -= time_remaining
                time_remaining = 0.0
            else:
                time_remaining -= job.remaining_time
                job.remaining_time = 0.0
                completed.append(job.ship_definition)
                self._active = None
        return completed

    @property
    def active_job(self) -> Optional[ProductionJob]:
        return self._active

    @property
    def queued_jobs(self) -> Iterable[ProductionJob]:
        return tuple(self._pending)

    # TODO: integrate resource consumption + facility gating logic from `game_guidance` / `research_guidance`.
