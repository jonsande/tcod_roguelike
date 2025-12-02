from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING
from collections import Counter

import random

import entity_factories
import tile_types
from generators.fixed import generate_array_of
from game_map import GameMap
from procgen import (
    RectangularRoom,
    _build_bookshelf_loot,
    _resolve_upstairs_location,
    _can_spawn_item_procedurally,
    _get_spawn_key,
    ensure_breakable_tiles,
    ensure_path_between,
    guarantee_downstairs_access,
    log_breakable_tile_mismatches,
    maybe_place_bookshelf,
    maybe_place_chest,
    maybe_place_table,
    place_entities_fixdungeon,
    spawn_door_entity,
    record_entity_spawned,
    record_loot_items,
)

if TYPE_CHECKING:
    from engine import Engine


# Bookshelf character: π
THE_LIBRARY_TEMPLATE: Tuple[str, ...] = (
    "##############################################################################",
    "##############################################################################",
    "#####....................................................................#####",
    "#####....................................................................#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####....................................................................#####",
    "#####....................................................................#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####....................................................................#####",
    "#####....................................................................#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####....................................................................#####",
    "#####....................................................................#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####....................................................................#####",
    "#####....................................................................#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#####",
    "#####....................................................................#####",
    "#####....................................................................#####",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#...#",
    "#####..ππππππ..ππππππ..ππππππ..ππππππ....ππππππ..ππππππ..ππππππ..ππππππ..#..>#",
    "#####....................................................................+..@#",
    "#####....................................................................#####",
    "##############################################################################",
)

THE_LIBRARY_MONSTER_TABLE: List[Tuple[object, int]] = [
    (entity_factories.orc, 6),
    (entity_factories.goblin, 5),
    (entity_factories.swarm_rat, 3),
    (entity_factories.snake, 90),
]

# Tabla de posibles monstruos a generarse en las posiciones con "M"
RANDOM_MONSTERS_IN_STATIC_POSITIONS = [entity_factories.orc, entity_factories.goblin, entity_factories.snake]

THE_LIBRARY_ITEM_TABLE: List[Tuple[object, int]] = [
    (entity_factories.health_potion, 5),
    (entity_factories.strength_potion, 3),
    (entity_factories.stamina_potion, 3),
    (entity_factories.strength_potion, 1), 
    (entity_factories.increase_max_stamina, 1), 
    (entity_factories.life_potion, 1), 
    (entity_factories.infra_vision_potion, 1), 
    (entity_factories.antidote, 1), 
    (entity_factories.poison_potion, 1),
    (entity_factories.blindness_potion, 1), 
    (entity_factories.confusion_potion, 1), 
    (entity_factories.paralysis_potion, 1), 
    (entity_factories.petrification_potion, 1), 
    (entity_factories.precission_potion, 1),
    (entity_factories.confusion_scroll, 1),
    (entity_factories.paralisis_scroll, 1),
    (entity_factories.identify_scroll, 3),
    (entity_factories.lightning_scroll, 2),
    (entity_factories.fireball_scroll, 2),
    (entity_factories.descend_scroll, 1),
    (entity_factories.teleport_scroll, 3),
    (entity_factories.prodigious_memory_scroll, 1),
    (entity_factories.long_sword, 1),
    (entity_factories.long_sword_plus, 1),
    (entity_factories.short_sword, 1),
    (entity_factories.short_sword_plus, 1),
    (entity_factories.spear, 1),
    (entity_factories.spear_plus, 1),
    (entity_factories.poisoned_triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),
    (entity_factories.triple_ration, 1),

]

# Rango de entidades aleatorias por habitación en este mapa.
THE_LIBRARY_MONSTER_COUNT = (5, 6)
THE_LIBRARY_ITEM_COUNT = (3, 6)


def _weighted_choices(pool: List[Tuple[object, int]], k: int) -> List[object]:
    if not pool or k <= 0:
        return []
    entities, weights = zip(*pool)
    return random.choices(entities, weights=weights, k=k)


def _place_random_entities_the_library(
    room: RectangularRoom,
    dungeon: GameMap,
    *,
    forbidden_cells: List[Tuple[int, int]],
    floor_number: int,
) -> None:
    """Place random monsters/items using the custom three-doors tables."""
    min_monsters, max_monsters = THE_LIBRARY_MONSTER_COUNT
    min_items, max_items = THE_LIBRARY_ITEM_COUNT
    number_of_monsters = random.randint(min_monsters, max_monsters)
    number_of_items = random.randint(min_items, max_items)

    monsters = _weighted_choices(THE_LIBRARY_MONSTER_TABLE, number_of_monsters)
    items = _weighted_choices(THE_LIBRARY_ITEM_TABLE, number_of_items)

    allowed_cells: List[Tuple[int, int]] = []
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
            if any(existing.x == x and existing.y == y for existing in dungeon.entities):
                continue
            allowed_cells.append((x, y))

    if not allowed_cells:
        return

    random.shuffle(allowed_cells)
    cursor = 0

    item_pending: Counter = Counter()

    for monster in monsters:
        if cursor >= len(allowed_cells):
            break
        x, y = allowed_cells[cursor]
        cursor += 1
        spawned = monster.spawn(dungeon, x, y)
        key = _get_spawn_key(monster)
        record_entity_spawned(
            spawned,
            floor_number,
            "monsters",
            key=key,
            procedural=True,
            source="library",
        )

    for item in items:
        if cursor >= len(allowed_cells):
            break
        key = _get_spawn_key(item)
        if key and not _can_spawn_item_procedurally(key, item_pending):
            continue
        x, y = allowed_cells[cursor]
        cursor += 1
        spawned = item.spawn(dungeon, x, y)
        if key:
            item_pending[key] += 1
        record_entity_spawned(
            spawned,
            floor_number,
            "items",
            key=key,
            procedural=True,
            source="library",
        )

def generate_the_library_map(
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    map: Tuple[str, ...] = THE_LIBRARY_TEMPLATE,
    walls,
    walls_special,
    floor_number: int,
    place_player: bool,
    place_downstairs: bool,
    upstairs_location: Optional[Tuple[int, int]] = None,
) -> GameMap:
    """Generate the fixed library layout (initially mirrors the the_library flow)."""
    entities = [engine.player] if place_player else []
    dungeon = GameMap(engine, map_width, map_height, entities=entities)

    rooms: List[RectangularRoom] = []
    center_of_last_room = (30, 30)
    room_width = 79
    room_height = 35
    new_room = RectangularRoom(0, 0, room_width, room_height)
    dungeon.tiles[new_room.inner] = tile_types.library_floor

    entry_point: Optional[Tuple[int, int]] = None
    resolved_upstairs = _resolve_upstairs_location(dungeon, upstairs_location)
    if resolved_upstairs:
        dungeon.upstairs_location = resolved_upstairs
        entry_point = resolved_upstairs

    walls_array = generate_array_of(map, "#")
    special_walls_array = generate_array_of(map, "√")
    special_floor_array = generate_array_of(map, " ")
    stairs_options = generate_array_of(map, ">")
    player_starts = generate_array_of(map, "@")
    doors = generate_array_of(map, "+")
    fake_walls_array = generate_array_of(map, "*")
    bookshelf_array = generate_array_of(map, "π")

    snake_array = generate_array_of(map, "s")
    swarm_rat_array = generate_array_of(map, "r")
    goblin_array = generate_array_of(map, "g")
    orc_array = generate_array_of(map, "o")
    sentinel_array = generate_array_of(map, "&")
    random_monsters_array = generate_array_of(map, "M")
    potion_array = generate_array_of(map, "!")

    forbidden_cells: List[Tuple[int, int]] = []
    forbidden_cells.extend(walls_array)
    forbidden_cells.extend(special_floor_array)
    forbidden_cells.extend(stairs_options)
    forbidden_cells.extend(player_starts)
    forbidden_cells.extend(doors)
    forbidden_cells.extend(fake_walls_array)
    forbidden_cells.extend(bookshelf_array)

    #place_entities_fixdungeon(new_room, dungeon, floor_number, forbidden_cells)
    _place_random_entities_the_library(
        new_room, dungeon, forbidden_cells=forbidden_cells, floor_number=floor_number
    )

    for x, y in walls_array:
        dungeon.tiles[(x, y)] = walls

    for x, y in special_walls_array:
        dungeon.tiles[(x, y)] = walls_special

    for x, y in special_floor_array:
        dungeon.tiles[(x, y)] = tile_types.floor

    dungeon.downstairs_location = None
    chosen_downstairs: Optional[Tuple[int, int]] = None
    if place_downstairs and stairs_options:
        chosen_downstairs = random.choice(stairs_options)
    for sx, sy in stairs_options:
        dungeon.tiles[(sx, sy)] = tile_types.floor
    if place_downstairs:
        if not chosen_downstairs:
            chosen_downstairs = center_of_last_room
        dungeon.tiles[chosen_downstairs] = tile_types.down_stairs
        dungeon.downstairs_location = chosen_downstairs

    for x, y in doors:
        dungeon.tiles[(x, y)] = tile_types.closed_door
        spawn_door_entity(dungeon, x, y)

    for x, y in fake_walls_array:
        dungeon.tiles[(x, y)] = tile_types.breakable_wall
        dungeon.tiles["dark"]["fg"][x, y] = walls["dark"]["fg"]
        dungeon.tiles["dark"]["bg"][x, y] = walls["dark"]["bg"]
        dungeon.tiles["light"]["fg"][x, y] = walls["light"]["fg"]
        dungeon.tiles["light"]["bg"][x, y] = walls["light"]["bg"]
        entity_factories.breakable_wall.spawn(dungeon, x, y)

    for x, y in bookshelf_array:
        shelf = entity_factories.bookshelf.spawn(dungeon, x, y)
        # TODO: el contenido de los bookshelf de the_library no debe generarse de la forma
        # habitual. Dentro sólo debe haber libros. Hay que crear también, por tanto, libros
        # genéricos en entity_factories
        loot = _build_bookshelf_loot(floor_number)
        entity_factories.fill_container_with_items(shelf, loot)
        record_loot_items(loot, floor_number, procedural=True, source="library_bookshelf")

    for x, y in snake_array:
        spawned = entity_factories.snake.spawn(dungeon, x, y)
        record_entity_spawned(
            spawned, floor_number, "monsters", procedural=False, source="library_static"
        )

    for x, y in swarm_rat_array:
        spawned = entity_factories.swarm_rat.spawn(dungeon, x, y)
        record_entity_spawned(
            spawned, floor_number, "monsters", procedural=False, source="library_static"
        )

    for x, y in goblin_array:
        spawned = entity_factories.goblin.spawn(dungeon, x, y)
        record_entity_spawned(
            spawned, floor_number, "monsters", procedural=False, source="library_static"
        )

    for x, y in orc_array:
        spawned = entity_factories.orc.spawn(dungeon, x, y)
        record_entity_spawned(
            spawned, floor_number, "monsters", procedural=False, source="library_static"
        )

    for x, y in sentinel_array:
        spawned = entity_factories.sentinel.spawn(dungeon, x, y)
        record_entity_spawned(
            spawned, floor_number, "monsters", procedural=False, source="library_static"
        )

    # Aquí se generan los monstruos que van a colocarse en las casillas en las que haya
    # una "M". Configurar las opciones de monstruos posibles al gusto.
    for x, y in random_monsters_array:
        selected_monster = entity_factories.monster_roulette(
            choices=RANDOM_MONSTERS_IN_STATIC_POSITIONS
        )
        spawned = selected_monster.spawn(dungeon, x, y)
        record_entity_spawned(
            spawned, floor_number, "monsters", procedural=True, source="library_random"
        )

    for x, y in potion_array:
        spawned = entity_factories.health_potion.spawn(dungeon, x, y)
        record_entity_spawned(
            spawned, floor_number, "items", procedural=False, source="library_static"
        )

    player_intro = random.choice(player_starts) if player_starts else center_of_last_room
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
                    print("WARNING: Library template has no guaranteed path between upstairs and downstairs.")

    #maybe_place_chest(dungeon, floor_number, rooms)
    #maybe_place_table(dungeon, floor_number, rooms)
    #maybe_place_bookshelf(dungeon, floor_number, rooms)
    ensure_breakable_tiles(dungeon)
    if engine.debug:
        log_breakable_tile_mismatches(dungeon, "generate_the_library_map")
    dungeon.center_rooms = []
    dungeon.door_candidates = []
    return dungeon


__all__ = ["generate_the_library_map", "THE_LIBRARY_TEMPLATE"]
