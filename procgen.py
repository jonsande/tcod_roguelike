from __future__ import annotations
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING
from game_map import GameMap, GameMapTown
import tile_types
import random
import tcod
from entity_factories import *
import uniques

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity
    
import entity_factories
import fixed_maps

"""En la línea 289 aprox establecemos el número de niveles de la mazmorra"""

# Camino de tiles que genera la tuneladora
tiles_path = []
# Tiles que pertenecen a una habitación
room_tiles = []
# Número máximo de puertas por nivel
max_doors = 4
# Número de muros rompibles
max_breakable_walls = 3

# Escombros máximos por planta
max_debris_by_floor = [
    (1, 30),
    (2, 9),
    (4, 7),
    (6, 14), # Floor 5 FIXED
    (7, 2),
]

# Items máximos por habitación
# Nivel mazmorra | nº items
treasure_floor = random.randint(5,9)
max_items_by_floor = [
    (1, 2),
    #(1, 1),
    (2, 1),
    (3, 0), 
    (4, 2),
    (6, random.randint(1, 3)), # Floor 5 FIXED
    (7, 2),
    (11, random.randint(1, 5)), # Floor 10 FIXED
    (12, 1),
]

# Monstruos máximos por habitación
# Nivel mazmorra | nº monstruos
max_monsters_by_floor = [
    (0, 0),
    (1, 2),
    (2, 1),
    (3, 1),
    (4, 2),
    (6, 0), # Floor 5 FIXED
    (7, 2),
    (11, 2),  # Floor 10 FIXED

]

# Probabilidades de que se generen estas entidades por sala.
# El nivel 0 al parecer es lo que se aplica por defecto a todos los niveles
# Al parecer las tiradas se hacen en orden?!
item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    #0: [(health_potion, 1), (damage_potion, 1)],
    #1: [(power_potion, 100), (damage_potion, 100), (health_potion, 100), (confusion_scroll, 100), (paralisis_scroll, 100), (lightning_scroll, 100), (fireball_scroll, 100)],
    #1: [(chain_mail, 100), (short_sword, 100), (long_sword, 100), (grial, 100)],
    #1: [(dagger_plus, 100)],
    1: [(antidote, 5), (sand_bag, 5), (health_potion, 5), (posion_potion, 5), (power_potion, 5), (stamina_potion, 5), (confusion_potion, 5), (precission_potion, 5), (strength_potion, 2)],
    2: [(health_potion, 15), (posion_potion, 15), (power_potion, 15), (stamina_potion, 15), (confusion_potion, 15), (precission_potion, 15), (rock, 15), (table, 15)],
    3: [(poisoned_triple_ration, 10), (triple_ration, 10), (rock, 45), (confusion_scroll, 10), (paralisis_scroll, 10), (lightning_scroll, 5), (fireball_scroll, 5), (short_sword, 5)],
    4: [(confusion_scroll, 15), (paralisis_scroll, 15), (lightning_scroll, 10), (fireball_scroll, 5)],
    5: [(lightning_scroll, 10), (fireball_scroll, 10), (long_sword, 5), (chain_mail, 5)],
    7: [(spear, 5)],
    8: [(short_sword, 15)],
}
enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    #0: [(fireplace, 100)], # Esto no hace nada porque el max_monsters_by_floor está a 0
    #1: [(bandit, 100)],
    1: [(monkey, 20), (fireplace, 100), (snake, 10), (adventurer, 10), (rat, 50), (swarm_rat, 20), (goblin, 10)],
    2: [(monkey, 20), (adventurer, 2), (rat, 50), (swarm_rat, 50), (goblin, 50)],
    3: [(orc, 50), (goblin, 50)],
    4: [(swarm_rat, 20), (rat, 0), (orc, 20), (goblin, 30)],
    5: [(true_orc, 5), (orc, 30), (goblin, 30), (troll, 5)],
    8: [(adventurer, 15), (true_orc, 20), (orc, 50), (goblin, 15), (bandit, 10)],
    12: [(adventurer, 0)],
}
debris_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(debris_a, 30)],
    3: [(debris_a, 20)],
    6: [(debris_a, 10)],
}


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


class RectangularRoom:

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

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
    
"""
class FixedRoom:

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

    # Esto genera las coordenadas de spawneo (en habitación)
    # para cada monstruo e ítem a generar
    for entity in monsters + items + debris:
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        # Esto comprueba si la coordenada en la que spawmear
        # está o no ya ocupada, y spawmea
        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):

            # Memorizamos las coordenadas donde se va a spawmear en origen la entidad
            # Esto es para la mecánica de la ia de que el monstruo vuelva a su posición
            # cuando el PJ queda fuera de su rango de detección
            entity.spawn_coord = (x, y)

            # Se spawmea
            entity.spawn(dungeon, x, y)


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
            allowed_cells_array.append((x, y))

    allowed_cells_array = list(set(allowed_cells_array) - set(forbidden_cells))
    # DEBUG
    #print(f"Allowed cells array: {allowed_cells_array}")

    for entity in monsters + items + debris:
        cell = random.choice(allowed_cells_array)
        # DEBUG
        #print(f"SELECTED CELL: {cell}")
        x = cell[0]
        y = cell[1]

        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):

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
        dungeon.tiles[(x, y)] = tile_types.door
        
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
        selected_monster = fixed_maps.monster_roulette()
        selected_monster.spawn(dungeon, x, y)
    
    # Colocamos al héroe
    player.place(player_intro[0], player_intro[1])
        
    
    

    #import gen_uniques
    #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)

    # Finally, append the new room to the list.
    rooms.append(new_room)
    # rooms.append(new_room2)

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

    for r in range(max_rooms):
        room_width = random.randint(room_min_size, room_max_size)
        room_height = random.randint(room_min_size, room_max_size)

        x = random.randint(0, dungeon.width - room_width - 1)
        y = random.randint(0, dungeon.height - room_height - 1)

        # "RectangularRoom" class makes rectangles easier to work with
        new_room = RectangularRoom(x, y, room_width, room_height)

        # new_room2 = RectangularRoom2(x, y, room_width, room_height)

        # Run through the other rooms and see if they intersect with this one.
        if any(new_room.intersects(other_room) for other_room in rooms):
            continue  # This room intersects, so go to the next attempt.
        # If there are no intersections then the room is valid.

        # Dig out this rooms inner area.
        #dungeon.tiles[new_room.borders] = tile_types.door
        dungeon.tiles[new_room.inner] = tile_types.floor
        

        if len(rooms) == 0:
            # The first room, where the player starts.
            player.place(*new_room.center, dungeon)
        else:  # All rooms after the first.
            # Dig out a tunnel between this room and the previous one.


            # tunner_between(start: Tuple[int,int], end: Tuple[int,int])
            for x, y in tunnel_between(rooms[-1].center, new_room.center):

                # Coloca suelo en cada posición x,y
                dungeon.tiles[x, y] = tile_types.floor

                # listado de posiciones por pasa el generador de túneles
                global tiles_path

                tiles_path.append((x, y))

            center_of_last_room = new_room.center
            rooms_array.append(center_of_last_room)
            engine.update_center_rooms_array(rooms_array)
            if engine.debug == True:
                print(f"DEBUG: CENTER OF ROOMS ARRAY: {rooms_array}")

        # Colocamos entidades genéricas
        place_entities(new_room, dungeon, engine.game_world.current_floor)

        # Colocamos puertas
        door_options = generate_posible_doors(new_room, dungeon, engine.game_world.current_floor)

        # Colocamos escaleras,
        # pero evitando que se genere escalera en el nivel 12
        if engine.game_world.current_floor == 12:
            pass
        else:
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

    return place_doors(dungeon, door_options)


def place_doors(dungeon, door_options):

    if door_options == []:
        return dungeon
    else:

        #print(door_options)
        for i in range(max_doors):
            door_location = random.choice(door_options)  
            
            dungeon.tiles[door_location[0], door_location[1]] = tile_types.door
            #entity_factories.door.spawn(dungeon, door_location[0], door_location[1])
        
        for i in range(max_breakable_walls):
            breakable_wall_location = random.choice(door_options)
            dungeon.tiles[breakable_wall_location[0], breakable_wall_location[1]] = tile_types.breakable_wall
            entity_factories.breakable_wall.spawn(dungeon, breakable_wall_location[0], breakable_wall_location[1])

        #print(dungeon)

        return dungeon


def generate_posible_doors(room: RectangularRoom, dungeon: GameMap, floor_number: int,) -> None:
    
    # Crear una lista con las casillas de la habitación recién creada:

    x1 = room.x1
    x2 = room.x2
    y1 = room.y1
    y2 = room.y2

    global room_tiles
    for y in range(y1, y2 +1):
            for x in range(x1, x2 +1):
                room_tiles.append((x, y))
                 
    set1 = set(room_tiles)
    if tiles_path == []:
        pass
    
    else:
        set2 = set(tiles_path)
        #print("tiles_path set:")
        #print(set2)
        set2 = set2.difference(set1)
        #print("Final set")
        #print(set2)

        door_options = list(set2)
        #print("Door options list:")
        #print(door_options)

        return door_options
    
    #return print("Ahún no se ha generado nintún tiles_path")


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
    dungeon.tiles[(35, 17)] = tile_types.down_stairs
    dungeon.downstairs_location = (35, 17)

    #import gen_uniques
    #gen_uniques.place_uniques(engine.game_world.current_floor, center_of_last_room, dungeon)

    # Finally, append the new room to the list.
    rooms.append(new_room)
    # rooms.append(new_room2)

    return dungeon