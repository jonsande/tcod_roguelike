from enum import auto, Enum


class RenderOrder(Enum):
    DECORATION = auto()
    OBSTACLE = auto()
    CORPSE = auto()
    #STAIRS = auto()
    ITEM = auto()
    ACTOR = auto()