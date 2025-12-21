from __future__ import annotations

from typing import List, Optional, Set, Tuple, TYPE_CHECKING

import random

import entity_factories
import settings
import tile_types
import uniques
from game_map import GameMap
from procgen import (
    RectangularRoom,
    _DisjointSet,
    _collect_room_entry_candidates_v3,
    _manhattan_distance,
    _maybe_place_entry_feature,
    _normalize_feature_probs,
    _room_contains_point,
    _room_fits_within_bounds,
    _rooms_intersect_with_padding,
    _shortest_room_path,
    apply_unique_room_features,
    is_unique_room_used,
    mark_unique_room_used,
    build_step_by_step_hot_path,
    add_room_decorations,
    carve_fixed_room,
    carve_room,
    carve_tunnel_path,
    choose_room_shape,
    ensure_path_between,
    get_fixed_room_choice,
    get_unique_room_choice,
    _remove_invalid_fixed_room_doors,
    guarantee_downstairs_access,
    maybe_place_chest,
    maybe_place_table,
    maybe_place_bookshelf,
    place_entities,
    tunnel_between,
)

if TYPE_CHECKING:
    from engine import Engine


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

    rooms: List[Tuple[RectangularRoom, Optional[Tuple[str, ...]], Optional[str], bool]] = []
    padding = max(0, settings.DUNGEON_V3_PADDING)
    fixed_room_allowed_doors: Set[Tuple[int, int]] = set()

    target_rooms = random.randint(settings.DUNGEON_V3_MIN_ROOMS, settings.DUNGEON_V3_MAX_ROOMS)
    attempts = 0
    max_attempts = settings.DUNGEON_V3_MAX_PLACEMENT_ATTEMPTS

    pending_unique_choice = None
    if settings.DUNGEON_V3_FIXED_ROOMS_ENABLED:
        pending_unique_choice = get_unique_room_choice(floor_number)
    while len(rooms) < target_rooms and attempts < max_attempts:
        attempts += 1
        template = None
        fixed_choice = None
        fixed_name = None
        is_unique = False
        if settings.DUNGEON_V3_FIXED_ROOMS_ENABLED:
            if pending_unique_choice:
                fixed_name, template, is_unique = pending_unique_choice
            else:
                fixed_choice = get_fixed_room_choice(floor_number)
                if fixed_choice:
                    fixed_name, template, is_unique = fixed_choice

        if template:
            height = len(template)
            width = max((len(row) for row in template), default=0)
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
        if is_unique and fixed_name:
            pending_unique_choice = None
        rooms.append((new_room, template, fixed_name, is_unique))

    if not rooms:
        raise RuntimeError("generate_dungeon_v3 failed to place any rooms.")

    entry_point: Optional[Tuple[int, int]] = upstairs_location
    dug_tiles: Set[Tuple[int, int]] = set()
    start_idx = 0
    if rooms and rooms[0][3]:
        for idx, (_, _, _, is_unique) in enumerate(rooms):
            if not is_unique:
                start_idx = idx
                break
    for index, (room, template, fixed_name, is_unique) in enumerate(rooms):
        carve_room(dungeon, room)
        dug_tiles.update(room.iter_floor_tiles())
        used_fixed_room = False
        if template:
            if is_unique and fixed_name and is_unique_room_used(fixed_name):
                if settings.DEBUG_MODE:
                    print(
                        f"DEBUG: Unique room {fixed_name} skipped (already used) on floor {floor_number}."
                    )
                fixed_name = None
                is_unique = False
                template = None
            if template and carve_fixed_room(dungeon, room, template, room_name=fixed_name):
                used_fixed_room = True
                fixed_room_allowed_doors.update(getattr(room, "allowed_door_coords", set()))
                if is_unique and fixed_name:
                    entry_points = getattr(room, "fixed_room_markers", {}).get("E", [])
                    if entry_points:
                        room.fixed_room_entry_points = list(entry_points)
                    apply_unique_room_features(dungeon, room, fixed_name)
                    mark_unique_room_used(fixed_name)
                    if settings.DEBUG_MODE:
                        print(
                            f"DEBUG: Unique room {fixed_name} placed at {room.center} on floor {floor_number}."
                        )
            elif is_unique and fixed_name and settings.DEBUG_MODE:
                print(
                    f"DEBUG: Unique room {fixed_name} not placed (template too big) on floor {floor_number}."
                )

        if not used_fixed_room:
            add_room_decorations(dungeon, room)

        if index == start_idx:
            if place_player:
                engine.player.place(*room.center, dungeon)
                entry_point = (engine.player.x, engine.player.y)
            elif not entry_point:
                entry_point = room.center
            dungeon.upstairs_location = entry_point
            dungeon.tiles[entry_point] = tile_types.up_stairs
        place_entities(room, dungeon, floor_number)
        uniques.place_uniques(floor_number, room.center, dungeon)

    centers = [room.center for room, _, _, _ in rooms]
    connection_points: List[Tuple[int, int]] = []
    forbidden_tunnel_tiles: Set[Tuple[int, int]] = set()
    for room, _, _, _ in rooms:
        entry_points = getattr(room, "fixed_room_entry_points", None)
        if entry_points:
            connection_points.append(random.choice(entry_points))
            fixed_tiles = set(getattr(room, "fixed_room_tiles", set()))
            allowed_entries = set(entry_points)
            forbidden_tunnel_tiles.update(fixed_tiles - allowed_entries)
        else:
            connection_points.append(room.center)
    edges: List[Tuple[int, int, int]] = []
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dist = _manhattan_distance(connection_points[i], connection_points[j])
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
        path = carve_tunnel_path(
            dungeon,
            connection_points[i],
            connection_points[j],
            forbidden=forbidden_tunnel_tiles if forbidden_tunnel_tiles else None,
        )
        for coord in path:
            dug_tiles.add(coord)

    _remove_invalid_fixed_room_doors(dungeon, fixed_room_allowed_doors)
    feature_probs = _normalize_feature_probs(
        getattr(settings, "DUNGEON_V3_ENTRY_FEATURE_PROBS", {"none": 1.0})
    )
    room_tile_sets = [set(room.iter_floor_tiles()) for room, _, _, _ in rooms]
    base_lock_chance = max(0.0, min(1.0, getattr(settings, "DUNGEON_V3_LOCKED_DOOR_CHANCE", 0.0)))
    lock_min_floor = getattr(settings, "DUNGEON_V3_LOCKED_DOOR_MIN_FLOOR", {})
    allowed_lock_colors = [
        color for color in entity_factories.KEY_COLORS if floor_number >= lock_min_floor.get(color, 1)
    ]
    lock_chance = base_lock_chance if allowed_lock_colors else 0.0
    locked_colors_in_floor: Set[str] = set()
    for room_tiles, (room, _, _, _) in zip(room_tile_sets, rooms):
        if getattr(room, "is_fixed_room", False):
            continue
        for coord in _collect_room_entry_candidates_v3(dungeon, room_tiles, dug_tiles):
            _maybe_place_entry_feature(
                dungeon,
                coord,
                feature_probs,
                room_center=room.center,
                lock_chance=lock_chance,
                dug_tiles=dug_tiles,
                allowed_lock_colors=allowed_lock_colors,
                locked_colors_registry=locked_colors_in_floor,
            )

    dungeon.room_tiles_map = {
        room.center: list(room_tiles)
        for room_tiles, (room, _, _, _) in zip(room_tile_sets, rooms)
    }

    if place_downstairs:
        candidate_rooms = [room for room in rooms if not room[3]]
        if not candidate_rooms:
            candidate_rooms = rooms
        target_room = max(
            candidate_rooms,
            key=lambda r: _manhattan_distance(r[0].center, entry_point or r[0].center),
        )
        downstairs_location = target_room[0].center
        dungeon.tiles[downstairs_location] = tile_types.down_stairs
        dungeon.downstairs_location = downstairs_location
    else:
        dungeon.downstairs_location = None

    upstairs_room_idx = None
    downstairs_room_idx = None
    if entry_point:
        for idx, (room, _, _, _) in enumerate(rooms):
            if _room_contains_point(room, entry_point):
                upstairs_room_idx = idx
                break
    if dungeon.downstairs_location:
        for idx, (room, _, _, _) in enumerate(rooms):
            if _room_contains_point(room, dungeon.downstairs_location):
                downstairs_room_idx = idx
                break
    if upstairs_room_idx is None and rooms:
        upstairs_room_idx = 0
    if downstairs_room_idx is None and rooms:
        downstairs_room_idx = len(rooms) - 1

    hot_path_centers: List[Tuple[int, int]] = []
    if upstairs_room_idx is not None and downstairs_room_idx is not None:
        idx_path = _shortest_room_path(connection_points, connections, upstairs_room_idx, downstairs_room_idx)
        if idx_path:
            hot_path_centers = [connection_points[i] for i in idx_path]
    start_for_hot_path = entry_point or dungeon.upstairs_location or (engine.player.x, engine.player.y)
    if getattr(settings, "DEBUG_DRAW_HOT_PATH", False):
        step_by_step_hot_path = build_step_by_step_hot_path(
            dungeon,
            centers=hot_path_centers,
            start=start_for_hot_path,
            goal=dungeon.downstairs_location or start_for_hot_path,
        )
    else:
        step_by_step_hot_path = []
    dungeon.rooms_hot_path = list(hot_path_centers)
    dungeon.hot_path = list(hot_path_centers)  # compat
    dungeon.step_by_step_hot_path = step_by_step_hot_path
    dungeon.shortest_path = step_by_step_hot_path  # compat
    dungeon.locked_door_colors = locked_colors_in_floor
    if getattr(settings, "DEBUG_DRAW_HOT_PATH", False):
        from procgen import _draw_hot_path  # Lazy import to avoid circular dependency

        _draw_hot_path(dungeon, dungeon.step_by_step_hot_path, allowed_tiles=None)

    if floor_number == settings.TOTAL_FLOORS:
        last_hot_room_center = hot_path_centers[-1] if hot_path_centers else (0, 0)
        uniques.place_uniques(floor_number, last_hot_room_center, dungeon)

    if place_downstairs and dungeon.downstairs_location and entry_point:
        if not ensure_path_between(dungeon, entry_point, dungeon.downstairs_location):
            if not guarantee_downstairs_access(dungeon, entry_point, dungeon.downstairs_location):
                raise RuntimeError("generate_dungeon_v3 failed to connect upstairs and downstairs.")

    maybe_place_chest(dungeon, floor_number, [room for room, _, _, _ in rooms])
    maybe_place_table(dungeon, floor_number, [room for room, _, _, _ in rooms])
    maybe_place_bookshelf(dungeon, floor_number, [room for room, _, _, _ in rooms])
    dungeon.center_rooms = [room.center for room, _, _, _ in rooms]
    dungeon.engine.update_center_rooms_array(list(dungeon.center_rooms))
    return dungeon


__all__ = ["generate_dungeon_v3"]
