from __future__ import annotations

from typing import List, TYPE_CHECKING

from components.base_component import BaseComponent

if TYPE_CHECKING:
    from entity import Actor, Item


class Inventory(BaseComponent):
    parent: Actor
    """
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items: List[Item] = []
    """
    def __init__(self, capacity: int = 0, items: List[Item] = []):
        self.capacity = capacity
        self.items = items

    def drop(self, item: Item) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at the player's current location.
        """
        self.items.remove(item)
        item.place(self.parent.x, self.parent.y, self.gamemap)

        self.engine.message_log.add_message(f"You dropped the {item.name}.")

    def throw(self, item: Item, x, y) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at certain location.
        """
        self.items.remove(item)
        item.place(x, y, self.gamemap)

        self.engine.message_log.add_message(f"You throw the {item.name}.")