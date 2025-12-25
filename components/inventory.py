from __future__ import annotations

import copy
from collections import defaultdict
from typing import Callable, List, Optional, TYPE_CHECKING, Tuple

import loot_tables

from components.base_component import BaseComponent

if TYPE_CHECKING:
    from components.equipment import Equipment
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
            expanded_items: List[Item] = []
            for entry in items:
                if (
                    isinstance(entry, tuple)
                    and len(entry) == 2
                    and isinstance(entry[1], int)
                ):
                    item, count = entry
                    if count <= 0:
                        continue
                    expanded_items.extend(copy.deepcopy(item) for _ in range(count))
                else:
                    expanded_items.append(entry)
            self.items = expanded_items
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

        owner = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if owner is None or engine is None:
            return
        if owner is engine.player:
            engine.message_log.add_message(f"You throw the {item.name}.")
            return
        if not engine.game_map.visible[owner.x, owner.y]:
            return
        if getattr(item, "projectile_type", None):
            engine.message_log.add_message(f"{owner.name} shoots an {item.name}.")
        else:
            engine.message_log.add_message(f"{owner.name} throws the {item.name}.")

    def reroll_loot(self) -> None:
        """Regenerate loot from the configured table, if any."""
        if not self.loot_table_key:
            return
        rolled_items = loot_tables.build_monster_inventory(
            self.loot_table_key, self.loot_amount
        )
        # Deep copy to ensure each entity gets independent item instances.
        self.items = [copy.deepcopy(item) for item in rolled_items]

    def _display_name(self, item: Item) -> str:
        base_name = item.name
        if getattr(item, "id_name", "") == "Sand bag":
            remaining = getattr(item, "uses", 0)
            max_uses = getattr(item, "max_uses", remaining)
            base_name = f"{base_name} ({remaining}/{max_uses})"
        return base_name

    def get_entries(
        self,
        *,
        equipment: Optional[Equipment] = None,
        filter_fn: Optional[Callable[[Item], bool]] = None,
        skip: Optional[Item] = None,
    ) -> List[Tuple[str, List[Item], bool]]:
        """Return sorted entries for inventory listing, splitting equipped items."""
        if filter_fn is None:
            filter_fn = lambda item: True

        equipped_entries = []
        grouped_items = defaultdict(list)
        entries = []

        for item in self.items:
            if skip and item is skip:
                continue
            if not filter_fn(item):
                continue
            entry_name = self._display_name(item)
            if equipment and equipment.item_is_equipped(item):
                equipped_entries.append((entry_name, [item], True))
            else:
                if getattr(item, "stackable", True):
                    grouped_items[entry_name].append(item)
                else:
                    entries.append((entry_name, [item], False))

        for name, items in grouped_items.items():
            entries.append((name, items, False))

        entries.extend(equipped_entries)
        # Equipados primero, luego alfabéticamente
        entries.sort(key=lambda entry: (0 if entry[2] else 1, entry[0]))
        return entries

    def entry_letter(
        self,
        item: Item,
        *,
        equipment: Optional[Equipment] = None,
        filter_fn: Optional[Callable[[Item], bool]] = None,
        skip: Optional[Item] = None,
    ) -> Optional[str]:
        entries = self.get_entries(equipment=equipment, filter_fn=filter_fn, skip=skip)
        for index, (_, items, _) in enumerate(entries):
            if item in items:
                if 0 <= index < 26:
                    return chr(ord("a") + index)
                return None
        return None
