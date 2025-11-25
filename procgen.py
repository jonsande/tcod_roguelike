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
import caverns
import settings

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
        self._per_floor: Dict[str, Dict[int, Counter]] = {
            cat: defaultdict(Counter) for cat in self._categories
        }
        self._labels: Dict[str, Dict[str, str]] = {cat: {} for cat in self._categories}

    def register_label(self, category: str, key: str, label: str) -> None:
        if category in self._labels:
            self._labels[category][key] = label

    def record(self, category: Optional[str], floor: int, key: str) -> None:
        if category not in self._totals:
            return
        self._totals[category][key] += 1
        self._per_floor[category][floor][key] += 1

    def get_total(self, category: str, key: str) -> int:
        if category not in self._totals:
            return 0
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
                for key, count in sorted(floor_counter.items()):
                    label = self._labels[cat].get(key, key)
                    lines.append(f"    {label}: {count}")
        return "\n".join(lines)

    def reset(self) -> None:
        for cat in self._categories:
            self._totals[cat].clear()
            self._per_floor[cat].clear()


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
        entity = getattr(entity_factories, name)
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
            current_total = generation_tracker.get_total(category, entry["name"])
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


def _draw_hot_path(
    dungeon: GameMap,
    hot_path: List[Tuple[int, int]],
    *,
    glyph: str = "*",
    dark_color: Tuple[int, int, int] = (180, 50, 50),
    light_color: Tuple[int, int, int] = (255, 90, 90),
) -> None:
    """Pinta sobre el mapa el camino del hot_path para depuración."""
    coords = _collect_hot_path_coords(hot_path)
    if not coords:
        return

    char_code = ord(glyph)
    for x, y in coords:
        if not dungeon.in_bounds(x, y):
            continue
        if not dungeon.tiles["walkable"][x, y]:
            continue
        if dungeon.upstairs_location and (x, y) == dungeon.upstairs_location:
            continue
        if dungeon.downstairs_location and (x, y) == dungeon.downstairs_location:
            continue
        dungeon.tiles["dark"]["ch"][x, y] = char_code
        dungeon.tiles["light"]["ch"][x, y] = char_code
        dungeon.tiles["dark"]["fg"][x, y] = dark_color
        dungeon.tiles["light"]["fg"][x, y] = light_color


def _collect_hot_path_coords(hot_path: List[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    coords: Set[Tuple[int, int]] = set()
    if len(hot_path) < 2:
        return coords
    for a, b in zip(hot_path[:-1], hot_path[1:]):
        coords.update(tunnel_between(a, b))
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
            candidates.add((nx, ny))
    return list(candidates)


def _maybe_place_entry_feature(
    dungeon: GameMap,
    coord: Tuple[int, int],
    options: List[Tuple[str, float]],
    *,
    room_center: Optional[Tuple[int, int]] = None,
    lock_chance: float = 0.0,
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
            lock_color = random.choice(entity_factories.KEY_COLORS)
        dungeon.tiles[x, y] = tile_types.closed_door
        spawn_door_entity(dungeon, x, y, lock_color=lock_color, room_center=room_center)
    elif choice == "breakable":
        convert_tile_to_breakable(dungeon, x, y)


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
    loot = _build_chest_loot(floor_number)

    # Ítems garantizados en el cofre del viejo
    for key in settings.OLD_MAN_CHEST:
        prototype = getattr(entity_factories, key, None)
        loot.append(copy.deepcopy(prototype))

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
        return


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
        entity.spawn(dungeon, x, y)
        if settings.DEBUG_MODE:
            if __debug__:
                print(f"DEBUG: Generando... {debug_name} en x={x} y={y}")
            if category and rule_name:
                generation_tracker.record(category, floor_number, rule_name)
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


def _select_chest_loot_table(floor: int) -> List[Tuple[str, float]]:
    if not chest_loot_tables:
        return []
    selected: List[Tuple[str, float]] = []
    for min_floor in sorted(chest_loot_tables.keys()):
        if min_floor > floor:
            break
        selected = chest_loot_tables[min_floor]
    return selected


def _build_chest_loot(floor: int) -> List[Entity]:
    loot_entries = _select_chest_loot_table(floor)
    if not loot_entries:
        return []
    min_items, max_items = get_floor_value(chest_item_count_by_floor, floor, (0, 0))
    if max_items <= 0 or min_items > max_items:
        return []
    count = random.randint(min_items, max_items)
    keys = [entry[0] for entry in loot_entries]
    weights = [float(entry[1]) for entry in loot_entries]
    chosen_keys = random.choices(keys, weights=weights, k=count)
    loot: List[Entity] = []
    for key in chosen_keys:
        prototype = getattr(entity_factories, key, None)
        if not prototype:
            continue
        loot.append(copy.deepcopy(prototype))
    return loot


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
    room_width = len(template[0]) if room_height else 0

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
    """Devuelve un resumen legible de cuántos monstruos/ítems se han generado por nivel."""
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


def generate_fixed_dungeon(
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    map,
    walls,
    walls_special,
    floor_number: int,
    place_player: bool,
    place_downstairs: bool,
    upstairs_location: Optional[Tuple[int, int]] = None,
) -> GameMap:
    """Generate a fixed-layout dungeon from ASCII templates."""
    entities = [engine.player] if place_player else []
    dungeon = GameMap(engine, map_width, map_height, entities=entities)

    rooms: List[RectangularRoom] = []
    #rooms: List[FixedRoom] = []

    center_of_last_room = (30, 30)

    room_width = 79
    room_height = 35

    x = 0
    y = 0

    new_room = RectangularRoom(x, y, room_width, room_height)
    #new_room = FixedRoom(x, y, room_width, room_height)
    # new_room2 = RectangularRoom2(x, y, room_width, room_height)

    # Dig out this rooms inner area so we start with solid floor.
    dungeon.tiles[new_room.inner] = tile_types.floor

    entry_point: Optional[Tuple[int, int]] = None
    resolved_upstairs = _resolve_upstairs_location(dungeon, upstairs_location)
    if resolved_upstairs:
        dungeon.upstairs_location = resolved_upstairs
        entry_point = resolved_upstairs
    
    walls_array = fixed_maps.generate_array_of(map, "#")
    special_walls_array = fixed_maps.generate_array_of(map, "√")
    special_floor_array = fixed_maps.generate_array_of(map, " ")
    stairs = fixed_maps.generate_array_of(map, ">")
    player_intro = fixed_maps.place_player(map)
    doors = fixed_maps.generate_array_of(map, "+")
    fake_walls_array = fixed_maps.generate_array_of(map, "*")
    
    snake_array = fixed_maps.generate_array_of(map, "s")
    swarm_rat_array = fixed_maps.generate_array_of(map, "r")
    goblin_array = fixed_maps.generate_array_of(map, "g")
    orc_array = fixed_maps.generate_array_of(map, "o")
    sentinel_array = fixed_maps.generate_array_of(map, "&")
    random_monsters_array = fixed_maps.generate_array_of(map, "M")

    forbidden_cells: List[Tuple[int, int]] = []
    forbidden_cells.extend(walls_array)
    forbidden_cells.extend(special_floor_array)
    forbidden_cells.extend(stairs)
    forbidden_cells.append(player_intro)
    forbidden_cells.extend(doors)
    forbidden_cells.extend(fake_walls_array)
    
    # Celdas ocupadas por monstruos generados estáticamente
    forbidden_cells.extend(snake_array)
    forbidden_cells.extend(swarm_rat_array)
    forbidden_cells.extend(goblin_array)
    forbidden_cells.extend(orc_array)
    forbidden_cells.extend(sentinel_array)
    forbidden_cells.extend(random_monsters_array)
    
    #print(f"Forbidden cells: {forbidden_cells}")
    
    # Colocamos entidades genéricas
    place_entities_fixdungeon(
        new_room, 
        dungeon, 
        floor_number, 
        forbidden_cells, 
        )
    
    # Colocamos muros, especiales, escaleras y puertas
    for x, y in walls_array:
        dungeon.tiles[(x, y)] = walls
        
    for x, y in special_walls_array:
        dungeon.tiles[(x, y)] = walls_special
        
    for x, y in special_floor_array:
        dungeon.tiles[(x, y)] = tile_types.floor
        
    dungeon.downstairs_location = None
    for index, (sx, sy) in enumerate(stairs):
        if place_downstairs and dungeon.downstairs_location is None:
            dungeon.tiles[(sx, sy)] = tile_types.down_stairs
            dungeon.downstairs_location = (sx, sy)
        else:
            dungeon.tiles[(sx, sy)] = tile_types.floor

    if place_downstairs and dungeon.downstairs_location is None:
        dungeon.tiles[center_of_last_room] = tile_types.down_stairs
        dungeon.downstairs_location = center_of_last_room
    
    for x, y in doors:
        dungeon.tiles[(x, y)] = tile_types.closed_door
        spawn_door_entity(dungeon, x, y)
        
    for x, y in fake_walls_array:
        dungeon.tiles[(x, y)] = tile_types.breakable_wall
        entity_factories.breakable_wall.spawn(dungeon, x, y)
        
    # Colocamos monstruos estáticos
    
    for x, y in snake_array:
        entity_factories.snake.spawn(dungeon, x, y)
        
    for x, y in swarm_rat_array:
        entity_factories.swarm_rat.spawn(dungeon, x, y)
        
    for x, y in goblin_array:
        entity_factories.goblin.spawn(dungeon, x, y)
        
    for x, y in orc_array:
        entity_factories.orc.spawn(dungeon, x, y)
        
    for x, y in sentinel_array:
        entity_factories.sentinel.spawn(dungeon, x, y)
        
    # Colocamos monstruos aleatorios:
    for x, y in random_monsters_array:
        # Para hacer esto bien habría que pasarle por parámetro
        # un map.name, pero para eso hay que hacer
        # que map sea una clase de objeto
        selected_monster = entity_factories.monster_roulette(choices=[entity_factories.orc, entity_factories.goblin, entity_factories.snake])
        selected_monster.spawn(dungeon, x, y)
    
    if place_player:
        engine.player.place(player_intro[0], player_intro[1], dungeon)
        entry_point = (engine.player.x, engine.player.y)
    elif entry_point is None:
        entry_point = player_intro
        dungeon.upstairs_location = player_intro
        dungeon.tiles[player_intro] = tile_types.up_stairs
    elif not place_player and not dungeon.upstairs_location and entry_point:
        dungeon.upstairs_location = entry_point
        dungeon.tiles[entry_point] = tile_types.up_stairs

    
    

    #import gen_uniques
    #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)

    # Finally, append the new room to the list.
    rooms.append(new_room)
    # rooms.append(new_room2)

    if place_downstairs and dungeon.downstairs_location and entry_point:
        if not ensure_path_between(dungeon, entry_point, dungeon.downstairs_location):
            if not guarantee_downstairs_access(dungeon, entry_point, dungeon.downstairs_location):
                if __debug__:
                    print("WARNING: Fixed dungeon template has no guaranteed path between upstairs and downstairs.")

    maybe_place_chest(dungeon, floor_number, rooms)
    ensure_breakable_tiles(dungeon)
    if engine.debug:
        log_breakable_tile_mismatches(dungeon, "generate_fixed_dungeon")
    dungeon.center_rooms = []
    return dungeon


def populate_cavern(dungeon: GameMap, floor_number: int) -> None:
    for entity in list(dungeon.entities):
        if entity is dungeon.engine.player:
            continue
        dungeon.entities.discard(entity)

    rooms_array: List[Tuple[int, int]] = []
    dungeon.engine.update_center_rooms_array(rooms_array)

    for _ in range(60):
        x = random.randint(1, dungeon.width - 2)
        y = random.randint(1, dungeon.height - 2)
        if dungeon.tiles["walkable"][x, y] and \
            (not dungeon.downstairs_location or (x, y) != dungeon.downstairs_location) and \
            (not dungeon.upstairs_location or (x, y) != dungeon.upstairs_location):
            entity_factories.debris_a.spawn(dungeon, x, y)
    dungeon.spawn_monsters_counter = 0

    min_monsters, max_monsters = get_floor_value(
        cavern_monster_count_by_floor, floor_number, (8, 14)
    )
    min_monsters = max(0, min_monsters)
    max_monsters = max(min_monsters, max_monsters)
    number_of_monsters = random.randint(min_monsters, max_monsters)

    for monster_entry in _select_weighted_spawn_entries(
        cavern_monster_spawn_rules, number_of_monsters, floor_number
    ):
        for _ in range(40):
            x = random.randint(1, dungeon.width - 2)
            y = random.randint(1, dungeon.height - 2)
            if not _can_place_entity(dungeon, x, y):
                continue
            monster_entry["entity"].spawn(dungeon, x, y)
            break

    min_items, max_items = get_floor_value(
        cavern_item_count_by_floor, floor_number, (0, 0)
    )
    min_items = max(0, min_items)
    max_items = max(min_items, max_items)
    number_of_items = random.randint(min_items, max_items) if max_items > 0 else 0

    for item_entry in _select_weighted_spawn_entries(
        cavern_item_spawn_rules, number_of_items, floor_number
    ):
        for _ in range(40):
            x = random.randint(1, dungeon.width - 2)
            y = random.randint(1, dungeon.height - 2)
            if not _can_place_entity(dungeon, x, y):
                continue
            item_entry["entity"].spawn(dungeon, x, y)
            break


def generate_cavern(
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    floor_number: int,
    place_player: bool,
    place_downstairs: bool,
    upstairs_location: Optional[Tuple[int, int]] = None,
    fill_probability: Optional[float] = None,
    birth_limit: Optional[int] = None,
    death_limit: Optional[int] = None,
    smoothing_steps: Optional[int] = None,
) -> GameMap:
    entities = [engine.player] if place_player else []
    dungeon = GameMap(engine, map_width, map_height, entities=entities)
    dungeon.tiles = np.full((map_width, map_height), fill_value=tile_types.wall, order="F")

    fill_probability = fill_probability if fill_probability is not None else settings.CAVERN_FILL_PROBABILITY
    birth_limit = birth_limit if birth_limit is not None else settings.CAVERN_BIRTH_LIMIT
    death_limit = death_limit if death_limit is not None else settings.CAVERN_DEATH_LIMIT
    smoothing_steps = smoothing_steps if smoothing_steps is not None else settings.CAVERN_SMOOTHING_STEPS

    ca_map = caverns.generate_cavern_map(
        map_width,
        map_height,
        steps=smoothing_steps,
        fill_probability=fill_probability,
        birth_limit=birth_limit,
        death_limit=death_limit,
    )
    ca_map, player_start, stairs_location = caverns.connect_cavern_regions(ca_map)

    dungeon.tiles["walkable"] = ca_map
    dungeon.tiles["transparent"] = ca_map

    floor_indices = np.where(ca_map)
    dungeon.tiles["dark"]["ch"][floor_indices] = tile_types.floor["dark"]["ch"]
    dungeon.tiles["dark"]["fg"][floor_indices] = tile_types.floor["dark"]["fg"]
    dungeon.tiles["dark"]["bg"][floor_indices] = tile_types.floor["dark"]["bg"]
    dungeon.tiles["light"]["ch"][floor_indices] = tile_types.floor["light"]["ch"]
    dungeon.tiles["light"]["fg"][floor_indices] = tile_types.floor["light"]["fg"]
    dungeon.tiles["light"]["bg"][floor_indices] = tile_types.floor["light"]["bg"]

    entry_point: Optional[Tuple[int, int]] = upstairs_location
    if upstairs_location:
        dungeon.upstairs_location = upstairs_location
        dungeon.tiles[upstairs_location] = tile_types.up_stairs

    spawn_location = player_start
    if upstairs_location:
        spawn_location = upstairs_location
    elif place_player:
        spawn_location = player_start

    if upstairs_location and spawn_location == upstairs_location:
        dungeon.tiles[spawn_location] = tile_types.up_stairs
    else:
        dungeon.tiles[spawn_location] = tile_types.floor
    if place_player:
        engine.player.place(*spawn_location, dungeon)
        entry_point = (engine.player.x, engine.player.y)
    elif entry_point is None:
        entry_point = spawn_location
        if not place_player:
            dungeon.upstairs_location = spawn_location
            dungeon.tiles[spawn_location] = tile_types.up_stairs
    elif not place_player and not dungeon.upstairs_location:
        dungeon.upstairs_location = entry_point
        dungeon.tiles[entry_point] = tile_types.up_stairs

    if place_downstairs:
        dungeon.tiles[stairs_location] = tile_types.floor
        dungeon.tiles[stairs_location] = tile_types.down_stairs
        dungeon.downstairs_location = stairs_location
    else:
        dungeon.downstairs_location = None

    populate_cavern(dungeon, floor_number)
    maybe_place_chest(dungeon, floor_number)

    if place_downstairs and dungeon.downstairs_location and entry_point:
        if not ensure_path_between(dungeon, entry_point, dungeon.downstairs_location):
            return generate_cavern(
                map_width,
                map_height,
                engine,
                floor_number=floor_number,
                place_player=place_player,
                place_downstairs=place_downstairs,
                upstairs_location=upstairs_location,
                fill_probability=fill_probability,
                birth_limit=birth_limit,
                death_limit=death_limit,
                smoothing_steps=smoothing_steps,
            )

    dungeon.center_rooms = []
    return dungeon


def generate_dungeon_v3(
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    floor_number: int,
    place_player: bool,
    place_downstairs: bool,
    upstairs_location: Optional[Tuple[int, int]] = None,
) -> GameMap:
    """Experimental generator focused en mazmorras con varias salas conectadas por MST + conexiones extra."""
    entities = [engine.player] if place_player else []
    dungeon = GameMap(engine, map_width, map_height, entities=entities)

    rooms: List[RectangularRoom] = []
    padding = max(0, settings.DUNGEON_V3_PADDING)

    target_rooms = random.randint(settings.DUNGEON_V3_MIN_ROOMS, settings.DUNGEON_V3_MAX_ROOMS)
    attempts = 0
    max_attempts = settings.DUNGEON_V3_MAX_PLACEMENT_ATTEMPTS

    while len(rooms) < target_rooms and attempts < max_attempts:
        attempts += 1
        template = None
        if settings.DUNGEON_V3_FIXED_ROOMS_ENABLED:
            fixed_choice = get_fixed_room_choice(floor_number)
            if fixed_choice:
                _, template = fixed_choice

        if template:
            height = len(template)
            width = len(template[0]) if height else 0
        else:
            width = random.randint(settings.DUNGEON_V3_ROOM_MIN_SIZE, settings.DUNGEON_V3_ROOM_MAX_SIZE)
            height = random.randint(settings.DUNGEON_V3_ROOM_MIN_SIZE, settings.DUNGEON_V3_ROOM_MAX_SIZE)

        x = random.randint(1, max(1, dungeon.width - width - 2))
        y = random.randint(1, max(1, dungeon.height - height - 2))
        shape = "rectangle" if template else choose_room_shape(width, height)
        new_room = RectangularRoom(x, y, width, height, shape=shape)
        if not _room_fits_within_bounds(new_room, dungeon.width, dungeon.height):
            continue
        if any(_rooms_intersect_with_padding(new_room, other[0], padding) for other in rooms):
            continue
        rooms.append((new_room, template))

    if not rooms:
        raise RuntimeError("generate_dungeon_v3 failed to place any rooms.")

    # Carve rooms and place entities.
    entry_point: Optional[Tuple[int, int]] = upstairs_location
    for index, (room, template) in enumerate(rooms):
        carve_room(dungeon, room)
        used_fixed_room = False
        if template:
            if carve_fixed_room(dungeon, room, template):
                used_fixed_room = True

        if not used_fixed_room:
            add_room_decorations(dungeon, room)

        if index == 0:
            if place_player:
                engine.player.place(*room.center, dungeon)
                entry_point = (engine.player.x, engine.player.y)
            elif not entry_point:
                entry_point = room.center
            dungeon.upstairs_location = entry_point
            dungeon.tiles[entry_point] = tile_types.up_stairs
        place_entities(room, dungeon, floor_number)
        uniques.place_uniques(floor_number, room.center, dungeon)

    # Conectamos salas con un MST + conexiones extra.
    centers = [room.center for room, _ in rooms]
    edges: List[Tuple[int, int, int]] = []
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dist = _manhattan_distance(centers[i], centers[j])
            edges.append((dist, i, j))
    edges.sort(key=lambda e: e[0])

    ds = _DisjointSet(len(rooms))
    connections: List[Tuple[int, int]] = []
    for dist, i, j in edges:
        if ds.union(i, j):
            connections.append((i, j))
        if len(connections) >= len(rooms) - 1:
            break

    extra_attempts = settings.DUNGEON_V3_EXTRA_CONNECTIONS
    for _ in range(extra_attempts):
        candidates = [edge for edge in edges if edge[1:] not in connections and (edge[2], edge[1]) not in connections]
        if not candidates:
            break
        dist, i, j = random.choice(candidates)
        if random.random() < settings.DUNGEON_V3_EXTRA_CONNECTION_CHANCE:
            connections.append((i, j))

    for i, j in connections:
        carve_tunnel_path(dungeon, centers[i], centers[j])

    # Añadimos puertas/muros rompibles opcionales en puntos de entrada a sala.
    feature_probs = _normalize_feature_probs(
        getattr(settings, "DUNGEON_V3_ENTRY_FEATURE_PROBS", {"none": 1.0})
    )
    room_tile_sets = [set(room.iter_floor_tiles()) for room, _ in rooms]
    lock_chance = max(0.0, min(1.0, getattr(settings, "DUNGEON_V3_LOCKED_DOOR_CHANCE", 0.0)))
    for room_tiles, (room, _) in zip(room_tile_sets, rooms):
        for coord in _collect_room_entry_candidates_v3(dungeon, room_tiles):
            _maybe_place_entry_feature(
                dungeon,
                coord,
                feature_probs,
                room_center=room.center,
                lock_chance=lock_chance,
            )

    # Escaleras
    if place_downstairs:
        target_room = max(
            rooms,
            key=lambda r: _manhattan_distance(r[0].center, entry_point or r[0].center),
        )
        downstairs_location = target_room[0].center
        dungeon.tiles[downstairs_location] = tile_types.down_stairs
        dungeon.downstairs_location = downstairs_location
    else:
        dungeon.downstairs_location = None

    # Hot path: camino más corto entre sala de subida y bajada.
    upstairs_room_idx = None
    downstairs_room_idx = None
    if entry_point:
        for idx, (room, _) in enumerate(rooms):
            if _room_contains_point(room, entry_point):
                upstairs_room_idx = idx
                break
    if dungeon.downstairs_location:
        for idx, (room, _) in enumerate(rooms):
            if _room_contains_point(room, dungeon.downstairs_location):
                downstairs_room_idx = idx
                break
    if upstairs_room_idx is None and rooms:
        upstairs_room_idx = 0
    if downstairs_room_idx is None and rooms:
        downstairs_room_idx = len(rooms) - 1

    hot_path_centers: List[Tuple[int, int]] = []
    if upstairs_room_idx is not None and downstairs_room_idx is not None:
        idx_path = _shortest_room_path(centers, connections, upstairs_room_idx, downstairs_room_idx)
        if idx_path:
            hot_path_centers = [centers[i] for i in idx_path]
    dungeon.hot_path = hot_path_centers
    if getattr(settings, "DEBUG_DRAW_HOT_PATH", False):
        _draw_hot_path(dungeon, hot_path_centers)

    # Accesibilidad
    if place_downstairs and dungeon.downstairs_location and entry_point:
        if not ensure_path_between(dungeon, entry_point, dungeon.downstairs_location):
            if not guarantee_downstairs_access(dungeon, entry_point, dungeon.downstairs_location):
                raise RuntimeError("generate_dungeon_v3 failed to connect upstairs and downstairs.")

    maybe_place_chest(dungeon, floor_number, [room for room, _ in rooms])
    dungeon.center_rooms = [room.center for room, _ in rooms]
    dungeon.engine.update_center_rooms_array(list(dungeon.center_rooms))
    return dungeon


def generate_dungeon_v2(
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    floor_number: int,
    place_player: bool,
    place_downstairs: bool,
    upstairs_location: Optional[Tuple[int, int]] = None,
) -> GameMap:
    """Experimental generator that builds a fully connected graph of rooms."""
    max_attempts = max(1, settings.DUNGEON_V2_MAX_MAP_ATTEMPTS)
    for _ in range(max_attempts):
        entities = [engine.player] if place_player else []
        dungeon = GameMap(engine, map_width, map_height, entities=entities)
        room_tiles_global: Set[Tuple[int, int]] = set()
        corridor_tiles: Set[Tuple[int, int]] = set()

        initial_result = _create_initial_v2_room(
            dungeon,
            floor_number,
            place_player=place_player,
            upstairs_location=upstairs_location,
            room_tiles_global=room_tiles_global,
        )
        if not initial_result:
            continue
        initial_room, entry_point = initial_result
        rooms: List[V2RoomNode] = [initial_room]
        rooms_array: List[Tuple[int, int]] = [initial_room.rect.center]

        pending = deque(
            (initial_room, entry)
            for entry in initial_room.entrances
            if not entry.connected
        )
        success = True

        while pending:
            if len(rooms) >= settings.DUNGEON_V2_MAX_ROOMS:
                success = False
                break
            room_node, entry = pending.popleft()
            if entry.connected:
                continue
            new_room = _expand_room_from_entry(
                dungeon,
                parent_entry=entry,
                floor_number=floor_number,
                room_tiles_global=room_tiles_global,
                corridor_tiles=corridor_tiles,
                rooms=rooms,
            )
            if not new_room:
                success = False
                break
            entry.connected = True
            rooms.append(new_room)
            rooms_array.append(new_room.rect.center)
            for room_entry in new_room.entrances:
                if not room_entry.connected:
                    pending.append((new_room, room_entry))

        if not success or pending:
            continue

        if place_downstairs:
            if not rooms:
                continue
            target_room = max(
                rooms,
                key=lambda node: _manhattan_distance(node.rect.center, entry_point),
            )
            downstairs_location = target_room.rect.center
            dungeon.tiles[downstairs_location] = tile_types.down_stairs
            dungeon.downstairs_location = downstairs_location
        else:
            dungeon.downstairs_location = None

        if entry_point:
            path_start = entry_point
        elif place_player:
            path_start = (engine.player.x, engine.player.y)
        elif dungeon.upstairs_location:
            path_start = dungeon.upstairs_location
        else:
            path_start = rooms[0].rect.center

        if place_downstairs and dungeon.downstairs_location and path_start:
            if not ensure_path_between(dungeon, path_start, dungeon.downstairs_location):
                if not guarantee_downstairs_access(dungeon, path_start, dungeon.downstairs_location):
                    continue

        maybe_place_chest(dungeon, floor_number, [node.rect for node in rooms])
        dungeon.center_rooms = [center for center in rooms_array]
        dungeon.engine.update_center_rooms_array(list(rooms_array))
        return dungeon

    raise RuntimeError("generate_dungeon_v2 failed to build a valid layout.")


def generate_dungeon(
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    floor_number: int,
    place_player: bool,
    place_downstairs: bool,
    upstairs_location: Optional[Tuple[int, int]] = None,
) -> GameMap:
    """Generate a new dungeon map."""
    entities = [engine.player] if place_player else []
    dungeon = GameMap(engine, map_width, map_height, entities=entities)

    rooms: List[RectangularRoom] = []

    center_of_last_room = (0, 0)
    downstairs_candidate: Optional[Tuple[int, int]] = None
    rooms_array = []
    entry_point: Optional[Tuple[int, int]] = upstairs_location

    if upstairs_location:
        dungeon.upstairs_location = upstairs_location
        dungeon.tiles[upstairs_location] = tile_types.up_stairs

    for _ in range(max_rooms):
        template = None
        fixed_choice = get_fixed_room_choice(floor_number)
        if fixed_choice:
            _, template = fixed_choice
            room_height = len(template)
            room_width = len(template[0]) if room_height else 0
        else:
            room_width = random.randint(room_min_size, room_max_size)
            room_height = random.randint(room_min_size, room_max_size)

        x = random.randint(0, dungeon.width - room_width - 1)
        y = random.randint(0, dungeon.height - room_height - 1)

        # "RectangularRoom" class makes rectangles easier to work with
        shape = "rectangle" if template else choose_room_shape(room_width, room_height)

        new_room = RectangularRoom(x, y, room_width, room_height, shape=shape)

        # new_room2 = RectangularRoom2(x, y, room_width, room_height)

        # Run through the other rooms and see if they intersect with this one.
        if any(new_room.intersects(other_room) for other_room in rooms):
            continue  # This room intersects, so go to the next attempt.
        # If there are no intersections then the room is valid.

        # Dig out this rooms inner area.
        carve_room(dungeon, new_room)

        used_fixed_room = False
        if template:
            if carve_fixed_room(dungeon, new_room, template):
                used_fixed_room = True

        if not used_fixed_room:
            add_room_decorations(dungeon, new_room)
        

        if len(rooms) == 0:
            if place_player:
                engine.player.place(*new_room.center, dungeon)
                entry_point = (engine.player.x, engine.player.y)
            elif not entry_point:
                entry_point = upstairs_location or new_room.center
            if not place_player and not dungeon.upstairs_location and entry_point:
                dungeon.upstairs_location = entry_point
                dungeon.tiles[entry_point] = tile_types.up_stairs
            center_of_last_room = new_room.center
            downstairs_candidate = center_of_last_room
            rooms_array.append(center_of_last_room)
        else:  # All rooms after the first.
            carve_tunnel_path(dungeon, rooms[-1].center, new_room.center)

            center_of_last_room = new_room.center
            downstairs_candidate = center_of_last_room
            rooms_array.append(center_of_last_room)
            engine.update_center_rooms_array(rooms_array)
            if settings.DEBUG_MODE:
                if engine.debug == True:
                    print(f"DEBUG: CENTER OF ROOMS ARRAY: {rooms_array}")


        if rooms and DUNGEON_EXTRA_CONNECTION_CHANCE > 0:
            for _ in range(DUNGEON_EXTRA_CONNECTION_ATTEMPTS):
                if random.random() < DUNGEON_EXTRA_CONNECTION_CHANCE:
                    target_room = random.choice(rooms)
                    carve_tunnel_path(dungeon, target_room.center, new_room.center)

        # Colocamos entidades genéricas
        if settings.DEBUG_MODE:
            from color import bcolors
            print(f"{bcolors.WARNING}====== DEBUG: Placing entities in room at...\nDungeon: {dungeon}\nFloor number: {floor_number}\nRoom center: {new_room.center}\nFixed: {used_fixed_room}{bcolors.ENDC}")
        
        place_entities(new_room, dungeon, floor_number)

        #import gen_uniques
        #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)
        
        # Colocamos entidades especiales
        # Esto seguramente sería mejor hacerlo con place() de entity.py
        uniques.place_uniques(floor_number, center_of_last_room, dungeon)

        # Finally, append the new room to the list.
        rooms.append(new_room)
        # rooms.append(new_room2)

    if place_downstairs:
        if not downstairs_candidate:
            downstairs_candidate = entry_point or center_of_last_room
        if downstairs_candidate:
            dungeon.tiles[downstairs_candidate] = tile_types.floor
            dungeon.tiles[downstairs_candidate] = tile_types.down_stairs
            dungeon.downstairs_location = downstairs_candidate
        else:
            dungeon.downstairs_location = None
    else:
        dungeon.downstairs_location = None

    if not place_player and not dungeon.upstairs_location:
        fallback_upstairs = entry_point or center_of_last_room
        if fallback_upstairs:
            dungeon.upstairs_location = fallback_upstairs
            dungeon.tiles[fallback_upstairs] = tile_types.up_stairs

    if entry_point:
        path_start = entry_point
    elif place_player:
        path_start = (engine.player.x, engine.player.y)
    elif upstairs_location:
        path_start = upstairs_location
    else:
        path_start = center_of_last_room

    if place_downstairs and dungeon.downstairs_location and path_start:
        if not ensure_path_between(
            dungeon,
            path_start,
            dungeon.downstairs_location,
        ):
            if not guarantee_downstairs_access(dungeon, path_start, dungeon.downstairs_location):
                return generate_dungeon(
                    max_rooms,
                    room_min_size,
                    room_max_size,
                    map_width,
                    map_height,
                    engine,
                    floor_number=floor_number,
                    place_player=place_player,
                    place_downstairs=place_downstairs,
                    upstairs_location=upstairs_location,
                )

    door_candidates = collect_door_candidates(dungeon)

    dungeon = place_doors(dungeon, door_candidates)
    ensure_breakable_tiles(dungeon)
    if engine.debug:
        log_breakable_tile_mismatches(dungeon, "generate_dungeon")
    maybe_place_chest(dungeon, floor_number, rooms)
    dungeon.center_rooms = list(rooms_array)
    return dungeon


def place_doors(dungeon: GameMap, door_options: List[Tuple[int, int]]):

    if not door_options:
        return dungeon

    pool = door_options.copy()
    random.shuffle(pool)

    doors_to_place = min(max_doors, len(pool))
    selected_doors = pool[:doors_to_place]

    for x, y in selected_doors:
        dungeon.tiles[x, y] = tile_types.closed_door
        spawn_door_entity(dungeon, x, y)

    remaining = pool[doors_to_place:]
    breakable_to_place = min(max_breakable_walls, len(remaining))

    for x, y in remaining[:breakable_to_place]:
        dungeon.tiles[x, y] = tile_types.breakable_wall
        entity_factories.breakable_wall.spawn(dungeon, x, y)

    return dungeon


    return dungeon


def collect_door_candidates(dungeon: GameMap) -> List[Tuple[int, int]]:
    candidates: List[Tuple[int, int]] = []

    for x in range(1, dungeon.width - 1):
        for y in range(1, dungeon.height - 1):
            if not dungeon.tiles["walkable"][x, y]:
                continue

            if dungeon.downstairs_location and (x, y) == dungeon.downstairs_location:
                continue
            if dungeon.upstairs_location and (x, y) == dungeon.upstairs_location:
                continue

            walls = {}
            wall_neighbors = 0
            walkable_neighbors = 0

            for name, (dx, dy) in zip(
                ("north", "south", "east", "west"),
                [(0, -1), (0, 1), (1, 0), (-1, 0)],
            ):
                nx, ny = x + dx, y + dy
                is_wall = (
                    not dungeon.in_bounds(nx, ny)
                    or not dungeon.tiles["walkable"][nx, ny]
                )
                walls[name] = is_wall
                if is_wall:
                    wall_neighbors += 1
                else:
                    walkable_neighbors += 1

            if wall_neighbors != 2 or walkable_neighbors < 2:
                continue

            if not (
                (walls["north"] and walls["south"])
                or (walls["east"] and walls["west"])
            ):
                continue

            candidates.append((x, y))

    return candidates


def generate_town(
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    floor_number: int,
    place_player: bool,
    place_downstairs: bool,
    upstairs_location: Optional[Tuple[int, int]] = None,
    **_,
) -> GameMap:
    """Generate a town-style starting area."""
    entities = [engine.player] if place_player else []
    dungeon = GameMapTown(engine, map_width, map_height, entities=entities)

    entry_point: Optional[Tuple[int, int]] = upstairs_location
    if upstairs_location:
        dungeon.upstairs_location = upstairs_location
        dungeon.tiles[upstairs_location] = tile_types.up_stairs

    #rooms: List[RectangularRoom] = []
    rooms: List[TownRoom] = []

    center_of_last_room = (30, 30)

    room_width = 80
    room_height = 36

    #x = random.randint(0, dungeon.width - room_width - 1)
    #y = random.randint(0, dungeon.height - room_height - 1)
    x = 0
    y = 0

    # "RectangularRoom" class makes rectangles easier to work with
    #new_room = RectangularRoom(x, y, room_width, room_height)
    new_room = TownRoom(x, y, room_width, room_height)
    # new_room2 = RectangularRoom2(x, y, room_width, room_height)

    # Dig out this rooms inner area.
    dungeon.tiles[new_room.inner] = tile_types.town_floor
    
    #if random.random() > 0.4:
    #    dungeon.tiles[new_room.inner] = tile_types.floor
    #else:
    #    if random.random() > 0.8:
    #        dungeon.tiles[new_room.inner] = tile_types.floor3
    #    else:
    #        dungeon.tiles[new_room.inner] = tile_types.floor2

    if place_player:
        engine.player.place(*new_room.center, dungeon)
        entry_point = (engine.player.x, engine.player.y)
    elif entry_point is None:
        entry_point = new_room.center

    downstairs = (35, 17)

    _place_town_old_man_with_campfire(
        dungeon, stairs_location=downstairs, floor_number=floor_number
    )

    # Colocamos entidades genéricas
    place_entities(new_room, dungeon, floor_number)

    # Colocamos escaleras,
    if place_downstairs:
        dungeon.tiles[downstairs] = tile_types.floor
        dungeon.tiles[downstairs] = tile_types.down_stairs
        dungeon.downstairs_location = downstairs
    else:
        dungeon.downstairs_location = None

    #import gen_uniques
    #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)

    # Finally, append the new room to the list.
    rooms.append(new_room)
    # rooms.append(new_room2)

    maybe_place_chest(dungeon, floor_number, rooms)
    if place_downstairs and dungeon.downstairs_location and entry_point:
        if not ensure_path_between(dungeon, entry_point, dungeon.downstairs_location):
            raise RuntimeError("Town generation failed to connect starting area with stairs.")

    dungeon.center_rooms = []
    return dungeon
