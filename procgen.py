from __future__ import annotations
from typing import Any, Dict, Iterator, List, Tuple, TYPE_CHECKING, Optional, Set
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
import heapq
import copy
from game_map import GameMap, GameMapTown
import tile_types
import random
import tcod
import numpy as np
import fixed_rooms
from entity_factories import *
import uniques
import settings
from entity import TableContainer, BookShelfContainer

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity
    
import entity_factories
import fixed_maps

# Direcciones cardinales (N, S, E, O) reutilizadas en varias rutinas.
CARDINAL_DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
# Número máximo de puertas por nivel
max_doors = settings.MAX_DOORS_BY_LEVEL
# Número de muros rompibles
max_breakable_walls = settings.MAX_BREAKABLE_WALLS

# Relative weights for non-rectangular room shapes (rectangle weight is always 1.0).
ROOM_SHAPE_WEIGHTS = settings.ROOM_SHAPE_WEIGHTS
ROOM_MIN_SIZE_SHAPES = settings.ROOM_MIN_SIZE_SHAPES
ROOM_DECORATION_CHANCE = settings.ROOM_DECORATION_CHANCE
FIXED_ROOM_CHANCES = settings.FIXED_ROOM_CHANCES
DUNGEON_EXTRA_CONNECTION_CHANCE = settings.DUNGEON_EXTRA_CONNECTION_CHANCE
DUNGEON_EXTRA_CONNECTION_ATTEMPTS = settings.DUNGEON_EXTRA_CONNECTION_ATTEMPTS

# Escombros máximos por planta
max_debris_by_floor = settings.MAX_DEBRIS_BY_FLOOR

# Items máximos por habitación
# Nivel mazmorra | nº items
treasure_floor = random.randint(5,9)
max_items_by_floor = settings.MAX_ITEMS_BY_FLOOR

# Monstruos máximos por habitación
# Nivel mazmorra | nº monstruos
max_monsters_by_floor = settings.MAX_MONSTERS_BY_FLOOR

chest_spawn_chances = settings.CHEST_SPAWN_CHANCES
chest_item_count_by_floor = settings.CHEST_ITEM_COUNT_BY_FLOOR
chest_loot_tables = settings.CHEST_LOOT_TABLES
table_spawn_chances = settings.TABLE_SPAWN_CHANCES
table_item_count_by_floor = settings.TABLE_ITEM_COUNT_BY_FLOOR
table_loot_tables = settings.TABLE_LOOT_TABLES
bookshelf_spawn_chances = settings.BOOKSHELF_SPAWN_CHANCES
bookshelf_item_count_by_floor = settings.BOOKSHELF_ITEM_COUNT_BY_FLOOR
bookshelf_loot_tables = settings.BOOKSHELF_LOOT_TABLES


def _resolve_entity_table(table_config):
    resolved: Dict[int, List[Tuple[Entity, int]]] = {}
    for floor, entries in table_config.items():
        resolved_entries = []
        for name, weight in entries:
            entity = getattr(entity_factories, name)
            resolved_entries.append((entity, weight))
        resolved[floor] = resolved_entries
    return resolved


def _get_spawn_display_name(entity: Entity) -> str:
    return getattr(entity, "id_name", getattr(entity, "name", "<Unknown>"))


class GenerationTracker:
    """Keeps track of how many entities spawned per floor."""

    def __init__(self) -> None:
        self._categories = ("items", "monsters")
        self._totals: Dict[str, Counter] = {cat: Counter() for cat in self._categories}
        self._procedural_totals: Dict[str, Counter] = {
            cat: Counter() for cat in self._categories
        }
        self._per_floor: Dict[str, Dict[int, Counter]] = {
            cat: defaultdict(Counter) for cat in self._categories
        }
        self._procedural_per_floor: Dict[str, Dict[int, Counter]] = {
            cat: defaultdict(Counter) for cat in self._categories
        }
        self._labels: Dict[str, Dict[str, str]] = {cat: {} for cat in self._categories}

    def register_label(self, category: str, key: str, label: str) -> None:
        if category in self._labels:
            self._labels[category][key] = label

    def record(
        self,
        category: Optional[str],
        floor: int,
        key: str,
        *,
        procedural: bool,
        source: str = "",
    ) -> None:
        if category not in self._totals:
            return
        self._totals[category][key] += 1
        self._per_floor[category][floor][key] += 1
        if procedural:
            self._procedural_totals[category][key] += 1
            self._procedural_per_floor[category][floor][key] += 1

    def get_total(self, category: str, key: str, *, procedural_only: bool = False) -> int:
        if category not in self._totals:
            return 0
        if procedural_only:
            return self._procedural_totals[category][key]
        return self._totals[category][key]

    def format_report(self, category: Optional[str] = None) -> str:
        categories = [category] if category else list(self._categories)
        lines: List[str] = []
        for cat in categories:
            if cat not in self._per_floor:
                continue
            lines.append(cat.capitalize())
            floors = self._per_floor[cat]
            if not floors:
                lines.append("  (sin datos)")
                continue
            for floor in sorted(floors.keys()):
                lines.append(f"  Nivel {floor}:")
                floor_counter = floors[floor]
                procedural_counter = self._procedural_per_floor[cat].get(floor, {})
                for key, count in sorted(floor_counter.items()):
                    label = self._labels[cat].get(key, key)
                    proc_count = procedural_counter.get(key, 0)
                    if proc_count and proc_count != count:
                        lines.append(f"    {label}: {count} (procedurales: {proc_count})")
                    elif proc_count:
                        lines.append(f"    {label}: {count} procedurales")
                    else:
                        lines.append(f"    {label}: {count}")
            totals = self._totals[cat]
            if totals:
                lines.append("  Totales:")
                for key, count in sorted(totals.items()):
                    label = self._labels[cat].get(key, key)
                    proc_count = self._procedural_totals[cat].get(key, 0)
                    if proc_count and proc_count != count:
                        lines.append(f"    {label}: {count} (procedurales: {proc_count})")
                    elif proc_count:
                        lines.append(f"    {label}: {count} procedurales")
                    else:
                        lines.append(f"    {label}: {count}")
        return "\n".join(lines)

    def reset(self) -> None:
        for cat in self._categories:
            self._totals[cat].clear()
            self._per_floor[cat].clear()
            self._procedural_totals[cat].clear()
            self._procedural_per_floor[cat].clear()


generation_tracker = GenerationTracker()


def _build_spawn_rule_entries(
    spawn_config: Dict[str, Dict],
    category: Optional[str],
    *,
    register_labels: bool = True,
) -> Dict[str, Dict]:
    resolved: Dict[str, Dict] = {}
    for name, config in spawn_config.items():
        entry = dict(config)
        entry.setdefault("min_floor", 1)
        entry.setdefault("base_weight", entry.get("base_weight", 0))
        entry.setdefault("weight_per_floor", entry.get("weight_per_floor", 0))
        entry.setdefault("max_instances", entry.get("max_instances"))
        entry.setdefault("min_instances", entry.get("min_instances"))
        entity = getattr(entity_factories, name)
        try:
            setattr(entity, "_spawn_key", name)
        except Exception:
            pass
        entry["entity"] = entity
        entry["name"] = name
        entry["display_name"] = _get_spawn_display_name(entity)
        progression = entry.get("weight_progression")
        if progression:
            entry["weight_progression"] = sorted(progression)
        if register_labels and category:
            generation_tracker.register_label(category, name, entry["display_name"])
        resolved[name] = entry
    return resolved


item_spawn_rules = _build_spawn_rule_entries(settings.ITEM_SPAWN_RULES, "items")
enemy_spawn_rules = _build_spawn_rule_entries(settings.ENEMY_SPAWN_RULES, "monsters")
cavern_monster_spawn_rules = _build_spawn_rule_entries(
    settings.CAVERN_MONSTER_SPAWN_RULES, None, register_labels=False
)
cavern_item_spawn_rules = _build_spawn_rule_entries(
    settings.CAVERN_ITEM_SPAWN_RULES, None, register_labels=False
)
debris_chances = _resolve_entity_table(settings.DEBRIS_CHANCES)
cavern_monster_count_by_floor = settings.CAVERN_MONSTER_COUNT_BY_FLOOR
cavern_item_count_by_floor = settings.CAVERN_ITEM_COUNT_BY_FLOOR

def _get_max_instances_for_item(key: str) -> Optional[int]:
    entry = item_spawn_rules.get(key)
    if not entry:
        return None
    return entry.get("max_instances")


def _get_spawn_key(entity: Entity, default: Optional[str] = None) -> Optional[str]:
    return getattr(entity, "_spawn_key", default)


def _can_spawn_item_procedurally(key: str, pending: Optional[Counter] = None) -> bool:
    max_instances = _get_max_instances_for_item(key)
    if max_instances is None:
        return True
    current = generation_tracker.get_total("items", key, procedural_only=True)
    if pending:
        current += pending.get(key, 0)
    return current < max_instances


def record_entity_spawned(
    entity: Entity,
    floor: int,
    category: str,
    *,
    key: Optional[str] = None,
    procedural: bool,
    source: str = "",
) -> None:
    resolved_key = key or _get_spawn_key(entity) or getattr(entity, "id_name", None) or getattr(entity, "name", None)
    if not resolved_key:
        return
    generation_tracker.record(
        category, floor, resolved_key, procedural=procedural, source=source
    )


def record_loot_items(loot: List[Entity], floor: int, *, procedural: bool, source: str) -> None:
    for item in loot:
        record_entity_spawned(
            item, floor, "items", procedural=procedural, source=source
        )


def _compute_target_min_instances(entry: Dict) -> Optional[int]:
    raw_min = entry.get("min_instances")
    if raw_min is None:
        return None
    try:
        target = int(raw_min)
    except (TypeError, ValueError):
        return None
    target = max(0, target)
    max_instances = entry.get("max_instances")
    if max_instances is not None:
        try:
            target = min(target, int(max_instances))
        except (TypeError, ValueError):
            pass
    return target


def _eligible_levels_for_rule(levels: List[GameMap], min_floor: int) -> List[Tuple[int, GameMap]]:
    return [(idx + 1, level) for idx, level in enumerate(levels) if (idx + 1) >= min_floor]


def _force_min_instances(
    entry: Dict,
    category: str,
    levels: List[GameMap],
    missing: int,
    *,
    source: str,
) -> None:
    min_floor = entry.get("min_floor", 1)
    candidates = _eligible_levels_for_rule(levels, min_floor)
    if not candidates:
        if settings.DEBUG_MODE and __debug__:
            print(f"DEBUG: Sin niveles elegibles para min_instances de {entry.get('name')}")
        return

    for _ in range(missing):
        placed = False
        for _ in range(100):
            floor, level = random.choice(candidates)
            x = random.randint(1, level.width - 2)
            y = random.randint(1, level.height - 2)
            if not _can_place_entity(level, x, y):
                continue
            spawned = entry["entity"].spawn(level, x, y)
            record_entity_spawned(
                spawned,
                floor,
                category,
                key=entry.get("name"),
                procedural=True,
                source=source,
            )
            placed = True
            break
        if not placed and settings.DEBUG_MODE and __debug__:
            print(f"DEBUG: No se pudo colocar instancia extra para {entry.get('name')}")


def enforce_minimum_spawns(levels: List[GameMap]) -> None:
    """Force-spawn entries that declare min_instances and haven't reached that count procedurally."""
    categories = [
        ("items", item_spawn_rules),
        ("monsters", enemy_spawn_rules),
    ]
    for category, rules in categories:
        for name, entry in rules.items():
            target = _compute_target_min_instances(entry)
            if target is None or target <= 0:
                continue
            current = generation_tracker.get_total(category, name, procedural_only=True)
            missing = max(0, target - current)
            if missing <= 0:
                continue
            _force_min_instances(
                entry,
                category,
                levels,
                missing,
                source="min_instances_enforcer",
            )


def _compute_rule_weight(entry: Dict, floor: int) -> float:
    min_floor = entry.get("min_floor", 1)
    if floor < min_floor:
        return 0.0
    weight = float(entry.get("base_weight", 0))
    progression = entry.get("weight_progression")
    if progression:
        for threshold, value in progression:
            if floor >= threshold:
                weight = float(value)
            else:
                break
    else:
        growth = float(entry.get("weight_per_floor", 0))
        weight += growth * max(0, floor - min_floor)
    return max(0.0, weight)


def _select_spawn_entries(
    rules: Dict[str, Dict],
    number_of_entities: int,
    floor: int,
    category: str,
) -> List[Dict]:
    selections: List[Dict] = []
    pending_counts: Counter = Counter()
    for _ in range(number_of_entities):
        candidates: List[Dict] = []
        weights: List[float] = []
        for entry in rules.values():
            if floor < entry.get("min_floor", 1):
                continue
            max_instances = entry.get("max_instances")
            current_total = generation_tracker.get_total(
                category, entry["name"], procedural_only=True
            )
            current_total += pending_counts.get(entry["name"], 0)
            if max_instances is not None and current_total >= max_instances:
                continue
            weight = _compute_rule_weight(entry, floor)
            if weight <= 0:
                continue
            candidates.append(entry)
            weights.append(weight)
        if not candidates:
            break
        choice = random.choices(candidates, weights=weights, k=1)[0]
        selections.append(choice)
        pending_counts[choice["name"]] += 1
    return selections


def _select_weighted_spawn_entries(
    rules: Dict[str, Dict],
    number_of_entities: int,
    floor: int,
    category: Optional[str] = None,
) -> List[Dict]:
    selections: List[Dict] = []
    pending_counts: Counter = Counter()
    for _ in range(number_of_entities):
        candidates: List[Dict] = []
        weights: List[float] = []
        for entry in rules.values():
            if floor < entry.get("min_floor", 1):
                continue
            max_instances = entry.get("max_instances")
            current_total = pending_counts.get(entry["name"], 0)
            if category:
                current_total += generation_tracker.get_total(
                    category, entry["name"], procedural_only=True
                )
            if max_instances is not None and current_total >= max_instances:
                continue
            weight = _compute_rule_weight(entry, floor)
            if weight <= 0:
                continue
            candidates.append(entry)
            weights.append(weight)
        if not candidates:
            break
        choice = random.choices(candidates, weights=weights, k=1)[0]
        selections.append(choice)
        pending_counts[choice["name"]] += 1
    return selections


def get_max_value_for_floor(
    max_value_by_floor: List[Tuple[int, int]], floor: int
) -> int:
    current_value = 0

    for floor_minimum, value in max_value_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

    return current_value


def get_floor_value(entries: List[Tuple[int, Any]], floor: int, default: Any) -> Any:
    """Return the last configured value whose floor requirement is <= current floor."""
    current_value = default
    for floor_minimum, value in entries:
        if floor_minimum > floor:
            break
        current_value = value
    return current_value


def get_entities_at_random(
    weighted_chances_by_floor: Dict[int, List[Tuple[Entity, int]]],
    number_of_entities: int,
    floor: int,
) -> List[Entity]:
    entity_weighted_chances = {}

    for key, values in weighted_chances_by_floor.items():
        if key > floor:
            break
        else:
            for value in values:
                entity = value[0]
                weighted_chance = value[1]

                entity_weighted_chances[entity] = weighted_chance

    entities = list(entity_weighted_chances.keys())
    entity_weighted_chance_values = list(entity_weighted_chances.values())

    chosen_entities = random.choices(
        entities, weights=entity_weighted_chance_values, k=number_of_entities
    )

    return chosen_entities


def choose_room_shape(width: int, height: int) -> str:
    """Pick a room shape based on available sizes and weights."""
    options: List[Tuple[str, float]] = [("rectangle", 1.0)]

    if min(width, height) >= ROOM_MIN_SIZE_SHAPES["circle"]:
        options.append(("circle", ROOM_SHAPE_WEIGHTS["circle"]))

    if width >= ROOM_MIN_SIZE_SHAPES["ellipse"] and height >= ROOM_MIN_SIZE_SHAPES["ellipse"]:
        options.append(("ellipse", ROOM_SHAPE_WEIGHTS["ellipse"]))

    if width >= ROOM_MIN_SIZE_SHAPES["cross"] and height >= ROOM_MIN_SIZE_SHAPES["cross"]:
        options.append(("cross", ROOM_SHAPE_WEIGHTS["cross"]))

    shapes, weights = zip(*options)
    return random.choices(shapes, weights=weights, k=1)[0]


class RectangularRoom:

    def __init__(self, x: int, y: int, width: int, height: int, shape: str = "rectangle"):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height
        self.shape = shape

        inner_width = max(1, self.x2 - self.x1 - 1)
        inner_height = max(1, self.y2 - self.y1 - 1)

        self.radius = max(2, min(inner_width, inner_height) // 2) if shape == "circle" else 0
        if shape == "ellipse":
            self.ellipse_axes = (
                max(2.0, inner_width / 2),
                max(2.0, inner_height / 2),
            )
        else:
            self.ellipse_axes = None

        if shape == "cross":
            self.cross_half_width_x = max(1, inner_width // 4)
            self.cross_half_width_y = max(1, inner_height // 4)
        else:
            self.cross_half_width_x = 0
            self.cross_half_width_y = 0

        self._cached_tiles: Optional[List[Tuple[int, int]]] = None

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y
    
    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)
    
    def intersects(self, other: RectangularRoom) -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )

    def iter_floor_tiles(self) -> Iterator[Tuple[int, int]]:
        """Yield every interior tile that belongs to this room."""
        if self.shape == "circle":
            cx, cy = self.center
            radius_sq = self.radius * self.radius
            for x in range(self.x1 + 1, self.x2):
                for y in range(self.y1 + 1, self.y2):
                    if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= radius_sq:
                        yield x, y
        elif self.shape == "ellipse" and self.ellipse_axes:
            cx, cy = self.center
            axis_x, axis_y = self.ellipse_axes
            axis_x_sq = axis_x * axis_x
            axis_y_sq = axis_y * axis_y
            for x in range(self.x1 + 1, self.x2):
                for y in range(self.y1 + 1, self.y2):
                    if (
                        ((x - cx) * (x - cx)) / axis_x_sq
                        + ((y - cy) * (y - cy)) / axis_y_sq
                    ) <= 1.0:
                        yield x, y
        elif self.shape == "cross":
            cx, cy = self.center
            for x in range(self.x1 + 1, self.x2):
                for y in range(self.y1 + 1, self.y2):
                    if (
                        abs(x - cx) <= self.cross_half_width_x
                        or abs(y - cy) <= self.cross_half_width_y
                    ):
                        yield x, y
        else:
            for x in range(self.x1 + 1, self.x2):
                for y in range(self.y1 + 1, self.y2):
                    yield x, y

    def random_location(self) -> Tuple[int, int]:
        """Return a random floor coordinate inside the room."""
        if self.shape == "rectangle":
            return (
                random.randint(self.x1 + 1, self.x2 - 1),
                random.randint(self.y1 + 1, self.y2 - 1),
            )

        if self._cached_tiles is None:
            self._cached_tiles = list(self.iter_floor_tiles())
        if not self._cached_tiles:
            return self.center
        return random.choice(self._cached_tiles)

    
class TownRoom:

    def __init__(self, x: int, y: int, width: int, height: int):
        # Para que no se generen muros en el borde le metemos el -1
        # y hacemos el tamaño del room más grande en el generate_town()
        self.x1 = x - 1
        self.y1 = y - 1
        self.x2 = width
        self.y2 = height

    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    def random_location(self) -> Tuple[int, int]:
        """Return a random interior coordinate inside the town room."""
        return (
            random.randint(self.x1 + 1, self.x2 - 1),
            random.randint(self.y1 + 1, self.y2 - 1),
        )


"""class FixedRoom:

    def __init__(self, x: int, y: int, width: int, height: int):
        # Para que no se generen muros en el borde le metemos el -1
        # y hacemos el tamaño del room más grande en el generate_town()
        self.x1 = x
        self.y1 = y
        self.x2 = width
        self.y2 = height

    @property
    def inner(self) -> Tuple[slice, slice]:
        #Return the inner area of this room as a 2D array index.
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y
"""


@dataclass
class RoomEntrance:
    inner: Tuple[int, int]
    outer: Tuple[int, int]
    direction: Tuple[int, int]
    connected: bool = False


@dataclass
class V2RoomNode:
    rect: RectangularRoom
    entrances: List[RoomEntrance]
    floor_tiles: Set[Tuple[int, int]]


OPPOSITE_DIRECTION = {
    (1, 0): (-1, 0),
    (-1, 0): (1, 0),
    (0, 1): (0, -1),
    (0, -1): (0, 1),
}


def _within_bounds(x: int, y: int, width: int, height: int, *, margin: int = 1) -> bool:
    if x < margin or y < margin:
        return False
    if x >= width - margin or y >= height - margin:
        return False
    return True


def _random_v2_room_dimensions() -> Tuple[int, int]:
    """Return actual RectangularRoom width/height for v2 generator."""
    interior_width = random.randint(
        settings.DUNGEON_V2_ROOM_MIN_SIZE,
        settings.DUNGEON_V2_ROOM_MAX_SIZE,
    )
    interior_height = random.randint(
        settings.DUNGEON_V2_ROOM_MIN_SIZE,
        settings.DUNGEON_V2_ROOM_MAX_SIZE,
    )
    # RectangularRoom digs tiles in the [x1 + 1, x2) range, so interior width = width - 1.
    width = max(2, interior_width + 1)
    height = max(2, interior_height + 1)
    return width, height


def _room_fits_within_bounds(room: RectangularRoom, map_width: int, map_height: int) -> bool:
    if room.x1 < 1 or room.y1 < 1:
        return False
    if room.x2 >= map_width - 1 or room.y2 >= map_height - 1:
        return False
    return True


def _gather_room_entry_candidates(
    room: RectangularRoom,
    map_width: int,
    map_height: int,
) -> List[RoomEntrance]:
    candidates: List[RoomEntrance] = []

    for x in range(room.x1 + 1, room.x2):
        north_inner = (x, room.y1 + 1)
        north_outer = (x, room.y1)
        if _within_bounds(north_outer[0], north_outer[1], map_width, map_height):
            candidates.append(RoomEntrance(north_inner, north_outer, (0, -1)))
        south_inner = (x, room.y2 - 1)
        south_outer = (x, room.y2)
        if _within_bounds(south_outer[0], south_outer[1], map_width, map_height):
            candidates.append(RoomEntrance(south_inner, south_outer, (0, 1)))

    for y in range(room.y1 + 1, room.y2):
        west_inner = (room.x1 + 1, y)
        west_outer = (room.x1, y)
        if _within_bounds(west_outer[0], west_outer[1], map_width, map_height):
            candidates.append(RoomEntrance(west_inner, west_outer, (-1, 0)))
        east_inner = (room.x2 - 1, y)
        east_outer = (room.x2, y)
        if _within_bounds(east_outer[0], east_outer[1], map_width, map_height):
            candidates.append(RoomEntrance(east_inner, east_outer, (1, 0)))

    return candidates


def _entrances_are_adjacent(a: RoomEntrance, b: RoomEntrance) -> bool:
    dx = abs(a.inner[0] - b.inner[0])
    dy = abs(a.inner[1] - b.inner[1])
    return dx <= 1 and dy <= 1


def _build_room_entrances(
    room: RectangularRoom,
    map_width: int,
    map_height: int,
    *,
    forced_entry: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
    min_entries: int = 1,
) -> Optional[List[RoomEntrance]]:
    candidates = _gather_room_entry_candidates(room, map_width, map_height)
    if not candidates:
        return None

    forced_instance: Optional[RoomEntrance] = None
    if forced_entry:
        forced_inner, forced_dir = forced_entry
        for candidate in candidates:
            if candidate.inner == forced_inner and candidate.direction == forced_dir:
                forced_instance = candidate
                break
        if not forced_instance:
            return None

    max_entries = min(4, len(candidates))
    min_entries = min(max_entries, max(1, min_entries))
    target_entries = random.randint(min_entries, max_entries)
    selected: List[RoomEntrance] = []

    if forced_instance:
        forced_instance.connected = True
        selected.append(forced_instance)
        candidates = [c for c in candidates if c is not forced_instance]
        target_entries = max(target_entries, min_entries)

    random.shuffle(candidates)
    for candidate in candidates:
        if len(selected) >= target_entries:
            break
        if any(_entrances_are_adjacent(candidate, existing) for existing in selected):
            continue
        selected.append(candidate)

    if len(selected) < min_entries:
        return None
    return selected


def _build_straight_corridor_path(
    start: Tuple[int, int],
    end: Tuple[int, int],
) -> Optional[List[Tuple[int, int]]]:
    if start == end:
        return [start]
    if start[0] != end[0] and start[1] != end[1]:
        return None

    path: List[Tuple[int, int]] = []
    if start[0] == end[0]:
        x = start[0]
        y_start = min(start[1], end[1])
        y_end = max(start[1], end[1])
        for y in range(y_start, y_end + 1):
            path.append((x, y))
    else:
        y = start[1]
        x_start = min(start[0], end[0])
        x_end = max(start[0], end[0])
        for x in range(x_start, x_end + 1):
            path.append((x, y))
    return path


def _corridor_path_is_clear(
    path: List[Tuple[int, int]],
    blocked_tiles: Set[Tuple[int, int]],
    *,
    allowed: Optional[Set[Tuple[int, int]]] = None,
) -> bool:
    allowed_positions = allowed or set()
    for coord in path:
        if coord in blocked_tiles and coord not in allowed_positions:
            return False
    return True


def _carve_corridor(
    dungeon: GameMap,
    path: List[Tuple[int, int]],
) -> None:
    for x, y in path:
        dungeon.tiles[x, y] = tile_types.floor


def _collect_room_floor_tiles(room: RectangularRoom) -> Set[Tuple[int, int]]:
    return set(room.iter_floor_tiles())


def _manhattan_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _rooms_intersect_with_padding(a: RectangularRoom, b: RectangularRoom, padding: int = 0) -> bool:
    return not (
        a.x2 + padding < b.x1
        or a.x1 - padding > b.x2
        or a.y2 + padding < b.y1
        or a.y1 - padding > b.y2
    )


def _room_contains_point(room: RectangularRoom, pt: Tuple[int, int]) -> bool:
    x, y = pt
    return room.x1 <= x < room.x2 and room.y1 <= y < room.y2


class _DisjointSet:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            self.parent[rx] = ry
        elif self.rank[rx] > self.rank[ry]:
            self.parent[ry] = rx
        else:
            self.parent[ry] = rx
            self.rank[rx] += 1
        return True


def _shortest_room_path(
    centers: List[Tuple[int, int]],
    connections: List[Tuple[int, int]],
    start_idx: int,
    goal_idx: int,
) -> List[int]:
    """Compute shortest path between rooms (by centers) using Dijkstra."""
    import heapq

    graph: Dict[int, List[Tuple[int, int]]] = {i: [] for i in range(len(centers))}
    for i, j in connections:
        w = _manhattan_distance(centers[i], centers[j])
        graph[i].append((j, w))
        graph[j].append((i, w))

    heap: List[Tuple[int, int]] = [(0, start_idx)]
    dist: Dict[int, int] = {start_idx: 0}
    prev: Dict[int, Optional[int]] = {start_idx: None}

    while heap:
        d, node = heapq.heappop(heap)
        if node == goal_idx:
            break
        if d != dist.get(node, 1_000_000):
            continue
        for neigh, w in graph.get(node, []):
            nd = d + w
            if nd < dist.get(neigh, 1_000_000):
                dist[neigh] = nd
                prev[neigh] = node
                heapq.heappush(heap, (nd, neigh))

    if goal_idx not in prev and goal_idx != start_idx:
        return []

    path: List[int] = []
    cursor: Optional[int] = goal_idx
    while cursor is not None:
        path.append(cursor)
        cursor = prev.get(cursor)
    path.reverse()
    return path


def _is_traversable_for_hot_path(
    dungeon: GameMap,
    x: int,
    y: int,
    *,
    allowed_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> bool:
    """Considera transitables suelo, puertas (abiertas o cerradas) y muros rompibles."""
    if not dungeon.in_bounds(x, y):
        return False
    if allowed_tiles is not None and (x, y) not in allowed_tiles:
        return False
    if dungeon.tiles["walkable"][x, y]:
        return True
    tile = dungeon.tiles[x, y]
    if np.array_equal(tile, tile_types.closed_door):
        return True
    if np.array_equal(tile, tile_types.breakable_wall):
        return True
    blocking = dungeon.get_blocking_entity_at_location(x, y)
    if blocking:
        name = getattr(blocking, "name", "").lower()
        if "door" in name or "wall" in name:
            return True
    return False


def _build_hot_path_cost(
    dungeon: GameMap,
    *,
    allowed_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> np.ndarray:
    """Coste de Pathfinder al estilo get_path_to: base walkable, puertas/rompibles con coste a 0, muros siguen a 0."""
    base_walkable = np.array(dungeon.tiles["walkable"], dtype=np.int16)
    cost = np.zeros_like(base_walkable, dtype=np.int16)
    cost[base_walkable.astype(bool)] = 1  # suelo normal

    for x in range(dungeon.width):
        for y in range(dungeon.height):
            tile = dungeon.tiles[x, y]
            if np.array_equal(tile, tile_types.closed_door):
                cost[x, y] = 2  # transitable, un poco peor que suelo
            elif np.array_equal(tile, tile_types.breakable_wall):
                cost[x, y] = 3  # transitable potencialmente, peor aún

    # for entity in dungeon.entities:
    #     if not getattr(entity, "blocks_movement", False):
    #         continue
    #     ex, ey = getattr(entity, "x", None), getattr(entity, "y", None)
    #     if ex is None or ey is None or not dungeon.in_bounds(ex, ey):
    #         continue
    #     if cost[ex, ey] == 0:
    #         continue  # no se reactiva un muro real
    #     # BUG: Si se añade algún coste, aunque sea 1, a veces preferirá atravesar muros
    #     # instransitables.
    #     cost[ex, ey] += 20  # Coste añadido si hay una entidad que bloquea el paso.

    return cost


def _compute_segment_path(
    dungeon: GameMap,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    *,
    allowed_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    """Camino más corto start->goal con Pathfinder, tratando puertas/muros rompibles como transitables."""
    if start == goal:
        return []
    if not dungeon.in_bounds(*start) or not dungeon.in_bounds(*goal):
        return []

    cost = _build_hot_path_cost(dungeon, allowed_tiles=None)
    if cost[start[0], start[1]] == 0 or cost[goal[0], goal[1]] == 0:
        return []
    graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
    pathfinder = tcod.path.Pathfinder(graph)
    pathfinder.add_root(start)
    try:
        raw_path: List[List[int]] = pathfinder.path_to(goal).tolist()
    except Exception:
        return []
    if len(raw_path) <= 1:
        return []
    return [(px, py) for px, py in raw_path[1:]]


def _compute_step_by_step_hot_path(
    dungeon: GameMap,
    centers_path: List[Tuple[int, int]],
    *,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    allowed_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    """Une start -> centros (en orden) -> goal concatenando caminos de Pathfinder."""
    if not centers_path:
        segment = _compute_segment_path(dungeon, start, goal, allowed_tiles=allowed_tiles)
        return segment

    full_path: List[Tuple[int, int]] = []
    current = start
    checkpoints = centers_path + [goal]
    for checkpoint in checkpoints:
        if current == checkpoint:
            continue
        segment = _compute_segment_path(dungeon, current, checkpoint, allowed_tiles=allowed_tiles)
        if not segment:
            return []
        if full_path and full_path[-1] == segment[0]:
            full_path.extend(segment[1:])
        else:
            full_path.extend(segment)
        current = checkpoint
    return full_path


def _is_valid_hot_path_step(dungeon: GameMap, x: int, y: int) -> bool:
    if not dungeon.in_bounds(x, y):
        return False
    if dungeon.tiles["walkable"][x, y]:
        return True
    tile = dungeon.tiles[x, y]
    if np.array_equal(tile, tile_types.closed_door):
        return True
    if np.array_equal(tile, tile_types.breakable_wall):
        return True
    return False


def _is_valid_hot_path(dungeon: GameMap, path: List[Tuple[int, int]]) -> bool:
    return all(_is_valid_hot_path_step(dungeon, x, y) for x, y in path)


def build_step_by_step_hot_path(
    dungeon: GameMap,
    *,
    centers: Optional[List[Tuple[int, int]]] = None,
    start: Optional[Tuple[int, int]] = None,
    goal: Optional[Tuple[int, int]] = None,
) -> List[Tuple[int, int]]:
    """Calcula el camino paso a paso usando rooms_hot_path, y lo valida."""
    centers_path = centers if centers is not None else getattr(dungeon, "rooms_hot_path", []) or getattr(dungeon, "hot_path", [])

    if start is None:
        player = getattr(getattr(dungeon, "engine", None), "player", None)
        if player and getattr(player, "gamemap", None) is dungeon:
            start = (player.x, player.y)
        elif getattr(dungeon, "upstairs_location", None):
            start = dungeon.upstairs_location
        elif centers_path:
            start = centers_path[0]
        else:
            start = (0, 0)
    if goal is None:
        goal = getattr(dungeon, "downstairs_location", None) or start

    path = _compute_step_by_step_hot_path(
        dungeon,
        centers_path,
        start=start,
        goal=goal,
        allowed_tiles=None,
    )
    if not _is_valid_hot_path(dungeon, path):
        return []
    return path

def _shortest_tile_path(
    dungeon: GameMap,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    *,
    allowed_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    """Dijkstra sobre rejilla cardinal usando _is_traversable_for_hot_path."""
    import heapq

    def _nearest_traversable(pt: Tuple[int, int], allowed_tiles: Optional[Set[Tuple[int, int]]]) -> Optional[Tuple[int, int]]:
        if _is_traversable_for_hot_path(dungeon, *pt, allowed_tiles=allowed_tiles):
            return pt
        from collections import deque
        seen = {pt}
        q = deque([pt])
        while q:
            x, y = q.popleft()
            for dx, dy in CARDINAL_DIRECTIONS:
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                if not dungeon.in_bounds(nx, ny):
                    continue
                if _is_traversable_for_hot_path(dungeon, nx, ny, allowed_tiles=allowed_tiles):
                    return (nx, ny)
                q.append((nx, ny))
        return None

    start_pt = _nearest_traversable(start, allowed_tiles)
    goal_pt = _nearest_traversable(goal, allowed_tiles)
    if not start_pt or not goal_pt:
        return []
    if start_pt == goal_pt:
        return [start_pt]

    heap: List[Tuple[int, Tuple[int, int]]] = [(0, start_pt)]
    dist: Dict[Tuple[int, int], int] = {start_pt: 0}
    prev: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start_pt: None}

    while heap:
        d, (x, y) = heapq.heappop(heap)
        if (x, y) == goal_pt:
            break
        if d != dist.get((x, y), 1_000_000):
            continue
        for dx, dy in CARDINAL_DIRECTIONS:
            nx, ny = x + dx, y + dy
            if not _is_traversable_for_hot_path(dungeon, nx, ny, allowed_tiles=allowed_tiles):
                continue
            nd = d + 1
            if nd < dist.get((nx, ny), 1_000_000):
                dist[(nx, ny)] = nd
                prev[(nx, ny)] = (x, y)
                heapq.heappush(heap, (nd, (nx, ny)))

    if goal_pt not in prev and goal_pt != start_pt:
        return []

    path: List[Tuple[int, int]] = []
    cursor: Optional[Tuple[int, int]] = goal_pt
    while cursor is not None:
        path.append(cursor)
        cursor = prev.get(cursor)
    path.reverse()
    return path


def _get_door_entity_at(dungeon: GameMap, x: int, y: int):
    for ent in dungeon.entities:
        if getattr(ent, "x", None) == x and getattr(ent, "y", None) == y:
            name = getattr(ent, "name", "").lower()
            if "door" in name:
                return ent
    return None


def _is_locked_door(dungeon: GameMap, x: int, y: int) -> bool:
    tile = dungeon.tiles[x, y]
    if not np.array_equal(tile, tile_types.closed_door):
        # Si el tile no es puerta cerrada, asumimos que no bloquea por cerradura.
        return False
    ent = _get_door_entity_at(dungeon, x, y)
    if not ent:
        return False
    fighter = getattr(ent, "fighter", None)
    if not fighter:
        return False
    if getattr(fighter, "is_open", False):
        return False
    return bool(getattr(fighter, "lock_color", None))


def _is_traversable_for_green_zone(dungeon: GameMap, x: int, y: int) -> bool:
    """Considera transitables suelo, puertas (incluyendo cerradas sin llave) y muros rompibles. Bloquea puertas cerradas con llave."""
    if not dungeon.in_bounds(x, y):
        return False
    if _is_locked_door(dungeon, x, y):
        return False
    if dungeon.tiles["walkable"][x, y]:
        return True
    tile = dungeon.tiles[x, y]
    if np.array_equal(tile, tile_types.closed_door):
        return True
    if np.array_equal(tile, tile_types.breakable_wall):
        return True
    blocking = dungeon.get_blocking_entity_at_location(x, y)
    if blocking:
        name = getattr(blocking, "name", "").lower()
        if "wall" in name:
            return True
        if "door" in name and not _is_locked_door(dungeon, x, y):
            return True
    return False

# BUG: La idea parecía buena, pero muchas veces no está funcionando.
def green_zone(dungeon: GameMap, origin: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Devuelve centros de salas alcanzables desde origin sin atravesar puertas cerradas con llave."""
    from collections import deque

    if not dungeon.in_bounds(*origin):
        return []

    visited: Set[Tuple[int, int]] = set()
    q = deque([origin])
    visited.add(origin)

    while q:
        x, y = q.popleft()
        for dx, dy in CARDINAL_DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (nx, ny) in visited:
                continue
            if not _is_traversable_for_green_zone(dungeon, nx, ny):
                continue
            visited.add((nx, ny))
            q.append((nx, ny))

    return [center for center in getattr(dungeon, "center_rooms", []) if center in visited]


def _draw_green_zone(
    dungeon: GameMap,
    origin: Tuple[int, int],
    *,
    dark_color: Tuple[int, int, int] = (50, 180, 50),
    light_color: Tuple[int, int, int] = (90, 255, 90),
) -> None:
    """Colorea los centros de las habitaciones alcanzables desde origin sin pasar por puertas cerradas con llave."""
    zone = green_zone(dungeon, origin)
    if not zone:
        return
    for cx, cy in zone:
        if not dungeon.in_bounds(cx, cy):
            continue
        dungeon.tiles["dark"]["fg"][cx, cy] = dark_color
        dungeon.tiles["light"]["fg"][cx, cy] = light_color

# BUG: Funciona bastante bien, pero sigue incluyendo algunas casillas intransitables en el
# camino. Esto ya pasó al intentar programar el movimiento de los adventurers. Al final lo
# solucionamos (no sé por qué [P.D: ahora sí sé por qué; ver más abajo]) buscando el camino más corto "por fases"; es decir, buscando
# primero el camino más corte de la habitación A a la B (sin tener en cuenta el destino
# final total), y repitiendo. En este caso las habitaciones elegidas deberían extraerse de
# del hot_path (a saber, la serie de los centros de las habitaciones que componen el camino
# más corto a las escaleras). [P.D.: hay que usar el pathfinder de tcod, que es lo que usan
# los actores para buscar el camino de un punto a otro]
def _draw_hot_path(
    dungeon: GameMap,
    shortest_path: Optional[List[Tuple[int, int]]] = None,
    *,
    dark_color: Tuple[int, int, int] = (180, 50, 50),
    light_color: Tuple[int, int, int] = (255, 90, 90),
    allowed_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> None:
    """Pinta el camino paso a paso (ya calculado) sobre el mapa para depuración."""
    if shortest_path is None:
        shortest_path = getattr(dungeon, "step_by_step_hot_path", [])
    if not shortest_path:
        return

    for x, y in shortest_path:
        if not dungeon.in_bounds(x, y):
            continue
        if dungeon.upstairs_location and (x, y) == dungeon.upstairs_location:
            continue
        if dungeon.downstairs_location and (x, y) == dungeon.downstairs_location:
            continue
        dungeon.tiles["dark"]["fg"][x, y] = dark_color
        dungeon.tiles["light"]["fg"][x, y] = light_color


def _collect_hot_path_coords(
    dungeon: GameMap,
    hot_path: List[Tuple[int, int]],
    *,
    allowed_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    coords: List[Tuple[int, int]] = []
    if len(hot_path) < 2:
        return []
    for a, b in zip(hot_path[:-1], hot_path[1:]):
        segment = _shortest_tile_path(dungeon, a, b, allowed_tiles=allowed_tiles)
        if not segment:
            continue
        segment = [pt for pt in segment if _is_traversable_for_hot_path(dungeon, *pt, allowed_tiles=allowed_tiles)]
        if not segment:
            continue
        if coords and coords[-1] == segment[0]:
            coords.extend(segment[1:])
        else:
            coords.extend(segment)
    return coords


def _normalize_feature_probs(raw: Dict[str, float]) -> List[Tuple[str, float]]:
    options = []
    for key, value in raw.items():
        try:
            weight = float(value)
        except Exception:
            weight = 0.0
        if weight > 0:
            options.append((key, weight))
    if not options:
        return [("none", 1.0)]
    total = sum(w for _, w in options)
    return [(k, w / total) for k, w in options]


def _collect_room_entry_candidates_v3(
    dungeon: GameMap,
    room_tiles: Set[Tuple[int, int]],
    dug_tiles: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    """Return corridor tiles adyacentes a la sala (no dentro de la sala)."""
    candidates: Set[Tuple[int, int]] = set()
    for x, y in room_tiles:
        for dx, dy in CARDINAL_DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (nx, ny) in room_tiles:
                continue
            if not dungeon.in_bounds(nx, ny):
                continue
            if not dungeon.tiles["walkable"][nx, ny]:
                continue
            if dug_tiles is not None:
                dug_tiles.add((nx, ny))
            candidates.add((nx, ny))
    return list(candidates)


def _maybe_place_entry_feature(
    dungeon: GameMap,
    coord: Tuple[int, int],
    options: List[Tuple[str, float]],
    *,
    room_center: Optional[Tuple[int, int]] = None,
    lock_chance: float = 0.0,
    dug_tiles: Optional[Set[Tuple[int, int]]] = None,
    allowed_lock_colors: Optional[List[str]] = None,
    locked_colors_registry: Optional[Set[str]] = None,
) -> None:
    def _has_opposing_walls(x: int, y: int) -> bool:
        north = dungeon.in_bounds(x, y - 1) and not dungeon.tiles["walkable"][x, y - 1]
        south = dungeon.in_bounds(x, y + 1) and not dungeon.tiles["walkable"][x, y + 1]
        east = dungeon.in_bounds(x + 1, y) and not dungeon.tiles["walkable"][x + 1, y]
        west = dungeon.in_bounds(x - 1, y) and not dungeon.tiles["walkable"][x - 1, y]
        return (north and south) or (east and west)

    if dungeon.upstairs_location and coord == dungeon.upstairs_location:
        return
    if dungeon.downstairs_location and coord == dungeon.downstairs_location:
        return
    if any(ent.x == coord[0] and ent.y == coord[1] for ent in dungeon.entities):
        return
    if not _has_opposing_walls(coord[0], coord[1]):
        return

    keys, weights = zip(*options)
    choice = random.choices(keys, weights=weights, k=1)[0]
    x, y = coord

    if choice == "door":
        lock_color: Optional[str] = None
        if lock_chance > 0 and random.random() < lock_chance:
            palette = allowed_lock_colors if allowed_lock_colors is not None else list(entity_factories.KEY_COLORS)
            if palette:
                lock_color = random.choice(palette)
        dungeon.tiles[x, y] = tile_types.closed_door
        spawn_door_entity(dungeon, x, y, lock_color=lock_color, room_center=room_center)
        if dug_tiles is not None:
            dug_tiles.add((x, y))
        if lock_color and locked_colors_registry is not None:
            locked_colors_registry.add(lock_color)
    elif choice == "breakable":
        convert_tile_to_breakable(dungeon, x, y)
        if dug_tiles is not None:
            dug_tiles.add((x, y))


def _choose_room_location_for_entry(
    width: int,
    height: int,
    target_inner: Tuple[int, int],
    direction: Tuple[int, int],
    map_width: int,
    map_height: int,
) -> Optional[Tuple[int, int]]:
    """Place a room so that `target_inner` lies on the wall defined by `direction`."""
    tx, ty = target_inner

    def _clamp_range(a: int, b: int) -> Optional[int]:
        if a > b:
            return None
        return random.randint(a, b)

    if direction == (1, 0):
        # Entrada en pared este: target_inner = x2 - 1
        x1 = tx - (width - 1)
        if x1 < 1 or x1 + width >= map_width - 1:
            return None
        y_min = max(1, ty - (height - 1))
        y_max = min(map_height - height - 1, ty - 1)
        y1 = _clamp_range(y_min, y_max)
        if y1 is None:
            return None
        return x1, y1

    if direction == (-1, 0):
        # Entrada en pared oeste: target_inner = x1 + 1
        x1 = tx - 1
        if x1 < 1 or x1 + width >= map_width - 1:
            return None
        y_min = max(1, ty - (height - 1))
        y_max = min(map_height - height - 1, ty - 1)
        y1 = _clamp_range(y_min, y_max)
        if y1 is None:
            return None
        return x1, y1

    if direction == (0, 1):
        # Entrada en pared sur: target_inner = y2 - 1
        y1 = ty - (height - 1)
        if y1 < 1 or y1 + height >= map_height - 1:
            return None
        x_min = max(1, tx - (width - 1))
        x_max = min(map_width - width - 1, tx - 1)
        x1 = _clamp_range(x_min, x_max)
        if x1 is None:
            return None
        return x1, y1

    if direction == (0, -1):
        # Entrada en pared norte: target_inner = y1 + 1
        y1 = ty - 1
        if y1 < 1 or y1 + height >= map_height - 1:
            return None
        x_min = max(1, tx - (width - 1))
        x_max = min(map_width - width - 1, tx - 1)
        x1 = _clamp_range(x_min, x_max)
        if x1 is None:
            return None
        return x1, y1

    return None


def _create_initial_v2_room(
    dungeon: GameMap,
    floor_number: int,
    *,
    place_player: bool,
    upstairs_location: Optional[Tuple[int, int]],
    room_tiles_global: Set[Tuple[int, int]],
) -> Optional[Tuple[V2RoomNode, Tuple[int, int]]]:
    attempts = settings.DUNGEON_V2_ROOM_PLACEMENT_ATTEMPTS
    for _ in range(attempts):
        width, height = _random_v2_room_dimensions()
        if dungeon.width - width - 2 <= 1 or dungeon.height - height - 2 <= 1:
            return None
        if upstairs_location:
            anchor_x, anchor_y = upstairs_location
            x1 = max(1, min(anchor_x - width // 2, dungeon.width - width - 2))
            y1 = max(1, min(anchor_y - height // 2, dungeon.height - height - 2))
        else:
            max_x = max(1, dungeon.width - width - 2)
            max_y = max(1, dungeon.height - height - 2)
            x1 = random.randint(1, max_x)
            y1 = random.randint(1, max_y)

        room = RectangularRoom(x1, y1, width, height)
        if not _room_fits_within_bounds(room, dungeon.width, dungeon.height):
            continue

        entries = _build_room_entrances(
            room,
            dungeon.width,
            dungeon.height,
            min_entries=1,
        )
        if not entries:
            continue

        if upstairs_location:
            if (
                upstairs_location[0] <= room.x1
                or upstairs_location[0] >= room.x2
                or upstairs_location[1] <= room.y1
                or upstairs_location[1] >= room.y2
            ):
                continue
            upstairs_coord = upstairs_location
        else:
            upstairs_coord = room.center

        carve_room(dungeon, room)
        floor_tiles = _collect_room_floor_tiles(room)
        room_tiles_global.update(floor_tiles)

        dungeon.tiles[upstairs_coord] = tile_types.up_stairs
        dungeon.upstairs_location = upstairs_coord

        if place_player:
            dungeon.engine.player.place(*upstairs_coord, dungeon)
            entry_point = (dungeon.engine.player.x, dungeon.engine.player.y)
        else:
            entry_point = upstairs_coord

        place_entities(room, dungeon, floor_number)
        uniques.place_uniques(floor_number, room.center, dungeon)

        return V2RoomNode(room, entries, floor_tiles), entry_point
    return None


def _expand_room_from_entry(
    dungeon: GameMap,
    *,
    parent_entry: RoomEntrance,
    floor_number: int,
    room_tiles_global: Set[Tuple[int, int]],
    corridor_tiles: Set[Tuple[int, int]],
    rooms: List[V2RoomNode],
) -> Optional[V2RoomNode]:
    attempts = settings.DUNGEON_V2_ROOM_PLACEMENT_ATTEMPTS
    min_distance = settings.DUNGEON_V2_MIN_ROOM_DISTANCE
    max_distance = settings.DUNGEON_V2_MAX_ROOM_DISTANCE

    for _ in range(attempts):
        corridor_length = random.randint(min_distance, max_distance)
        target_inner = (
            parent_entry.inner[0] + parent_entry.direction[0] * corridor_length,
            parent_entry.inner[1] + parent_entry.direction[1] * corridor_length,
        )
        if not _within_bounds(target_inner[0], target_inner[1], dungeon.width, dungeon.height):
            continue

        width, height = _random_v2_room_dimensions()
        anchor = _choose_room_location_for_entry(
            width,
            height,
            target_inner,
            OPPOSITE_DIRECTION[parent_entry.direction],
            dungeon.width,
            dungeon.height,
        )
        if not anchor:
            continue
        x1, y1 = anchor
        room = RectangularRoom(x1, y1, width, height)
        if not _room_fits_within_bounds(room, dungeon.width, dungeon.height):
            continue
        if any(room.intersects(node.rect) for node in rooms):
            continue

        room_tiles = _collect_room_floor_tiles(room)
        if room_tiles & (room_tiles_global | corridor_tiles):
            continue

        forced_dir = OPPOSITE_DIRECTION[parent_entry.direction]
        entries = _build_room_entrances(
            room,
            dungeon.width,
            dungeon.height,
            forced_entry=(target_inner, forced_dir),
            min_entries=1,
        )
        if not entries:
            continue

        forced_entry = next((entry for entry in entries if entry.inner == target_inner), None)
        if not forced_entry:
            continue

        path = _build_straight_corridor_path(parent_entry.inner, target_inner)
        if not path:
            continue
        allowed_tiles = {parent_entry.inner, target_inner}
        if not _corridor_path_is_clear(path, room_tiles_global, allowed=allowed_tiles):
            continue

        carve_room(dungeon, room)
        room_tiles_global.update(room_tiles)
        _carve_corridor(dungeon, path)
        corridor_tiles.update(path)

        forced_entry.connected = True
        node = V2RoomNode(room, entries, room_tiles)

        place_entities(room, dungeon, floor_number)
        uniques.place_uniques(floor_number, room.center, dungeon)

        return node
    return None


def _can_place_entity(dungeon: GameMap, x: int, y: int) -> bool:
    if not dungeon.in_bounds(x, y):
        return False
    if not dungeon.tiles["walkable"][x, y]:
        return False
    if (x, y) == dungeon.downstairs_location:
        return False
    if dungeon.upstairs_location and (x, y) == dungeon.upstairs_location:
        return False
    if any(existing.x == x and existing.y == y for existing in dungeon.entities):
        return False
    return True


def _place_town_old_man_with_campfire(
    dungeon: GameMapTown,
    *,
    stairs_location: Optional[Tuple[int, int]],
    floor_number: int,
) -> None:
    """Place El viejo and his eternal campfire near the Town stairs."""
    if not stairs_location:
        return

    stairs_x, stairs_y = stairs_location
    preferred_offsets = [8, 9]
    old_man_position: Optional[Tuple[int, int]] = None
    base_y = stairs_y + 2

    for offset in preferred_offsets:
        candidate_x = stairs_x - offset
        if candidate_x < 0:
            continue
        candidate = (candidate_x, base_y)
        if _can_place_entity(dungeon, *candidate):
            old_man_position = candidate
            break

    if old_man_position is None:
        # Fall back to tiles nearby but still west of the stairs.
        for offset in preferred_offsets:
            candidate_x = stairs_x - offset
            if candidate_x < 0:
                continue
            for y_delta in (0, -1, 1, -2, 2):
                candidate = (candidate_x, base_y + y_delta)
                if _can_place_entity(dungeon, *candidate):
                    old_man_position = candidate
                    break
            if old_man_position:
                break

    if old_man_position is None:
        return

    entity_factories.old_man.spawn(dungeon, *old_man_position)

    preferred_direction = 1 if stairs_x >= old_man_position[0] else -1
    neighbor_priority = [(preferred_direction, 0)]
    fallback_offsets = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ]
    for offset in fallback_offsets:
        if offset not in neighbor_priority:
            neighbor_priority.append(offset)

    campfire_position: Optional[Tuple[int, int]] = None
    for dx, dy in neighbor_priority:
        cx, cy = old_man_position[0] + dx, old_man_position[1] + dy
        if _can_place_entity(dungeon, cx, cy):
            entity_factories.eternal_campfire.spawn(dungeon, cx, cy)
            campfire_position = (cx, cy)
            break

    if campfire_position is None:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue
                cx, cy = old_man_position[0] + dx, old_man_position[1] + dy
                if _can_place_entity(dungeon, cx, cy):
                    entity_factories.eternal_campfire.spawn(dungeon, cx, cy)
                    campfire_position = (cx, cy)
                    break
            if campfire_position:
                break

    _place_town_old_man_chest(dungeon, old_man_position, floor_number)


def _place_town_old_man_chest(
    dungeon: GameMapTown,
    old_man_position: Tuple[int, int],
    floor_number: int,
) -> None:
    """Place a guaranteed chest near the town old man when on floor 1."""
    if floor_number != 1:
        return

    # Ítems aleatorios en el cofre del viejo
    loot_random = _build_chest_loot(floor_number)
    loot_bonus = _build_old_man_bonus_loot()
    loot_static: List[Entity] = []

    # Ítems garantizados en el cofre del viejo
    for key in settings.OLD_MAN_CHEST:
        prototype = getattr(entity_factories, key, None)
        if prototype is None:
            continue
        loot_static.append(copy.deepcopy(prototype))

    loot: List[Entity] = []
    loot.extend(loot_random)
    loot.extend(loot_bonus)
    loot.extend(loot_static)

    if not loot:
        return

    chest_offsets = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
        (2, 0),
        (-2, 0),
        (0, 2),
        (0, -2),
    ]
    for dx, dy in chest_offsets:
        chest_x = old_man_position[0] + dx - 1
        chest_y = old_man_position[1] + dy + 1
        if not _can_place_entity(dungeon, chest_x, chest_y):
            continue
        chest_entity = entity_factories.chest.spawn(dungeon, chest_x, chest_y)
        entity_factories.fill_chest_with_items(chest_entity, loot)
        record_loot_items(
            loot_random, floor_number, procedural=True, source="old_man_chest"
        )
        record_loot_items(
            loot_bonus, floor_number, procedural=True, source="old_man_chest_bonus"
        )
        record_loot_items(
            loot_static, floor_number, procedural=False, source="old_man_chest_static"
        )
        return


def _build_old_man_bonus_loot() -> List[Entity]:
    """Return additional random loot for the Old Man chest."""
    pool = getattr(settings, "OLD_MAN_RANDOM_ITEM_POOL", None)
    count_config = getattr(settings, "OLD_MAN_RANDOM_ITEM_COUNT", 0)

    if not pool:
        return []

    weighted_pool: List[Tuple[str, float]] = []
    for entry in pool:
        if isinstance(entry, str):
            key = entry
            weight = 1.0
        elif isinstance(entry, (tuple, list)) and entry:
            key = entry[0]
            weight = entry[1] if len(entry) > 1 else 1.0
        else:
            continue

        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            continue

        if not key or weight_value <= 0:
            continue
        weighted_pool.append((key, weight_value))

    if not weighted_pool:
        return []

    def _normalize_count_range(value: Any) -> Tuple[int, int]:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            minimum = max(0, int(value[0]))
            maximum = max(0, int(value[1]))
        else:
            minimum = maximum = max(0, int(value))
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        return minimum, maximum

    try:
        min_count, max_count = _normalize_count_range(count_config)
    except (TypeError, ValueError):
        return []

    if max_count <= 0:
        return []

    picks = random.randint(min_count, max_count)
    if picks <= 0:
        return []

    keys = [entry[0] for entry in weighted_pool]
    weights = [entry[1] for entry in weighted_pool]
    chosen_keys = random.choices(keys, weights=weights, k=picks)

    bonus_loot: List[Entity] = []
    pending_counts: Counter = Counter()
    for item_key in chosen_keys:
        if not _can_spawn_item_procedurally(item_key, pending_counts):
            continue
        prototype = getattr(entity_factories, item_key, None)
        if prototype is None:
            continue
        bonus_loot.append(copy.deepcopy(prototype))
        pending_counts[item_key] += 1

    return bonus_loot


def _spawn_entity_template(
    entity: Entity,
    location_provider,
    dungeon: GameMap,
    floor_number: int,
    debug_name: str,
    context: str,
    category: Optional[str] = None,
    rule_name: Optional[str] = None,
) -> None:
    placed = False
    for _ in range(20):
        x, y = location_provider()
        if not _can_place_entity(dungeon, x, y):
            continue
        entity.spawn_coord = (x, y)
        spawned = entity.spawn(dungeon, x, y)
        _maybe_fill_container_loot(spawned, floor_number)
        if category and rule_name:
            record_entity_spawned(
                spawned, floor_number, category, key=rule_name, procedural=True, source=context
            )
        if settings.DEBUG_MODE and __debug__:
            print(f"DEBUG: Generando... {debug_name} en x={x} y={y}")
        placed = True
        break
    if settings.DEBUG_MODE:
        if not placed and __debug__:
            print(f"DEBUG: Failed to place {debug_name} en {context}")


def place_entities(room: RectangularRoom, dungeon: GameMap, floor_number: int,) -> None:
    number_of_monsters = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
    )
    number_of_items = random.randint(
        0, get_max_value_for_floor(max_items_by_floor, floor_number)
    )
    number_of_debris = random.randint(
        0, get_max_value_for_floor(max_debris_by_floor, floor_number)
    )

    monsters = _select_spawn_entries(
        enemy_spawn_rules, number_of_monsters, floor_number, "monsters"
    )
    items = _select_spawn_entries(
        item_spawn_rules, number_of_items, floor_number, "items"
    )
    debris: List[Entity] = get_entities_at_random(
        debris_chances, number_of_debris, floor_number
    )

    location_provider = room.random_location
    context = f"room at {room.center}"

    for entry in monsters:
        _spawn_entity_template(
            entry["entity"],
            location_provider,
            dungeon,
            floor_number,
            entry["display_name"],
            context,
            "monsters",
            entry["name"],
        )

    for entry in items:
        _spawn_entity_template(
            entry["entity"],
            location_provider,
            dungeon,
            floor_number,
            entry["display_name"],
            context,
            "items",
            entry["name"],
        )

    for entity in debris:
        _spawn_entity_template(
            entity,
            location_provider,
            dungeon,
            floor_number,
            entity.name,
            context,
        )


def _select_loot_table_for_floor(
    loot_tables_by_floor: Dict[int, List[Tuple[str, float]]], floor: int
) -> List[Tuple[str, float]]:
    if not loot_tables_by_floor:
        return []
    selected: List[Tuple[str, float]] = []
    for min_floor in sorted(loot_tables_by_floor.keys()):
        if min_floor > floor:
            break
        selected = loot_tables_by_floor[min_floor]
    return selected


def _build_loot_for_floor(
    loot_tables_by_floor: Dict[int, List[Tuple[str, float]]],
    item_count_by_floor: List[Tuple[int, Tuple[int, int]]],
    floor: int,
) -> List[Entity]:
    loot_entries = _select_loot_table_for_floor(loot_tables_by_floor, floor)
    if not loot_entries:
        return []
    min_items, max_items = get_floor_value(item_count_by_floor, floor, (0, 0))
    if max_items <= 0 or min_items > max_items:
        return []
    count = random.randint(min_items, max_items)
    if count <= 0:
        return []
    keys = [entry[0] for entry in loot_entries]
    weights = [float(entry[1]) for entry in loot_entries]
    chosen_keys = random.choices(keys, weights=weights, k=count)
    loot: List[Entity] = []
    pending_counts: Counter = Counter()
    for key in chosen_keys:
        if not _can_spawn_item_procedurally(key, pending_counts):
            continue
        prototype = getattr(entity_factories, key, None)
        if not prototype:
            continue
        loot.append(copy.deepcopy(prototype))
        pending_counts[key] += 1
    return loot


def _select_chest_loot_table(floor: int) -> List[Tuple[str, float]]:
    return _select_loot_table_for_floor(chest_loot_tables, floor)


def _build_chest_loot(floor: int) -> List[Entity]:
    return _build_loot_for_floor(chest_loot_tables, chest_item_count_by_floor, floor)


def _select_table_loot_table(floor: int) -> List[Tuple[str, float]]:
    return _select_loot_table_for_floor(table_loot_tables, floor)


def _build_table_loot(floor: int) -> List[Entity]:
    return _build_loot_for_floor(table_loot_tables, table_item_count_by_floor, floor)


def _select_bookshelf_loot_table(floor: int) -> List[Tuple[str, float]]:
    return _select_loot_table_for_floor(bookshelf_loot_tables, floor)


def _build_bookshelf_loot(floor: int) -> List[Entity]:
    return _build_loot_for_floor(
        bookshelf_loot_tables, bookshelf_item_count_by_floor, floor
    )


def _maybe_fill_container_loot(entity: Entity, floor_number: int) -> None:
    """Populate table-like containers with loot when they spawn."""
    loot: List[Entity] = []
    if isinstance(entity, TableContainer):
        loot = _build_table_loot(floor_number)
    elif isinstance(entity, BookShelfContainer):
        loot = _build_bookshelf_loot(floor_number)
    else:
        return
    entity_factories.fill_container_with_items(entity, loot)
    record_loot_items(loot, floor_number, procedural=True, source="container_spawn")


def maybe_place_table(
    dungeon: GameMap,
    floor_number: int,
    rooms: Optional[List] = None,
) -> None:
    """Place a lootable table with its own spawn chance."""
    chance = get_floor_value(table_spawn_chances, floor_number, 0.0)
    if chance <= 0 or random.random() > chance:
        return

    def pick_location() -> Optional[Tuple[int, int]]:
        if rooms:
            room = random.choice(rooms)
            return room.random_location()
        for _ in range(20):
            x = random.randint(1, dungeon.width - 2)
            y = random.randint(1, dungeon.height - 2)
            if dungeon.tiles["walkable"][x, y]:
                return (x, y)
        return None

    for _ in range(50):
        coords = pick_location()
        if not coords:
            continue
        x, y = coords
        if not _can_place_entity(dungeon, x, y):
            continue
        loot = _build_table_loot(floor_number)
        table_entity = entity_factories.table.spawn(dungeon, x, y)
        entity_factories.fill_container_with_items(table_entity, loot)
        record_loot_items(loot, floor_number, procedural=True, source="table")
        if settings.DEBUG_MODE:
            if __debug__:
                print(f"DEBUG: Generando... Table en x={x} y={y}")
        return
    if settings.DEBUG_MODE:
        if __debug__:
            print(f"DEBUG: Failed to place table en floor {floor_number}")


def maybe_place_bookshelf(
    dungeon: GameMap,
    floor_number: int,
    rooms: Optional[List] = None,
) -> None:
    """Place a lootable bookshelf with its own spawn chance."""
    chance = get_floor_value(bookshelf_spawn_chances, floor_number, 0.0)
    if chance <= 0 or random.random() > chance:
        return

    def pick_location() -> Optional[Tuple[int, int]]:
        if rooms:
            room = random.choice(rooms)
            return room.random_location()
        for _ in range(20):
            x = random.randint(1, dungeon.width - 2)
            y = random.randint(1, dungeon.height - 2)
            if dungeon.tiles["walkable"][x, y]:
                return (x, y)
        return None

    for _ in range(50):
        coords = pick_location()
        if not coords:
            continue
        x, y = coords
        if not _can_place_entity(dungeon, x, y):
            continue
        loot = _build_bookshelf_loot(floor_number)
        bookshelf_entity = entity_factories.bookshelf.spawn(dungeon, x, y)
        entity_factories.fill_container_with_items(bookshelf_entity, loot)
        record_loot_items(loot, floor_number, procedural=True, source="bookshelf")
        if settings.DEBUG_MODE:
            if __debug__:
                print(f"DEBUG: Generando... Bookshelf en x={x} y={y}")
        return
    if settings.DEBUG_MODE:
        if __debug__:
            print(f"DEBUG: Failed to place bookshelf en floor {floor_number}")


def maybe_place_chest(
    dungeon: GameMap,
    floor_number: int,
    rooms: Optional[List] = None,
) -> None:
    chance = get_floor_value(chest_spawn_chances, floor_number, 0.0)
    if chance <= 0 or random.random() > chance:
        return

    def pick_location() -> Optional[Tuple[int, int]]:
        if rooms:
            room = random.choice(rooms)
            return room.random_location()
        for _ in range(20):
            x = random.randint(1, dungeon.width - 2)
            y = random.randint(1, dungeon.height - 2)
            if dungeon.tiles["walkable"][x, y]:
                return (x, y)
        return None

    for _ in range(50):
        coords = pick_location()
        if not coords:
            continue
        x, y = coords
        if not _can_place_entity(dungeon, x, y):
            continue
        loot = _build_chest_loot(floor_number)
        chest_entity = entity_factories.chest.spawn(dungeon, x, y)
        entity_factories.fill_chest_with_items(chest_entity, loot)
        record_loot_items(loot, floor_number, procedural=True, source="chest")
        if settings.DEBUG_MODE:
            if __debug__:
                print(f"DEBUG: Generando... Chest en x={x} y={y}")
        return
    if settings.DEBUG_MODE:
        if __debug__:
            print(f"DEBUG: Failed to place chest en floor {floor_number}")


def tunnel_between(
    start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end

    if random.random() < 0.5:  # 50% chance.
        # Move horizontally, then vertically.
        corner_x, corner_y = x2, y1
    else:
        # Move vertically, then horizontally.
        corner_x, corner_y = x1, y2

    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        yield x, y

    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x, y


def carve_tunnel_path(dungeon: GameMap, start: Tuple[int, int], end: Tuple[int, int]) -> None:
    for index, (x, y) in enumerate(tunnel_between(start, end)):
        if index == 0:
            continue
        dungeon.tiles[x, y] = tile_types.floor


def carve_room(dungeon: GameMap, room: RectangularRoom) -> None:
    """Carve the interior of the room into the dungeon tile map."""
    if room.shape == "rectangle":
        dungeon.tiles[room.inner] = tile_types.floor
        return

    for x, y in room.iter_floor_tiles():
        dungeon.tiles[x, y] = tile_types.floor


def clamp_room_position(room: RectangularRoom, x: int, y: int) -> Tuple[int, int]:
    min_x = room.x1 + 1
    max_x = room.x2 - 1
    min_y = room.y1 + 1
    max_y = room.y2 - 1
    return (
        max(min_x, min(max_x, x)),
        max(min_y, min(max_y, y)),
    )


def place_column_if_possible(dungeon: GameMap, x: int, y: int) -> bool:
    if not dungeon.in_bounds(x, y):
        return False
    if not dungeon.tiles["walkable"][x, y]:
        return False
    if dungeon.upstairs_location and (x, y) == dungeon.upstairs_location:
        return False
    if dungeon.downstairs_location and (x, y) == dungeon.downstairs_location:
        return False
    if dungeon.downstairs_location and (x, y) == dungeon.downstairs_location:
        return False
    if dungeon.get_blocking_entity_at_location(x, y):
        return False
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if dungeon.in_bounds(nx, ny) and not dungeon.tiles["walkable"][nx, ny]:
                return False

    dungeon.tiles[x, y] = tile_types.wall
    return True


def rectangle_column_positions(room: RectangularRoom) -> List[Tuple[int, int]]:
    cx, cy = room.center
    width = room.x2 - room.x1
    height = room.y2 - room.y1
    dx = max(2, width // 4)
    dy = max(2, height // 4)
    raw = [
        (cx - dx, cy - dy),
        (cx - dx, cy + dy),
        (cx + dx, cy - dy),
        (cx + dx, cy + dy),
    ]
    return [clamp_room_position(room, x, y) for x, y in raw]


def circle_column_positions(room: RectangularRoom) -> List[Tuple[int, int]]:
    cx, cy = room.center
    offset = max(1, room.radius - 1)
    raw = [
        (cx + offset, cy),
        (cx - offset, cy),
        (cx, cy + offset),
        (cx, cy - offset),
    ]
    return [clamp_room_position(room, x, y) for x, y in raw]


def ellipse_column_positions(room: RectangularRoom) -> List[Tuple[int, int]]:
    cx, cy = room.center
    axis_x, axis_y = room.ellipse_axes if room.ellipse_axes else (3.0, 2.0)
    dx = max(1, int(axis_x) - 1)
    dy = max(1, int(axis_y) - 2)
    raw = [
        (cx + dx, cy - dy),
        (cx + dx, cy + dy),
        (cx - dx, cy - dy),
        (cx - dx, cy + dy),
    ]
    return [clamp_room_position(room, x, y) for x, y in raw]


def cross_column_positions(room: RectangularRoom) -> List[Tuple[int, int]]:
    cx, cy = room.center
    dx = max(1, room.cross_half_width_x)
    dy = max(1, room.cross_half_width_y)
    raw = [
        (cx, cy - dy),
        (cx, cy + dy),
        (cx - dx, cy),
        (cx + dx, cy),
        (cx, cy),
    ]
    return [clamp_room_position(room, x, y) for x, y in raw]


def add_room_decorations(dungeon: GameMap, room: RectangularRoom) -> None:
    shape = getattr(room, "shape", None)
    if shape not in ROOM_DECORATION_CHANCE:
        return
    if random.random() > ROOM_DECORATION_CHANCE[shape]:
        return

    if shape == "rectangle":
        positions = rectangle_column_positions(room)
    elif shape == "circle":
        positions = circle_column_positions(room)
    elif shape == "ellipse":
        positions = ellipse_column_positions(room)
    elif shape == "cross":
        positions = cross_column_positions(room)
    else:
        return

    placed_any = False
    seen = set()
    for x, y in positions:
        if (x, y) in seen:
            continue
        seen.add((x, y))
        if place_column_if_possible(dungeon, x, y):
            placed_any = True

    if placed_any:
        return

    # Fallback: attempt to place up to two columns at random floor tiles.
    floor_tiles = list(room.iter_floor_tiles())
    random.shuffle(floor_tiles)
    attempts = 0
    for x, y in floor_tiles:
        if place_column_if_possible(dungeon, x, y):
            placed_any = True
        attempts += 1
        if attempts >= 2 or placed_any:
            break


def carve_fixed_room(dungeon: GameMap, room: RectangularRoom, template: Tuple[str, ...]) -> bool:
    room_height = len(template)
    room_width = max((len(row) for row in template), default=0)

    if room_width > (room.x2 - room.x1) or room_height > (room.y2 - room.y1):
        return False

    offset_x = room.x1
    offset_y = room.y1
    for y, row in enumerate(template):
        for x, ch in enumerate(row):
            tx = offset_x + x
            ty = offset_y + y
            if ch == "#":
                dungeon.tiles[tx, ty] = tile_types.wall
            elif ch == ".":
                dungeon.tiles[tx, ty] = tile_types.floor
            elif ch == "B":
                dungeon.tiles[tx, ty] = tile_types.breakable_wall
                entity_factories.breakable_wall.spawn(dungeon, tx, ty)
            elif ch == "+":
                dungeon.tiles[tx, ty] = tile_types.closed_door
                spawn_door_entity(dungeon, tx, ty)
    cx, cy = room.center
    dungeon.tiles[cx, cy] = tile_types.floor
    return True


def ensure_path_between(dungeon: GameMap, start: Tuple[int, int], goal: Tuple[int, int]) -> bool:
    from collections import deque

    width, height = dungeon.width, dungeon.height
    visited = {start}
    queue = deque([start])

    def is_traversable(x: int, y: int) -> bool:
        if not dungeon.in_bounds(x, y):
            return False
        if dungeon.tiles["walkable"][x, y]:
            return True
        tile = dungeon.tiles[x, y]
        # Consider closed doors passable since the player can open them.
        if np.array_equal(tile, tile_types.closed_door):
            return True
        # Breakable walls can be destroyed, so they count as a viable path blocker.
        if np.array_equal(tile, tile_types.breakable_wall):
            return True
        actor = dungeon.get_blocking_entity_at_location(x, y)
        if actor:
            name = getattr(actor, "name", "").lower()
            if "door" in name or "breakable" in name:
                return True
        return False

    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            return True
        for dx, dy in CARDINAL_DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited and is_traversable(nx, ny):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return False


# BUG: Esto no estaba funcionando bien. De todos modos era una mala idea. Esta función
# no es más que un bugfix provisional.
def guarantee_downstairs_access(dungeon: GameMap, start: Tuple[int, int], goal: Tuple[int, int]) -> bool:
    """Carve a minimal breakable corridor when the stairs are unreachable."""
    walls_to_convert = find_walls_to_convert(dungeon, start, goal)
    if not walls_to_convert:
        return False

    for x, y in walls_to_convert:
        convert_tile_to_breakable(dungeon, x, y)

    ensure_breakable_tiles(dungeon)
    if dungeon.engine.debug:
        print(f"[DEBUG] Forced breakable tunnel to downstairs via: {walls_to_convert}")
    return True


def find_walls_to_convert(
    dungeon: GameMap, start: Tuple[int, int], goal: Tuple[int, int]
) -> Optional[List[Tuple[int, int]]]:
    """Use Dijkstra to find the minimal set of walls to convert into breakables."""
    width, height = dungeon.width, dungeon.height
    heap: List[Tuple[int, Tuple[int, int]]] = []
    heapq.heappush(heap, (0, start))
    parents: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    costs: Dict[Tuple[int, int], int] = {start: 0}

    while heap:
        cost, (x, y) = heapq.heappop(heap)
        if (x, y) == goal:
            break
        for dx, dy in CARDINAL_DIRECTIONS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            traversable = is_tile_traversable_for_path(dungeon, nx, ny)
            new_cost = cost if traversable else cost + 1
            if new_cost < costs.get((nx, ny), 1_000_000):
                costs[(nx, ny)] = new_cost
                parents[(nx, ny)] = (x, y)
                heapq.heappush(heap, (new_cost, (nx, ny)))
    else:
        return None

    if goal not in parents:
        return None

    path: List[Tuple[int, int]] = []
    cursor: Optional[Tuple[int, int]] = goal
    while cursor and cursor != start:
        path.append(cursor)
        cursor = parents.get(cursor)
    path.reverse()

    walls: List[Tuple[int, int]] = []
    for coord in path:
        x, y = coord
        if not is_tile_traversable_for_path(dungeon, x, y):
            walls.append(coord)

    return walls


def is_tile_traversable_for_path(dungeon: GameMap, x: int, y: int) -> bool:
    if not dungeon.in_bounds(x, y):
        return False
    if dungeon.tiles["walkable"][x, y]:
        return True
    tile = dungeon.tiles[x, y]
    if np.array_equal(tile, tile_types.closed_door):
        return True
    if np.array_equal(tile, tile_types.breakable_wall):
        return True
    return False


def log_breakable_tile_mismatches(dungeon: GameMap, source: str) -> None:
    """Debug helper to spot walls whose tile got sobrescribed como suelo."""
    issues: List[Tuple[int, int, bool, bool]] = []
    for entity in dungeon.entities:
        if getattr(entity, "name", "").lower() != "suspicious wall":
            continue
        x, y = entity.x, entity.y
        walkable = bool(dungeon.tiles["walkable"][x, y])
        transparent = bool(dungeon.tiles["transparent"][x, y])
        if walkable or transparent:
            issues.append((x, y, walkable, transparent))

    if issues:
        print(f"[DEBUG] Breakable wall tile mismatches after {source}: {issues}")


def ensure_breakable_tiles(dungeon: GameMap) -> None:
    """Force every Suspicious wall entity to have an opaque, non-walkable tile."""
    corrected: List[Tuple[int, int]] = []
    for entity in dungeon.entities:
        if getattr(entity, "name", "").lower() != "suspicious wall":
            continue
        x, y = entity.x, entity.y
        tile = dungeon.tiles[x, y]
        if (
            dungeon.tiles["walkable"][x, y]
            or dungeon.tiles["transparent"][x, y]
            or not np.array_equal(tile, tile_types.breakable_wall)
        ):
            dungeon.tiles[x, y] = tile_types.breakable_wall
            corrected.append((x, y))
            ensure_breakable_entity(dungeon, x, y)

    if corrected and getattr(dungeon.engine, "debug", False):
        print(f"[DEBUG] Restored breakable wall tiles at: {corrected}")


def convert_tile_to_breakable(dungeon: GameMap, x: int, y: int) -> None:
    dungeon.tiles[x, y] = tile_types.breakable_wall
    ensure_breakable_entity(dungeon, x, y)


def ensure_breakable_entity(dungeon: GameMap, x: int, y: int) -> None:
    existing = [
        entity
        for entity in dungeon.entities
        if getattr(entity, "name", "").lower() == "suspicious wall"
        and entity.x == x
        and entity.y == y
    ]
    if not existing:
        entity_factories.breakable_wall.spawn(dungeon, x, y)


def spawn_door_entity(
    dungeon: GameMap,
    x: int,
    y: int,
    open_state: bool = False,
    lock_color: Optional[str] = None,
    room_center: Optional[Tuple[int, int]] = None,
) -> None:
    for entity in dungeon.entities:
        if getattr(entity, "name", "").lower() == "door" and entity.x == x and entity.y == y:
            fighter = getattr(entity, "fighter", None)
            if fighter:
                if lock_color is not None and hasattr(fighter, "lock_color"):
                    fighter.lock_color = lock_color
                if hasattr(fighter, "set_open"):
                    fighter.set_open(open_state)
            if room_center is not None:
                setattr(entity, "room_center", room_center)
            return
    door_entity = entity_factories.door.spawn(dungeon, x, y)
    fighter = getattr(door_entity, "fighter", None)
    if fighter:
        if lock_color is not None and hasattr(fighter, "lock_color"):
            fighter.lock_color = lock_color
        if hasattr(fighter, "set_open"):
            fighter.set_open(open_state)
    if room_center is not None:
        setattr(door_entity, "room_center", room_center)



def get_fixed_room_choice(current_floor: int) -> Optional[Tuple[str, Tuple[str, ...]]]:
    candidates: List[Tuple[str, Tuple[str, ...]]] = []
    for name, rules in FIXED_ROOM_CHANCES.items():
        chance = 0.0
        for min_floor, value in rules:
            if current_floor >= min_floor:
                chance = value
        if chance <= 0:
            continue
        if random.random() < chance:
            template = getattr(fixed_rooms, name, None)
            if template:
                candidates.append((name, template))

    if not candidates:
        return None

    return random.choice(candidates)


def place_entities_fixdungeon(room: RectangularRoom, dungeon: GameMap, floor_number: int, forbidden_cells) -> None:
    
    number_of_monsters = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
    )
    number_of_items = random.randint(
        0, get_max_value_for_floor(max_items_by_floor, floor_number)
    )
    number_of_debris = random.randint(
        0, get_max_value_for_floor(max_debris_by_floor, floor_number)
    )

    monsters = _select_spawn_entries(
        enemy_spawn_rules, number_of_monsters, floor_number, "monsters"
    )
    items = _select_spawn_entries(
        item_spawn_rules, number_of_items, floor_number, "items"
    )
    debris: List[Entity] = get_entities_at_random(
        debris_chances, number_of_debris, floor_number
    )

    allowed_cells_array = []
    for x in range(room.x1 + 1, room.x2 - 1):
        for y in range(room.y1 + 1, room.y2 - 1):
            if (x, y) in forbidden_cells:
                continue
            if not dungeon.tiles["walkable"][x, y]:
                continue
            if dungeon.downstairs_location and (x, y) == dungeon.downstairs_location:
                continue
            if dungeon.upstairs_location and (x, y) == dungeon.upstairs_location:
                continue
            allowed_cells_array.append((x, y))

    if not allowed_cells_array:
        if __debug__:
            print("DEBUG: No hay celdas disponibles en la sala fija.")
        return

    def location_provider():
        return random.choice(allowed_cells_array)

    context = f"fixed room at {room.center}"

    for entry in monsters:
        _spawn_entity_template(
            entry["entity"],
            location_provider,
            dungeon,
            floor_number,
            entry["display_name"],
            context,
            "monsters",
            entry["name"],
        )

    for entry in items:
        _spawn_entity_template(
            entry["entity"],
            location_provider,
            dungeon,
            floor_number,
            entry["display_name"],
            context,
            "items",
            entry["name"],
        )

    for entity in debris:
        _spawn_entity_template(
            entity,
            location_provider,
            dungeon,
            floor_number,
            entity.name,
            context,
        )


def report_generation_stats(category: Optional[str] = None) -> str:
    """Devuelve un resumen legible de cuántos monstruos/ítems se han generado por nivel y en total."""
    return generation_tracker.format_report(category)


def reset_generation_stats() -> None:
    """Reinicia los contadores de generación (por ejemplo, al comenzar una partida nueva)."""
    generation_tracker.reset()


def _resolve_upstairs_location(dungeon: GameMap, target: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    if not target:
        return None
    from collections import deque

    queue = deque([target])
    visited = {target}

    while queue:
        x, y = queue.popleft()
        if dungeon.in_bounds(x, y) and dungeon.tiles["walkable"][x, y]:
            dungeon.tiles[x, y] = tile_types.up_stairs
            return (x, y)
        for dx, dy in CARDINAL_DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (nx, ny) in visited:
                continue
            visited.add((nx, ny))
            queue.append((nx, ny))
    return None
