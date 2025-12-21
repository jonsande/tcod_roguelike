import random

# TODO: deberían poder crearse con objetos estas salas. Donde aparezca 
# el carácter '~' debe generarse un scroll (aleatorio), donde aparezca 
# el caracter '!' debe generarse una poción aleatoria, y donde aparezca 
# el caracter '/' debe aparecer un arma aleatoria. La probabilidad de que 
# aparezca una cosa u otra debe ser configurable, así como la probabilidad 
# de que aparezca un tipo u otro de pócima (si lo que se genera es una pócima), 
# un tipo u otro de pergamino (si lo que se genera es un pergamino), un tipo u otro 
# de arma (si lo que se genera es un arma).

import color

room_01 = (
    "..##..##..##..",
    "..............",
    "..............",
    "..##..##..##..",
)

room_02 = (
    "..............",
    "..............",
    "..#..#..#..#..",
    "..............",
    "..............",
)

room_03 = (
    "..............",
    "..#..#..#..#..",
    "..............",
)

room_04 = (
    ".......",
    ".##+##.",
    ".#...#.",
    ".#...#.",
    ".##+##.",
    ".......",
)

room_05 = (
    "..#..#..#..#..",
    "#+#+##+##+##+#",
    "..............",
    "#+#+##+##+##+#",
    "..#..#..#..#..",
)

room_06 = (
    "..#..#..",
    "#+#..#+#",
    "........",
    "#+#..#+#",
    "..#..#..",
)

room_07 = (
    "#####..#####",
    "##........##",
    "............",
    "............",
    "##........##",
    "#####..#####",
)

# UNIQUE ROOMS

## "E" Entry points (connections)
## "C" Chest
## "M" Mesa
## "@" Personaje
## "+" Por defecto, puerta cerrada ordinaria (sin llave). Para que esté cerrada con llave
## hay que especificarlo en el método apply de cada unique room
## "-" Puerta cerrada ordinaria (sin llave).

## THE STUDY

the_study = (
    "#####",
    "#.@M#",
    "#...#",
    "#+###",
    "#E###",
)

## EL POZO

the_well = (
    "###E###",
    "#.....#",
    "E.. ..E",
    "#.....#",
    "###E###",

)

## EL ÍDOLO

the_idol_room = (
    "###############",
    "####.......####",
    "##...........##",
    "#......I......#",
    "##...........##",
    "####.......####",
    "#######.#######",
    "#######E#######",
)

## LA CÁRCEL

prisioner_vault = [
    (
        "#################",
        "##.@#.@#.@#.@#.@#",
        "###+#+##+##+##+##",
        "E-..............#",
        "###+#+##+##+##+##",
        "##.@#.@#.@#.@#.@#",
        "#################",
    ),
    (
        "#################",
        "#.@#.@#.@#.@#.@##",
        "##+#+##+##+##+###",
        "#..............-E",
        "##+#+##+##+##+###",
        "#.@#.@#.@#.@#.@##",
        "#################",
    ),
    (
        "###E###",
        "###-###",
        "#@#.#@#",
        "#.+.+.#",
        "###.###",
        "#@#.#@#",
        "#.+.+.#",
        "###.###",
        "#@#.#@#",
        "#.+.+.#",
        "###.###",
        "#@#.#@#",
        "#.+.+.#",
        "#######",
    ),
    (
        "#######",
        "#@#.#@#",
        "#.+.+.#",
        "###.###",
        "#@#.#@#",
        "#.+.+.#",
        "###.###",
        "#@#.#@#",
        "#.+.+.#",
        "###.###",
        "#@#.#@#",
        "#.+.+.#",
        "###-###",
        "###E###",
    ), 
]

## LA BODEGA

## LABORATORIO

## BLUE CHEST ROOM

blue_chest_room = (
    "#####E#####",
    "#####+#####",
    "##.......##",
    "#.........#",
    "##.......##",
    "####.C.####",
    "###########",
)

BLUE_CHEST_ROOM_CONTENTS = [
    random.choice(["strength_potion", "life_potion"]),
    "long_sword_plus",
]

class UniqueRoomBase:
    key = ""
    template = ()
    name = ""
    description = None
    key_color = None

    def apply(self, dungeon, room) -> None:
        room.is_unique_room = True
        if self.name:
            dungeon.room_names_by_center[room.center] = self.name
        if self.description:
            dungeon.room_desc_by_center[room.center] = self.description
            dungeon.room_desc_color_by_center[room.center] = color.descend
        if self.key:
            dungeon.unique_room_types.add(self.key)
            tiles = set(getattr(room, "fixed_room_tiles", set()))
            if tiles:
                dungeon.unique_room_tiles_by_type[self.key] = tiles
        if hasattr(dungeon, "unique_room_centers"):
            dungeon.unique_room_centers.add(room.center)


class BlueChestRoom(UniqueRoomBase):
    key = "blue_chest_room"
    template = blue_chest_room
    name = "Blue chest room"
    description = "La cámara se encuentra sellada con extrañas planchas metálicas. Al fondo, en el centro de una cavidad de techo abobedado, hay un cofre decorado con pequeños cristales azules."
    key_color = "blue"
    chest_symbol = "C"
    chest_name = "Blue chest"
    chest_color = (60, 120, 220)
    chest_contents = BLUE_CHEST_ROOM_CONTENTS
    door_symbol = "+"
    door_lock_color = "blue"
    key_min_floor = 4
    key_max_floor = 6

    def apply(self, dungeon, room) -> None:
        super().apply(dungeon, room)
        markers = getattr(room, "fixed_room_markers", {}) or {}
        door_positions = markers.get(self.door_symbol, [])
        if not door_positions:
            door_positions = list(getattr(room, "allowed_door_coords", set()))
        if door_positions:
            import procgen
            for x, y in door_positions:
                procgen.spawn_door_entity(dungeon, x, y, lock_color=self.door_lock_color)
                dungeon.tiles[x, y] = procgen.tile_types.closed_door

        positions = markers.get(self.chest_symbol, [])
        if not positions:
            return
        x, y = positions[0]
        import entity_factories
        import copy

        chest_entity = entity_factories.chest.spawn(dungeon, x, y)
        chest_entity.name = self.chest_name
        chest_entity.id_name = self.chest_name.lower().replace(" ", "_")
        chest_entity.color = self.chest_color
        chest_entity.is_unique_room_chest = True
        items = []
        for item_id in self.chest_contents:
            item_proto = getattr(entity_factories, str(item_id), None)
            if not item_proto:
                continue
            items.append(copy.deepcopy(item_proto))
        if items:
            entity_factories.fill_container_with_items(chest_entity, items)
        entity_factories.maybe_turn_chest_into_mimic(chest_entity)


class PrisionerVault(UniqueRoomBase):
    key = "prisioner_vault"
    template = prisioner_vault
    name = "Prisioner vault"
    description = "No te gusta el aspecto de este lugar."
    key_color = "square"
    door_symbol = "+"
    door_lock_color = "square"
    prisioner_symbol = "@"
    key_min_floor = 4
    key_max_floor = key_min_floor + 3

    def apply(self, dungeon, room) -> None:
        super().apply(dungeon, room)
        markers = getattr(room, "fixed_room_markers", {}) or {}
        door_positions = markers.get(self.door_symbol, [])
        if not door_positions:
            door_positions = list(getattr(room, "allowed_door_coords", set()))
        if door_positions:
            import procgen
            for x, y in door_positions:
                procgen.spawn_door_entity(dungeon, x, y, lock_color=self.door_lock_color)
                dungeon.tiles[x, y] = procgen.tile_types.closed_door

        positions = markers.get(self.prisioner_symbol, [])
        if not positions:
            return
        x, y = random.choice(positions)
        import entity_factories
        entity_factories.prisioner.spawn(dungeon, x, y)


UNIQUE_ROOMS = {
    "blue_chest_room": BlueChestRoom,
    "prisioner_vault": PrisionerVault,
}
