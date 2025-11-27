from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

import random

import entity_factories
import settings
import tile_types
import uniques
from game_map import GameMap
from procgen import (
    DUNGEON_EXTRA_CONNECTION_ATTEMPTS,
    DUNGEON_EXTRA_CONNECTION_CHANCE,
    RectangularRoom,
    add_room_decorations,
    carve_fixed_room,
    carve_room,
    carve_tunnel_path,
    choose_room_shape,
    ensure_breakable_tiles,
    ensure_path_between,
    get_fixed_room_choice,
    guarantee_downstairs_access,
    log_breakable_tile_mismatches,
    maybe_place_chest,
    maybe_place_table,
    place_entities,
    spawn_door_entity,
)

if TYPE_CHECKING:
    from engine import Engine


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

        shape = "rectangle" if template else choose_room_shape(room_width, room_height)
        new_room = RectangularRoom(x, y, room_width, room_height, shape=shape)

        if any(new_room.intersects(other_room) for other_room in rooms):
            continue

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
        else:
            carve_tunnel_path(dungeon, rooms[-1].center, new_room.center)

            center_of_last_room = new_room.center
            downstairs_candidate = center_of_last_room
            rooms_array.append(center_of_last_room)
            engine.update_center_rooms_array(rooms_array)
            if settings.DEBUG_MODE and engine.debug:
                from color import bcolors

                print(
                    f"{bcolors.WARNING}====== DEBUG: Placing entities in room at..."
                    f"\nDungeon: {dungeon}\nFloor number: {floor_number}\n"
                    f"Room center: {new_room.center}\nFixed: {used_fixed_room}{bcolors.ENDC}"
                )

        if rooms and DUNGEON_EXTRA_CONNECTION_CHANCE > 0:
            for _ in range(DUNGEON_EXTRA_CONNECTION_ATTEMPTS):
                if random.random() < DUNGEON_EXTRA_CONNECTION_CHANCE:
                    target_room = random.choice(rooms)
                    carve_tunnel_path(dungeon, target_room.center, new_room.center)

        if settings.DEBUG_MODE and engine.debug:
            from color import bcolors

            print(
                f"{bcolors.WARNING}====== DEBUG: Placing entities in room at..."
                f"\nDungeon: {dungeon}\nFloor number: {floor_number}\n"
                f"Room center: {new_room.center}\nFixed: {used_fixed_room}{bcolors.ENDC}"
            )

        place_entities(new_room, dungeon, floor_number)
        uniques.place_uniques(floor_number, center_of_last_room, dungeon)
        rooms.append(new_room)

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
    maybe_place_table(dungeon, floor_number, rooms)
    dungeon.center_rooms = list(rooms_array)
    return dungeon


def place_doors(dungeon: GameMap, door_options: List[Tuple[int, int]]) -> GameMap:
    from procgen import max_breakable_walls, max_doors

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


__all__ = ["generate_dungeon", "place_doors", "collect_door_candidates"]
