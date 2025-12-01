from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

import tile_types
from game_map import GameMapTown
from procgen import (
    TownRoom,
    _place_town_old_man_with_campfire,
    ensure_path_between,
    maybe_place_chest,
    maybe_place_table,
    maybe_place_bookshelf,
    place_entities,
)

if TYPE_CHECKING:
    from engine import Engine


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
) -> GameMapTown:
    """Generate a town-style starting area."""
    entities = [engine.player] if place_player else []
    dungeon = GameMapTown(engine, map_width, map_height, entities=entities)

    entry_point: Optional[Tuple[int, int]] = upstairs_location
    if upstairs_location:
        dungeon.upstairs_location = upstairs_location
        dungeon.tiles[upstairs_location] = tile_types.up_stairs

    rooms: List[TownRoom] = []

    center_of_last_room = (30, 30)

    room_width = 80
    room_height = 36

    x = 0
    y = 0

    new_room = TownRoom(x, y, room_width, room_height)

    dungeon.tiles[new_room.inner] = tile_types.town_floor

    if place_player:
        engine.player.place(*new_room.center, dungeon)
        entry_point = (engine.player.x, engine.player.y)
    elif entry_point is None:
        entry_point = new_room.center

    downstairs = (35, 17)

    _place_town_old_man_with_campfire(
        dungeon, stairs_location=downstairs, floor_number=floor_number
    )

    place_entities(new_room, dungeon, floor_number)

    if place_downstairs:
        dungeon.tiles[downstairs] = tile_types.floor
        dungeon.tiles[downstairs] = tile_types.down_stairs
        dungeon.downstairs_location = downstairs
    else:
        dungeon.downstairs_location = None

    rooms.append(new_room)

    maybe_place_chest(dungeon, floor_number, rooms)
    maybe_place_table(dungeon, floor_number, rooms)
    maybe_place_bookshelf(dungeon, floor_number, rooms)
    if place_downstairs and dungeon.downstairs_location and entry_point:
        if not ensure_path_between(dungeon, entry_point, dungeon.downstairs_location):
            raise RuntimeError("Town generation failed to connect starting area with stairs.")

    dungeon.center_rooms = []
    return dungeon


__all__ = ["generate_town"]
