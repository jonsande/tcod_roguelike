from __future__ import annotations
import copy
import math
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union

from render_order import RenderOrder

if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.consumable import Consumable
    from components.equipment import Equipment
    from components.equippable import Equippable
    from components.fighter import Fighter, Door
    from components.inventory import Inventory
    from components.level import Level
    from game_map import GameMap

T = TypeVar("T", bound="Entity")


class Entity:

    """A generic object to represent players, enemies, items, etc.
    EveryTHING in our world"""

    parent: Union[GameMap, Inventory]

    def __init__(
        self,
        parent: Optional[GameMap] = None,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        blocks_movement: bool = False,
        render_order: RenderOrder = RenderOrder.CORPSE,
        spawn_coord: int = (0, 0),
        generated_item_list: int = [],
        #transparent: int = False,
        #blocks_vision: bool = False,
):

        self.spawn_coord = spawn_coord
        self.generated_item_list = generated_item_list
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
        self.render_order = render_order
        #self.transparent = transparent
        #self.blocks_vision = blocks_vision
        if parent:
            # If parent isn't provided now then it will be set later.
            self.parent = parent
            parent.entities.add(self)


    @property
    def gamemap(self) -> GameMap:
        return self.parent.gamemap


    def spawn(self: T, gamemap: GameMap, x: int, y: int) -> T:
        """Spawn a copy of this instance at the given location."""
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.parent = gamemap
        gamemap.entities.add(clone)
        return clone

    
    def place(self, x: int, y: int, gamemap: Optional[GameMap] = None) -> None:
        """Place this entity at a new location.  Handles moving across GameMaps."""
        self.x = x
        self.y = y
        if gamemap:
            if hasattr(self, "parent"):  # Possibly uninitialized.
                if self.parent is self.gamemap:
                    self.gamemap.entities.remove(self)
            self.parent = gamemap
            gamemap.entities.add(self)


    def distance(self, x: int, y: int) -> float:
        """
        Return the distance between the current entity and the given (x, y) coordinate.
        """
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
    
    def move(self, dx: int, dy: int) -> None:
        # Move the entity by a given amount
        self.x += dx
        self.y += dy

#from actions import PassAction
class Actor(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI],
        equipment: Equipment,
        fighter: Fighter,
        inventory: Inventory,
        level: Level,
        to_eat_drop = None,
        #recover_rate: int,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=True,
            render_order=RenderOrder.ACTOR,
        )

        self.ai_cls = ai_cls
        self.ai: Optional[BaseAI] = ai_cls(self)

        self.equipment: Equipment = equipment
        self.equipment.parent = self

        self.fighter = fighter
        self.fighter.parent = self

        self.inventory = inventory
        self.inventory.parent = self

        self.level = level
        self.level.parent = self
        self.to_eat_drop = to_eat_drop

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this actor can perform actions."""
        return bool(self.ai)
    
    #def pass_turn(self):
    #    return PassAction
    

class Item(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        identified: bool = False,
        id_name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
        throwable: bool = False,
        #powered: Optional[Powered] = None,
        uses: int = 1,
        info: str = "NO INFO"
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            #id_name = id_name,
            blocks_movement=False,
            render_order=RenderOrder.ITEM,
        )

        self.consumable = consumable
        
        if self.consumable:
            self.consumable.parent = self

        self.equippable = equippable

        if self.equippable:
            self.equippable.parent = self

        self.throwable = throwable
        self.identified = identified
        self.id_name = id_name
        self.uses = uses
        self.info = info

    def identify(self):
        # Esto creo que no es necesario
        self.name = self.id_name
        self.identified = True
        
        # ESTO HAY QUE HACERLO CON for obj in set(self.gamemap.items) + ...
        # Identificación automática por consumo:
        # for obj in set(self.gamemap.items):
        #     if isinstance(obj, Item):
        #         # Para que sólo identifique el mismo tipo de item que se consuma:
        #         if obj.id_name == self.id_name:
        #             obj.name = self.id_name
        #         obj.identified = True
        #         self.parent.engine.identified_items.append(self.id_name)

        # Identificación automática por consumo:
        import gc
        from entity import Item
        #self.parent.identified == True
        for obj in gc.get_objects():
            if isinstance(obj, Item):
                # Para que sólo identifique el mismo tipo de item que se consuma:
                if obj.id_name == self.id_name:
                    #import ipdb;ipdb.set_trace()
                    obj.name = self.id_name
                    obj.identified = True





class Decoration(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=False,
            render_order=RenderOrder.DECORATION,
        )


class Obstacle(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI] = None,
        fighter: Door,
        #obstacle: Door,
        level: Level,
        equipment: Equipment,
        inventory: Inventory,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=True,
            render_order=RenderOrder.DECORATION,
        )

        self.ai: Optional[BaseAI] = ai_cls(self)

        #self.obstacle = obstacle
        #self.obstacle.parent = self
        self.fighter = fighter
        self.fighter.parent = self

        self.level = level
        self.level.parent = self

        self.equipment: Equipment = equipment
        self.equipment.parent = self

        self.inventory = inventory
        self.inventory.parent = self

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this actor can perform actions."""
        return bool(self.ai)


