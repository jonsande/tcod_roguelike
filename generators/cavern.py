from __future__ import annotations

from typing import Optional, Tuple, List, TYPE_CHECKING

import numpy as np
import random

import entity_factories
import settings
import tile_types
from game_map import GameMap
from procgen import (
    _can_place_entity,
    _select_weighted_spawn_entries,
    generation_tracker,
    cavern_item_count_by_floor,
    cavern_item_spawn_rules,
    cavern_monster_count_by_floor,
    cavern_monster_spawn_rules,
    ensure_path_between,
    get_floor_value,
    maybe_place_chest,
    maybe_place_table,
    #maybe_place_bookshelf,
)

if TYPE_CHECKING:
    from engine import Engine


WALL = False
FLOOR = True


def generate_noise_map(width: int, height: int, fill_probability: float) -> np.ndarray:
    rng = np.random.default_rng()
    return rng.random((width, height)) < fill_probability


def simulate_ca_step(map_array: np.ndarray, birth_limit: int, death_limit: int) -> np.ndarray:
    wall_count = np.zeros_like(map_array, dtype=np.int8)

    width, height = map_array.shape
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            shifted = np.roll(map_array, shift=(dx, dy), axis=(0, 1))

            if dx == -1:
                shifted[-1, :] = WALL
            if dx == 1:
                shifted[0, :] = WALL
            if dy == -1:
                shifted[:, -1] = WALL
            if dy == 1:
                shifted[:, 0] = WALL

            wall_count += shifted == WALL

    new_map = np.where(wall_count > death_limit, WALL, FLOOR)
    new_map = np.where(wall_count < birth_limit, FLOOR, new_map)
    return new_map


def generate_cavern_map(
    width: int,
    height: int,
    steps: int = 4,
    fill_probability: float = 0.45,
    birth_limit: int = 4,
    death_limit: int = 4,
) -> np.ndarray:
    noise = generate_noise_map(width, height, fill_probability=fill_probability)

    for _ in range(steps):
        noise = simulate_ca_step(noise, birth_limit, death_limit)

    noise[0, :] = WALL
    noise[-1, :] = WALL
    noise[:, 0] = WALL
    noise[:, -1] = WALL

    return noise


def flood_fill(map_array: np.ndarray, start: Tuple[int, int]) -> List[Tuple[int, int]]:
    width, height = map_array.shape
    visited = np.zeros_like(map_array, dtype=bool)
    to_visit = [start]
    region: List[Tuple[int, int]] = []

    while to_visit:
        x, y = to_visit.pop()
        if not (0 <= x < width and 0 <= y < height):
            continue
        if visited[x, y]:
            continue
        if map_array[x, y] == WALL:
            continue

        visited[x, y] = True
        region.append((x, y))

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            to_visit.append((x + dx, y + dy))

    return region


def connect_cavern_regions(map_array: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int], Tuple[int, int]]:
    width, height = map_array.shape
    visited = np.zeros_like(map_array, dtype=bool)
    regions: List[List[Tuple[int, int]]] = []

    for x in range(width):
        for y in range(height):
            if map_array[x, y] == FLOOR and not visited[x, y]:
                region = flood_fill(map_array, (x, y))
                for rx, ry in region:
                    visited[rx, ry] = True
                if region:
                    regions.append(region)

    if not regions:
        return map_array, (width // 2, height // 2), (width // 2 + 1, height // 2 + 1)

    regions.sort(key=len, reverse=True)
    main_region = set(regions[0])

    for region in regions[1:]:

        closest_main = None
        closest_region = None
        best_distance = None

        for x1, y1 in region:
            for x2, y2 in main_region:
                distance = abs(x1 - x2) + abs(y1 - y2)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    closest_main = (x2, y2)
                    closest_region = (x1, y1)

        if closest_main and closest_region:
            x1, y1 = closest_region
            x2, y2 = closest_main
            cx, cy = x1, y1
            while (cx, cy) != (x2, y2):
                if cx < x2:
                    cx += 1
                elif cx > x2:
                    cx -= 1
                elif cy < y2:
                    cy += 1
                elif cy > y2:
                    cy -= 1
                map_array[cx, cy] = FLOOR
                main_region.add((cx, cy))

        main_region |= set(region)

    floor_tiles = list(main_region)
    player_start = random.choice(floor_tiles)
    stairs_location = random.choice(floor_tiles)

    return map_array, player_start, stairs_location



def populate_cavern(dungeon: GameMap, floor_number: int) -> None:
    for entity in list(dungeon.entities):
        if entity is dungeon.engine.player:
            continue
        dungeon.entities.discard(entity)

    rooms_array = []
    dungeon.engine.update_center_rooms_array(rooms_array)

    for _ in range(60):
        x = random.randint(1, dungeon.width - 2)
        y = random.randint(1, dungeon.height - 2)
        if (
            dungeon.tiles["walkable"][x, y]
            and not dungeon.is_downstairs_location(x, y)
            and (not dungeon.upstairs_location or (x, y) != dungeon.upstairs_location)
        ):
            entity_factories.debris_a.spawn(dungeon, x, y)
    dungeon.spawn_monsters_counter = 0
    dungeon.spawn_monsters_generated = 0

    min_monsters, max_monsters = get_floor_value(
        cavern_monster_count_by_floor, floor_number, (8, 14)
    )
    min_monsters = max(0, min_monsters)
    max_monsters = max(min_monsters, max_monsters)
    number_of_monsters = random.randint(min_monsters, max_monsters)

    for monster_entry in _select_weighted_spawn_entries(
        cavern_monster_spawn_rules, number_of_monsters, floor_number, "monsters"
    ):
        for _ in range(40):
            x = random.randint(1, dungeon.width - 2)
            y = random.randint(1, dungeon.height - 2)
            if not _can_place_entity(dungeon, x, y):
                continue
            monster_entry["entity"].spawn(dungeon, x, y)
            generation_tracker.record(
                "monsters",
                floor_number,
                monster_entry["name"],
                procedural=True,
                source="cavern",
            )
            break

    min_items, max_items = get_floor_value(
        cavern_item_count_by_floor, floor_number, (0, 0)
    )
    min_items = max(0, min_items)
    max_items = max(min_items, max_items)
    number_of_items = random.randint(min_items, max_items) if max_items > 0 else 0

    for item_entry in _select_weighted_spawn_entries(
        cavern_item_spawn_rules, number_of_items, floor_number, "items"
    ):
        for _ in range(40):
            x = random.randint(1, dungeon.width - 2)
            y = random.randint(1, dungeon.height - 2)
            if not _can_place_entity(dungeon, x, y):
                continue
            item_entry["entity"].spawn(dungeon, x, y)
            generation_tracker.record(
                "items",
                floor_number,
                item_entry["name"],
                procedural=True,
                source="cavern",
            )
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
    dungeon.is_cavern = True
    dungeon.tiles = np.full((map_width, map_height), fill_value=tile_types.wall, order="F")

    fill_probability = fill_probability if fill_probability is not None else settings.CAVERN_FILL_PROBABILITY
    birth_limit = birth_limit if birth_limit is not None else settings.CAVERN_BIRTH_LIMIT
    death_limit = death_limit if death_limit is not None else settings.CAVERN_DEATH_LIMIT
    smoothing_steps = smoothing_steps if smoothing_steps is not None else settings.CAVERN_SMOOTHING_STEPS

    ca_map = generate_cavern_map(
        map_width,
        map_height,
        steps=smoothing_steps,
        fill_probability=fill_probability,
        birth_limit=birth_limit,
        death_limit=death_limit,
    )
    ca_map, player_start, stairs_location = connect_cavern_regions(ca_map)

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
    maybe_place_table(dungeon, floor_number)
    #maybe_place_bookshelf(dungeon, floor_number)

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


__all__ = ["generate_cavern", "populate_cavern"]
