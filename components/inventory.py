from __future__ import annotations

import copy
from typing import List, Optional, TYPE_CHECKING

import loot_tables

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
    def __init__(
        self,
        capacity: int = 0,
        items: Optional[List[Item]] = None,
        loot_table_key: Optional[str] = None,
        loot_amount: int = 0,
    ):
        self.capacity = capacity
        self.items: List[Item] = []
        self.loot_table_key = loot_table_key
        self.loot_amount = loot_amount

        if items is not None:
            # Copy the provided list so inventories don't accidentally share references.
            self.items = list(items)
        elif self.loot_table_key:
            # Pre-roll loot for blueprints; actual instances re-roll on spawn.
            self.reroll_loot()

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

    def reroll_loot(self) -> None:
        """Regenerate loot from the configured table, if any."""
        if not self.loot_table_key:
            return
        rolled_items = loot_tables.build_monster_inventory(
            self.loot_table_key, self.loot_amount
        )
        # Deep copy to ensure each entity gets independent item instances.
        self.items = [copy.deepcopy(item) for item in rolled_items]
