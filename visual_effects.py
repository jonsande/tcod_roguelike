from __future__ import annotations

import random
from typing import List, Sequence, Tuple, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from tcod.console import Console


class VisualEffect(Protocol):
    """Simple interface for visual effects that can update independently of turns."""

    def update(self, dt: float) -> None:
        ...

    def render(self, console: "Console", game_map: object) -> None:
        ...


class WindEffect:
    """Lateral particles that drift across the map to mimic wind/gusts."""

    def __init__(
        self,
        width: int,
        height: int,
        *,
        char: str = "-",
        color: Tuple[int, int, int] = (103, 86, 36),
        density: float = 0.008,
        speed_range: Sequence[float] = (48.0, 64.0),
        direction: int = 1,
        sound_enabled: bool = True,
    ):
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.char = char
        self.color = color
        self.sound_enabled = sound_enabled
        self.density = max(0.0, float(density))
        self.speed_min = float(speed_range[0]) if speed_range else 6.0
        self.speed_max = float(speed_range[-1]) if speed_range else self.speed_min
        self.direction = -1 if direction < 0 else 1
        self.particles: List[dict[str, float]] = []
        self._seed_particles()

    def _seed_particles(self) -> None:
        target_count = max(1, int(self.width * self.height * self.density))
        for _ in range(target_count):
            self.particles.append(
                {
                    "x": random.uniform(0, self.width),
                    "y": random.uniform(0, self.height),
                    "vx": self._random_speed(),
                    "vy": random.uniform(-0.25, 0.25),
                }
            )

    def _random_speed(self) -> float:
        speed = random.uniform(self.speed_min, self.speed_max)
        return speed * self.direction

    def update(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        if not self.particles:
            return
        for particle in self.particles:
            particle["x"] = (particle["x"] + particle["vx"] * dt) % self.width
            particle["y"] = (particle["y"] + particle["vy"] * dt) % self.height
            # Small vertical jitter to keep the motion organic.
            particle["vy"] += random.uniform(-0.05, 0.05)
            particle["vy"] = max(-0.35, min(0.35, particle["vy"]))

    def render(self, console: "Console", game_map: object) -> None:
        visible = getattr(game_map, "visible", None)
        for particle in self.particles:
            x = int(particle["x"]) % self.width
            y = int(particle["y"]) % self.height
            if visible is not None:
                try:
                    if not visible[x, y]:
                        continue
                except Exception:
                    pass
            console.print(x=x, y=y, string=self.char, fg=self.color)


__all__ = ["VisualEffect", "WindEffect"]
