from enum import auto, Enum

# Más abajo en la lista, más arriba en el renderizado
class RenderOrder(Enum):
    DECORATION = auto()
    OBSTACLE = auto()
    CORPSE = auto()
    DOOR = auto()
    #STAIRS = auto()
    ITEM = auto()
    ACTOR = auto()
