from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

import entity_factories
import fixed_maps
import tile_types

from game_map import GameMap
from procgen import (
    RectangularRoom,
    _resolve_upstairs_location,
    ensure_breakable_tiles,
    ensure_path_between,
    guarantee_downstairs_access,
    log_breakable_tile_mismatches,
    maybe_place_chest,
    maybe_place_table,
    place_entities_fixdungeon,
    spawn_door_entity,
)

if TYPE_CHECKING:
    from engine import Engine


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

    center_of_last_room = (30, 30)

    room_width = 79
    room_height = 35

    x = 0
    y = 0

    new_room = RectangularRoom(x, y, room_width, room_height)

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
        selected_monster = entity_factories.monster_roulette(
            choices=[entity_factories.orc, entity_factories.goblin, entity_factories.snake]
        )
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

    rooms.append(new_room)

    if place_downstairs and dungeon.downstairs_location and entry_point:
        if not ensure_path_between(dungeon, entry_point, dungeon.downstairs_location):
            if not guarantee_downstairs_access(dungeon, entry_point, dungeon.downstairs_location):
                if __debug__:
                    print("WARNING: Fixed dungeon template has no guaranteed path between upstairs and downstairs.")

    maybe_place_chest(dungeon, floor_number, rooms)
    maybe_place_table(dungeon, floor_number, rooms)
    ensure_breakable_tiles(dungeon)
    if engine.debug:
        log_breakable_tile_mismatches(dungeon, "generate_fixed_dungeon")
    dungeon.center_rooms = []
    return dungeon


__all__ = ["generate_fixed_dungeon"]
