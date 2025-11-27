from __future__ import annotations

from collections import deque
from typing import List, Optional, Set, Tuple, TYPE_CHECKING

import settings
import tile_types
from game_map import GameMap
from procgen import (
    V2RoomNode,
    _create_initial_v2_room,
    _expand_room_from_entry,
    _manhattan_distance,
    ensure_path_between,
    guarantee_downstairs_access,
    maybe_place_chest,
    maybe_place_table,
)

if TYPE_CHECKING:
    from engine import Engine


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
        maybe_place_table(dungeon, floor_number, [node.rect for node in rooms])
        dungeon.center_rooms = [center for center in rooms_array]
        dungeon.engine.update_center_rooms_array(list(rooms_array))
        return dungeon

    raise RuntimeError("generate_dungeon_v2 failed to build a valid layout.")


__all__ = ["generate_dungeon_v2"]
