# TODO: deberían poder crearse con objetos estas salas. Donde aparezca 
# el carácter '~' debe generarse un scroll (aleatorio), donde aparezca 
# el caracter '!' debe generarse una poción aleatoria, y donde aparezca 
# el caracter '/' debe aparecer un arma aleatoria. La probabilidad de que 
# aparezca una cosa u otra debe ser configurable, así como la probabilidad 
# de que aparezca un tipo u otro de pócima (si lo que se genera es una pócima), 
# un tipo u otro de pergamino (si lo que se genera es un pergamino), un tipo u otro 
# de arma (si lo que se genera es un arma).

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
    "#####..#####",
    "##........##",
    "............",
    "............",
    "##........##",
    "#####..#####",
    "#####..#####",
)

# UNIQUE ROOMS

## BLUE CHEST ROOM
## "E" Entry points (connections)
## "C" Chest
## "+" Door

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
    "health_potion",
    "health_potion",
    "power_potion",
]

class UniqueRoomBase:
    key = ""
    template = ()
    name = ""
    description = None

    def apply(self, dungeon, room) -> None:
        if self.name:
            dungeon.room_names_by_center[room.center] = self.name
        if self.description:
            dungeon.room_desc_by_center[room.center] = self.description


class BlueChestRoom(UniqueRoomBase):
    key = "blue_chest_room"
    template = blue_chest_room
    name = "Blue chest room"
    description = "Un cofre azul destaca en el centro, rodeado de muros sellados."
    chest_symbol = "C"
    chest_name = "Blue chest"
    chest_color = (60, 120, 220)
    chest_contents = BLUE_CHEST_ROOM_CONTENTS

    def apply(self, dungeon, room) -> None:
        super().apply(dungeon, room)
        markers = getattr(room, "fixed_room_markers", {}) or {}
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
        items = []
        for item_id in self.chest_contents:
            item_proto = getattr(entity_factories, str(item_id), None)
            if not item_proto:
                continue
            items.append(copy.deepcopy(item_proto))
        if items:
            entity_factories.fill_container_with_items(chest_entity, items)


UNIQUE_ROOMS = {
    "blue_chest_room": BlueChestRoom,
}
