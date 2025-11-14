from __future__ import annotations
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING, Optional, Set
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

"""En la línea 289 aprox establecemos el número de niveles de la mazmorra"""

# Direcciones cardinales (N, S, E, O) reutilizadas en varias rutinas.
CARDINAL_DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
# Número máximo de puertas por nivel
max_doors = 4
# Número de muros rompibles
max_breakable_walls = 3

# Relative weights for non-rectangular room shapes (rectangle weight is always 1.0).
ROOM_SHAPE_WEIGHTS = settings.ROOM_SHAPE_WEIGHTS
ROOM_MIN_SIZE_SHAPES = settings.ROOM_MIN_SIZE_SHAPES
ROOM_DECORATION_CHANCE = settings.ROOM_DECORATION_CHANCE
FIXED_ROOM_CHANCES = settings.FIXED_ROOM_CHANCES

# Escombros máximos por planta
max_debris_by_floor = settings.MAX_DEBRIS_BY_FLOOR

# Items máximos por habitación
# Nivel mazmorra | nº items
treasure_floor = random.randint(5,9)
max_items_by_floor = settings.MAX_ITEMS_BY_FLOOR

# Monstruos máximos por habitación
# Nivel mazmorra | nº monstruos
max_monsters_by_floor = settings.MAX_MONSTERS_BY_FLOOR


def _resolve_entity_table(table_config):
    resolved: Dict[int, List[Tuple[Entity, int]]] = {}
    for floor, entries in table_config.items():
        resolved_entries = []
        for name, weight in entries:
            entity = getattr(entity_factories, name)
            resolved_entries.append((entity, weight))
        resolved[floor] = resolved_entries
    return resolved


item_chances = _resolve_entity_table(settings.ITEM_CHANCES)
enemy_chances = _resolve_entity_table(settings.ENEMY_CHANCES)
debris_chances = _resolve_entity_table(settings.DEBRIS_CHANCES)


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

    # Monstruos
    monsters: List[Entity] = get_entities_at_random(
        enemy_chances, number_of_monsters, floor_number
    )
    items: List[Entity] = get_entities_at_random(
        item_chances, number_of_items, floor_number
    )

    #
    debris: List[Entity] = get_entities_at_random(
        debris_chances, number_of_debris, floor_number
    )

    # Generamos las coordenadas de spawneo (en habitación)
    # para cada monstruo e ítem a generar
    def can_place_entity(entity: Entity, x: int, y: int) -> bool:
        if not dungeon.in_bounds(x, y):
            return False
        if not dungeon.tiles["walkable"][x, y]:
            return False
        if (x, y) == dungeon.downstairs_location:
            return False
        if any(existing.x == x and existing.y == y for existing in dungeon.entities):
            return False
        return True

    for entity in monsters + items + debris:
        placed = False
        for _ in range(20):
            x, y = room.random_location()

            if can_place_entity(entity, x, y):
                print(f"DEBUG: Generando... {entity.name} en x={x} y={y}")
                entity.spawn_coord = (x, y)
                entity.spawn(dungeon, x, y)
                placed = True
                break

        if not placed:
            if __debug__:
                print(f"DEBUG: Failed to place {entity.name} in room at {room.center}")
            

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
    if (x, y) == dungeon.downstairs_location:
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
                dungeon.tiles[tx, ty] = tile_types.wall
                instance = entity_factories.breakable_wall.spawn(dungeon, tx, ty)
                wall_char_code = tile_types.wall["light"]["ch"]
                wall_fg = tuple(tile_types.wall["light"]["fg"])
                instance.char = chr(wall_char_code)
                instance.color = wall_fg
            elif ch == "+":
                dungeon.tiles[tx, ty] = tile_types.closed_door
    cx, cy = room.center
    dungeon.tiles[cx, cy] = tile_types.floor
    return True


def ensure_path_between(dungeon: GameMap, start: Tuple[int, int], goal: Tuple[int, int]) -> bool:
    from collections import deque

    width, height = dungeon.width, dungeon.height
    visited = set()
    queue = deque([start])

    def is_traversable(x: int, y: int) -> bool:
        if not dungeon.in_bounds(x, y):
            return False
        if dungeon.tiles["walkable"][x, y]:
            return True
        actor = dungeon.get_blocking_entity_at_location(x, y)
        if actor and getattr(actor, "name", "").lower().startswith("door"):
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

    # Monstruos
    monsters: List[Entity] = get_entities_at_random(
        enemy_chances, number_of_monsters, floor_number
    )
    items: List[Entity] = get_entities_at_random(
        item_chances, number_of_items, floor_number
    )

    #
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
            if (x, y) == dungeon.downstairs_location:
                continue
            allowed_cells_array.append((x, y))

    for entity in monsters + items + debris:
        cell = random.choice(allowed_cells_array)
        # DEBUG
        #print(f"SELECTED CELL: {cell}")
        x = cell[0]
        y = cell[1]

        if not any(entity.x == x and entity.y == y for entity in dungeon.entities) and dungeon.in_bounds(x, y):

            # Memorizamos las coordenadas donde se va a spawmear en origen la entidad
            # Esto es para la mecánica de la ia de que el monstruo vuelva a su posición
            # cuando el PJ queda fuera de su rango de detección
            entity.spawn_coord = (x, y)

            # Se spawmea
            entity.spawn(dungeon, x, y)


def generate_fixed_dungeon(
    map_width: int,
    map_height: int,
    engine: Engine,
    map,
    walls,
    walls_special
) -> GameMap:
    """Generate a new dungeon map."""
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, entities=[player])

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

    # Dig out this rooms inner area.
    dungeon.tiles[new_room.inner] = tile_types.floor
    
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

    forbidden_cells = []
    forbidden_cells.extend(walls_array)
    forbidden_cells.extend(special_floor_array)
    forbidden_cells.extend(stairs)
    forbidden_cells.extend(player_intro)
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
        engine.game_world.current_floor, 
        forbidden_cells, 
        )
    
    # Colocamos muros, especiales, escaleras y puertas
    for x, y in walls_array:
        dungeon.tiles[(x, y)] = walls
        
    for x, y in special_walls_array:
        dungeon.tiles[(x, y)] = walls_special
        
    for x, y in special_floor_array:
        dungeon.tiles[(x, y)] = tile_types.floor
        
    for x, y in stairs:
        dungeon.tiles[(x, y)] = tile_types.down_stairs
        dungeon.downstairs_location = (x, y)
    
    for x, y in doors:
        dungeon.tiles[(x, y)] = tile_types.closed_door
        
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
    
    # Colocamos al héroe
    player.place(player_intro[0], player_intro[1])
        
    
    

    #import gen_uniques
    #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)

    # Finally, append the new room to the list.
    rooms.append(new_room)
    # rooms.append(new_room2)

    return dungeon


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
        if dungeon.tiles["walkable"][x, y] and (x, y) != dungeon.downstairs_location:
            entity_factories.debris_a.spawn(dungeon, x, y)
    dungeon.spawn_monsters_counter = 0

    for _ in range(random.randint(8, 14)):
        x = random.randint(1, dungeon.width - 2)
        y = random.randint(1, dungeon.height - 2)
        if dungeon.tiles["walkable"][x, y] and (x, y) != dungeon.downstairs_location:
            entity_factories.monster_roulette().spawn(dungeon, x, y)


def generate_cavern(
    map_width: int,
    map_height: int,
    engine: Engine,
    *,
    fill_probability: Optional[float] = None,
    birth_limit: Optional[int] = None,
    death_limit: Optional[int] = None,
    smoothing_steps: Optional[int] = None,
) -> GameMap:
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, entities=[player])
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

    dungeon.tiles[player_start] = tile_types.floor
    player.place(*player_start, dungeon)

    dungeon.tiles[stairs_location] = tile_types.floor
    dungeon.tiles[stairs_location] = tile_types.down_stairs
    dungeon.downstairs_location = stairs_location

    populate_cavern(dungeon, engine.game_world.current_floor)

    return dungeon


def generate_dungeon(
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_width: int,
    map_height: int,
    engine: Engine,
) -> GameMap:
    """Generate a new dungeon map."""
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, entities=[player])

    rooms: List[RectangularRoom] = []
    #rooms: List[TownRoom] = []

    center_of_last_room = (0, 0)
    rooms_array = []

    for _ in range(max_rooms):
        template = None
        fixed_choice = get_fixed_room_choice(engine.game_world.current_floor)
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
            # The first room, where the player starts.
            player.place(*new_room.center, dungeon)
            center_of_last_room = new_room.center
            rooms_array.append(center_of_last_room)
        else:  # All rooms after the first.
            for x, y in tunnel_between(rooms[-1].center, new_room.center):
                dungeon.tiles[x, y] = tile_types.floor

            center_of_last_room = new_room.center
            rooms_array.append(center_of_last_room)
            engine.update_center_rooms_array(rooms_array)
            if engine.debug == True:
                print(f"DEBUG: CENTER OF ROOMS ARRAY: {rooms_array}")

        # Colocamos entidades genéricas
        place_entities(new_room, dungeon, engine.game_world.current_floor)

        # Colocamos escaleras,
        # pero evitando que se genere escalera en el nivel 16
        if engine.game_world.current_floor == 16:
            pass
        else:
            dungeon.tiles[center_of_last_room] = tile_types.floor
            dungeon.tiles[center_of_last_room] = tile_types.down_stairs
            dungeon.downstairs_location = center_of_last_room

        #import gen_uniques
        #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)
        
        # Colocamos entidades especiales
        # Esto seguramente sería mejor hacerlo con place() de entity.py
        uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)

        # Finally, append the new room to the list.
        rooms.append(new_room)
        # rooms.append(new_room2)

    if not ensure_path_between(
        dungeon,
        (player.x, player.y),
        dungeon.downstairs_location,
    ):
        return generate_dungeon(
            max_rooms, room_min_size, room_max_size, map_width, map_height, engine
        )

    door_candidates = collect_door_candidates(dungeon)

    return place_doors(dungeon, door_candidates)


def place_doors(dungeon: GameMap, door_options: List[Tuple[int, int]]):

    if not door_options:
        return dungeon

    pool = door_options.copy()
    random.shuffle(pool)

    doors_to_place = min(max_doors, len(pool))
    selected_doors = pool[:doors_to_place]

    for x, y in selected_doors:
        dungeon.tiles[x, y] = tile_types.closed_door

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

            if (x, y) == dungeon.downstairs_location:
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
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_width: int,
    map_height: int,
    engine: Engine,
) -> GameMap:
    """Generate a new dungeon map."""
    player = engine.player
    #dungeon = GameMap(engine, map_width, map_height, entities=[player])
    dungeon = GameMapTown(engine, map_width, map_height, entities=[player])

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

    if len(rooms) == 0:
        # The first room, where the player starts.
        player.place(*new_room.center, dungeon)
    else:  # All rooms after the first.
        # Dig out a tunnel between this room and the previous one.
        #for x, y in tunnel_between(rooms[-1].center, new_room.center):
        #    dungeon.tiles[x, y] = tile_types.floor
        pass  
        

        #center_of_last_room = new_room.center

    # Colocamos entidades genéricas
    place_entities(new_room, dungeon, engine.game_world.current_floor)

    # Colocamos escaleras,
    dungeon.tiles[(35, 17)] = tile_types.floor
    dungeon.tiles[(35, 17)] = tile_types.down_stairs
    dungeon.downstairs_location = (35, 17)

    #import gen_uniques
    #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)

    # Finally, append the new room to the list.
    rooms.append(new_room)
    # rooms.append(new_room2)

    return dungeon
