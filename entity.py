from __future__ import annotations
import copy
import math
from typing import Callable, Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union

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
        # Refresh any inventory loot that should be generated per-instance.
        inventory = getattr(clone, "inventory", None)
        reroll_loot = getattr(inventory, "reroll_loot", None)
        if callable(reroll_loot):
            reroll_loot()
        clone.x = x
        clone.y = y
        clone.parent = gamemap
        gamemap.entities.add(clone)
        on_spawn = getattr(clone, "on_spawn", None)
        if callable(on_spawn):
            on_spawn(clone)
        assign_dynamic = getattr(clone, "_assign_dynamic_info", None)
        if callable(assign_dynamic):
            assign_dynamic()
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
        max_uses: Optional[int] = None,
        stackable: bool = True,
        id_info: Optional[str] = None,
        info: str = "NO INFO",
        dynamic_info_factory: Optional[Callable[[], str]] = None,
        projectile_dice: Optional[Tuple[int, int]] = None,
        projectile_bonus: int = 0,
        projectile_type: Optional[str] = None,
        projectile_destroy_chance_on_hit: float = 0.0,
        bundle_range: Optional[Tuple[int, int]] = None,
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
        self.max_uses = uses if max_uses is None else max_uses
        self.stackable = stackable
        self.id_info = id_info
        self.info = info
        self._dynamic_info_factory = dynamic_info_factory
        self._dynamic_info_assigned = False
        self.projectile_dice = projectile_dice
        self.projectile_bonus = projectile_bonus
        self.projectile_type = projectile_type
        self.projectile_destroy_chance_on_hit = projectile_destroy_chance_on_hit
        self.bundle_range = bundle_range

    def _assign_dynamic_info(self) -> None:
        """Generate contextual info once when a factory is provided."""
        if self._dynamic_info_assigned:
            return
        if self._dynamic_info_factory:
            description = self._dynamic_info_factory()
            if description:
                self.info = description
        self._dynamic_info_assigned = True

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

    def _equippable_suffix(self) -> str:
        """Return a dynamic description of bonuses/penalties applied when equipped."""
        equippable = getattr(self, "equippable", None)
        if not equippable:
            return ""
        summary = equippable.describe_modifiers()
        if not summary:
            return ""
        newline = "\n\n"
        return f"Effects when equipped:\n\n{summary.lstrip(newline)}"

    def full_info(self) -> str:
        """Return base info plus a generated summary of equippable effects."""
        self._assign_dynamic_info()
        parts = []
        if self.info:
            parts.append(self.info)
        show_identified_details = self.identified or not getattr(self, "id_info", None)
        if show_identified_details:
            if getattr(self, "id_info", None):
                parts.append(self.id_info)
            suffix = self._equippable_suffix()
            if suffix:
                parts.append(suffix)
        return "\n\n".join(parts) if parts else "NO INFO"

class Book(Item):
    """Consumables or notes that simply reveal their info text when read."""

    def __init__(self, *, info: str = "NO INFO", **kwargs):
        kwargs.setdefault("throwable", True)
        kwargs.setdefault("info", info)
        super().__init__(**kwargs)

    def read_message(self) -> str:
        return self.info


class GeneratedBook(Book):
    """Book that rolls a fresh title and content each time it is copied."""

    def __init__(
        self,
        *,
        title_fn: Callable[[], str],
        content_fn: Callable[[], str],
        **kwargs,
    ):
        self._title_fn = title_fn
        self._content_fn = content_fn
        kwargs.setdefault("name", title_fn())
        kwargs.setdefault("id_name", "Book")
        kwargs.setdefault("info", content_fn())
        kwargs.setdefault("stackable", False)
        super().__init__(**kwargs)

    def __deepcopy__(self, memo):
        """Create a new generated book with a fresh title and content."""
        return GeneratedBook(
            title_fn=self._title_fn,
            content_fn=self._content_fn,
            char=self.char,
            color=self.color,
            id_name=self.id_name,
        )


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
        render_order: RenderOrder = RenderOrder.OBSTACLE,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=True,
            render_order=render_order,
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


class Chest(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "C",
        open_char: str = "c",
        color: Tuple[int, int, int] = (184, 134, 11),
        name: str = "Chest",
        inventory: Optional["Inventory"] = None,
        is_open: bool = False,
    ):
        if inventory is None:
            from components.inventory import Inventory as _Inventory

            inventory = _Inventory(capacity=0, items=[])

        super().__init__(
            x=x,
            y=y,
            char=open_char if is_open else char,
            color=color,
            name=name,
            blocks_movement=True,
            render_order=RenderOrder.ITEM,
        )
        self.closed_char = char
        self.open_char = open_char
        self.is_open = is_open
        self.inventory = inventory
        self.inventory.parent = self

    def open(self) -> bool:
        if self.is_open:
            return False
        self.is_open = True
        self.char = self.open_char
        self.name = "Open chest"
        return True

    def close(self) -> bool:
        if not self.is_open:
            return False
        self.is_open = False
        self.char = self.closed_char
        self.name = "Chest"
        return True

    def add_item(self, item: Item) -> None:
        """Add an item to the chest inventory."""
        self.inventory.items.append(item)
        item.parent = self.inventory


class TableContainer(Chest):
    """Container that looks like a table and can hold items."""

    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "#",
        open_char: str = "#",
        color: Tuple[int, int, int] = (100, 100, 100),
        name: str = "Table",
        inventory: Optional["Inventory"] = None,
        is_open: bool = False,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            open_char=open_char,
            color=color,
            name=name,
            inventory=inventory,
            is_open=is_open,
        )
        self.id_name = "table"

    def open(self) -> bool:
        if self.is_open:
            return False
        self.is_open = True
        self.char = self.open_char
        # El nombre permanece como "Table" para los mensajes.
        return True


class BookShelfContainer(Chest):
    """Container that represents a bookshelf and can hold items."""

    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "π",
        open_char: str = "π",
        color: Tuple[int, int, int] = (120, 90, 60),
        name: str = "Bookshelf",
        inventory: Optional["Inventory"] = None,
        is_open: bool = False,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            open_char=open_char,
            color=color,
            name=name,
            inventory=inventory,
            is_open=is_open,
        )
        self.id_name = "bookshelf"

    def open(self) -> bool:
        if self.is_open:
            return False
        self.is_open = True
        self.char = self.open_char
        return True
