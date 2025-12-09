# módulo dedicado a gestionar el equipo que lleva un actor (jugador o NPCs).

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType
import color

if TYPE_CHECKING:
    from entity import Actor, Item

# CUIDADO! No es lo mismo la clase Equippable que la clase Equipment.
# Equippable es un componente que tienen los ítems que pueden ser equipados.
# Equipment es un componente que tienen los actores (jugador, NPCs) que pueden equipar ítems.
class Equipment(BaseComponent):
    parent: Actor

    def __init__(
        self,
        weapon: Optional[Item] = None,
        armor: Optional[Item] = None,
        artifact: Optional[Item] = None,
        ring_left: Optional[Item] = None,
        ring_right: Optional[Item] = None,
        head_armor: Optional[Item] = None,
        has_head_slot: bool = False,
        cloak: Optional[Item] = None,
        has_cloak_slot: bool = False,
    ):
        self.weapon = weapon
        self.armor = armor
        self.artifact = artifact
        self.ring_left = ring_left
        self.ring_right = ring_right
        self.has_head_slot = has_head_slot
        self.head_armor = head_armor if has_head_slot else None
        self.has_cloak_slot = has_cloak_slot
        self.cloak = cloak if has_cloak_slot else None

    def __setstate__(self, state):
        """Ensure new slots exist when loading older save files."""
        self.__dict__.update(state)
        self.__dict__.setdefault("has_cloak_slot", False)
        self.__dict__.setdefault("cloak", None)

    def _equipped_equippables(self):
        return [
            item.equippable
            for item in (
                self.weapon,
                self.armor,
                self.head_armor,
                self.cloak,
                self.artifact,
                self.ring_left,
                self.ring_right,
            )
            if item is not None and item.equippable is not None
        ]

    def _sum_bonus(self, attribute: str) -> int:
        return sum(getattr(eq, attribute, 0) for eq in self._equipped_equippables())

    def equipped_items(self):
        """Return a list of all currently equipped item instances."""
        return [
            item
            for item in (
                self.weapon,
                self.armor,
                self.head_armor,
                self.cloak,
                self.artifact,
                self.ring_left,
                self.ring_right,
            )
            if item is not None
        ]

    def _is_cursed(self, item: Optional[Item]) -> bool:
        eq = getattr(item, "equippable", None)
        return bool(eq and getattr(eq, "cursed", False))

    def _cannot_remove_cursed(self, item: Optional[Item], add_message: bool) -> bool:
        if not self._is_cursed(item):
            return False
        if add_message and item:
            self.parent.gamemap.engine.message_log.add_message(
                f"The {item.name} is cursed! You cannot remove it.",
                color.impossible,
            )
        return True

    @property
    def defense_bonus(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.defense_bonus

        if self.armor is not None and self.armor.equippable is not None:
            bonus += self.armor.equippable.defense_bonus

        if self.head_armor is not None and self.head_armor.equippable is not None:
            bonus += self.head_armor.equippable.defense_bonus

        if self.cloak is not None and self.cloak.equippable is not None:
            bonus += self.cloak.equippable.defense_bonus

        if self.artifact is not None and self.artifact.equippable is not None:
            bonus += self.artifact.equippable.defense_bonus

        if self.ring_left is not None and self.ring_left.equippable is not None:
            bonus += self.ring_left.equippable.defense_bonus

        if self.ring_right is not None and self.ring_right.equippable is not None:
            bonus += self.ring_right.equippable.defense_bonus

        return bonus

    # La propiedad total_equipment_dmg_bonus suma el bonus al daño de todas las piezas equipadas 
    # que hagan daño o aporten un bonus al daño.
    @property
    def total_equipment_dmg_bonus(self) -> int:
        total = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            #total += self.weapon.equippable.weapon_dmg
            total += self.weapon.equippable.dmg_bonus

        if self.armor is not None and self.armor.equippable is not None:
            # total += self.armor.equippable.weapon_dmg
            total += self.armor.equippable.dmg_bonus

        if self.head_armor is not None and self.head_armor.equippable is not None:
            total += self.head_armor.equippable.dmg_bonus

        if self.cloak is not None and self.cloak.equippable is not None:
            total += self.cloak.equippable.dmg_bonus

        if self.artifact is not None and self.artifact.equippable is not None:
            #total += self.artifact.equippable.weapon_dmg
            total += self.artifact.equippable.dmg_bonus

        if self.ring_left is not None and self.ring_left.equippable is not None:
            total += self.ring_left.equippable.dmg_bonus

        if self.ring_right is not None and self.ring_right.equippable is not None:
            total += self.ring_right.equippable.dmg_bonus

        return total
    
    @property
    def non_weapon_dmg_bonus(self) -> int:
        bonus = 0

        if self.armor is not None and self.armor.equippable is not None:
            bonus += self.armor.equippable.dmg_bonus

        if self.head_armor is not None and self.head_armor.equippable is not None:
            bonus += self.head_armor.equippable.dmg_bonus

        if self.cloak is not None and self.cloak.equippable is not None:
            bonus += self.cloak.equippable.dmg_bonus

        if self.artifact is not None and self.artifact.equippable is not None:
            bonus += self.artifact.equippable.dmg_bonus

        if self.ring_left is not None and self.ring_left.equippable is not None:
            bonus += self.ring_left.equippable.dmg_bonus

        if self.ring_right is not None and self.ring_right.equippable is not None:
            bonus += self.ring_right.equippable.dmg_bonus

        return bonus

    @property
    def stealth_bonus(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.stealth_bonus

        if self.armor is not None and self.armor.equippable is not None:
            bonus += self.armor.equippable.stealth_bonus

        if self.head_armor is not None and self.head_armor.equippable is not None:
            bonus += self.head_armor.equippable.stealth_bonus

        if self.cloak is not None and self.cloak.equippable is not None:
            bonus += self.cloak.equippable.stealth_bonus

        if self.artifact is not None and self.artifact.equippable is not None:
            bonus += self.artifact.equippable.stealth_bonus

        if self.ring_left is not None and self.ring_left.equippable is not None:
            bonus += self.ring_left.equippable.stealth_bonus

        if self.ring_right is not None and self.ring_right.equippable is not None:
            bonus += self.ring_right.equippable.stealth_bonus

        return bonus
    
    @property
    def stealth_penalty(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            #bonus += self.weapon.equippable.stealth_penalty
            bonus += self.weapon.equippable.armor_value_bonus

        if self.armor is not None and self.armor.equippable is not None:
            #bonus += self.armor.equippable.stealth_penalty
            bonus += self.armor.equippable.armor_value_bonus

        if self.head_armor is not None and self.head_armor.equippable is not None:
            bonus += self.head_armor.equippable.armor_value_bonus

        if self.cloak is not None and self.cloak.equippable is not None:
            bonus += self.cloak.equippable.armor_value_bonus

        if self.artifact is not None and self.artifact.equippable is not None:
            bonus += self.artifact.equippable.armor_value_bonus

        if self.ring_left is not None and self.ring_left.equippable is not None:
            bonus += self.ring_left.equippable.armor_value_bonus

        if self.ring_right is not None and self.ring_right.equippable is not None:
            bonus += self.ring_right.equippable.armor_value_bonus

        return bonus
    
    @property
    def to_hit_bonus(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.to_hit_bonus

        if self.armor is not None and self.armor.equippable is not None:
            bonus += self.armor.equippable.to_hit_bonus

        if self.head_armor is not None and self.head_armor.equippable is not None:
            bonus += self.head_armor.equippable.to_hit_bonus

        if self.cloak is not None and self.cloak.equippable is not None:
            bonus += self.cloak.equippable.to_hit_bonus

        if self.artifact is not None and self.artifact.equippable is not None:
            bonus += self.artifact.equippable.to_hit_bonus

        if self.ring_left is not None and self.ring_left.equippable is not None:
            bonus += self.ring_left.equippable.to_hit_bonus

        if self.ring_right is not None and self.ring_right.equippable is not None:
            bonus += self.ring_right.equippable.to_hit_bonus

        return bonus
    
    @property
    def to_hit_penalty(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.to_hit_penalty
            #bonus += 1

        if self.armor is not None and self.armor.equippable is not None:
            #bonus += self.weapon.equippable.to_hit_penalty
            bonus += self.armor.equippable.to_hit_penalty
            #bonus += 1 

        if self.head_armor is not None and self.head_armor.equippable is not None:
            bonus += self.head_armor.equippable.to_hit_penalty

        if self.cloak is not None and self.cloak.equippable is not None:
            bonus += self.cloak.equippable.to_hit_penalty

        if self.artifact is not None and self.artifact.equippable is not None:
            bonus += self.artifact.equippable.to_hit_penalty

        if self.ring_left is not None and self.ring_left.equippable is not None:
            bonus += self.ring_left.equippable.to_hit_penalty

        if self.ring_right is not None and self.ring_right.equippable is not None:
            bonus += self.ring_right.equippable.to_hit_penalty

        return bonus
    
    @property
    def armor_value_bonus(self) -> int:
        bonus = 0

        if self.armor is not None and self.armor.equippable is not None:
            bonus += self.armor.equippable.armor_value_bonus

        if self.head_armor is not None and self.head_armor.equippable is not None:
            bonus += self.head_armor.equippable.armor_value_bonus

        if self.cloak is not None and self.cloak.equippable is not None:
            bonus += self.cloak.equippable.armor_value_bonus

        if self.artifact is not None and self.artifact.equippable is not None:
            bonus += self.artifact.equippable.armor_value_bonus

        if self.ring_left is not None and self.ring_left.equippable is not None:
            bonus += self.ring_left.equippable.armor_value_bonus

        if self.ring_right is not None and self.ring_right.equippable is not None:
            bonus += self.ring_right.equippable.armor_value_bonus

        return bonus

    @property
    def strength_bonus(self) -> int:
        return self._sum_bonus("strength_bonus")

    @property
    def fov_bonus(self) -> int:
        return self._sum_bonus("fov_bonus")

    @property
    def max_stamina_bonus(self) -> int:
        return self._sum_bonus("max_stamina_bonus")

    @property
    def poison_resistance_bonus(self) -> int:
        return self._sum_bonus("poison_resistance_bonus")

    @property
    def super_memory_bonus(self) -> bool:
        return any(getattr(eq, "super_memory_bonus", False) for eq in self._equipped_equippables())

    @property
    def recover_rate_bonus(self) -> int:
        return self._sum_bonus("recover_rate_bonus")

    @property
    def base_defense_bonus(self) -> int:
        return self._sum_bonus("base_defense_bonus")

    @property
    def luck_bonus(self) -> int:
        return self._sum_bonus("luck_bonus")

    def item_is_equipped(self, item: Item) -> bool:
        return (
            self.weapon == item
            or self.armor == item
            or self.head_armor == item
            or self.cloak == item
            or self.artifact == item
            or self.ring_left == item
            or self.ring_right == item
        )

    def unequip_message(self, item_name: str) -> None:
        self.parent.gamemap.engine.message_log.add_message(
            f"You remove the {item_name}.", color.orange
        )

    def equip_message(self, item_name: str) -> None:
        self.parent.gamemap.engine.message_log.add_message(
            f"You equip the {item_name}."
        )

    def equip_to_slot(self, slot: str, item: Item, add_message: bool) -> None:
        current_item = getattr(self, slot)

        if current_item is not None:
            self.unequip_from_slot(slot, add_message)

        setattr(self, slot, item)

        if add_message:
            self.equip_message(item.name)

    def unequip_from_slot(self, slot: str, add_message: bool) -> None:
        current_item = getattr(self, slot)

        if self._cannot_remove_cursed(current_item, add_message):
            return

        if add_message:
            self.unequip_message(current_item.name)

        setattr(self, slot, None)

    def toggle_equip(self, equippable_item: Item, add_message: bool = True) -> None:
        if (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.WEAPON
        ):
            slot = "weapon"
            identify_on_equip = False
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.HEADARMOR
        ):
            if not self.has_head_slot:
                if add_message:
                    self.parent.gamemap.engine.message_log.add_message(
                        "You cannot wear helmets.",
                        color.impossible,
                    )
                return
            slot = "head_armor"
            identify_on_equip = False
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.CLOAK
        ):
            if not self.has_cloak_slot:
                if add_message:
                    self.parent.gamemap.engine.message_log.add_message(
                        "You cannot wear cloaks.",
                        color.impossible,
                    )
                return
            slot = "cloak"
            identify_on_equip = False
        else:
            if (
                equippable_item.equippable
                and equippable_item.equippable.equipment_type == EquipmentType.ARTIFACT
            ):
                
                slot = "artifact"
                identify_on_equip = False

            else:
                if (
                    equippable_item.equippable
                    and equippable_item.equippable.equipment_type == EquipmentType.RING
                ):
                    identify_on_equip = True
                    if self.ring_left == equippable_item:
                        slot = "ring_left"
                    elif self.ring_right == equippable_item:
                        slot = "ring_right"
                    elif self.ring_left is None:
                        slot = "ring_left"
                    elif self.ring_right is None:
                        slot = "ring_right"
                    else:
                        if add_message:
                            self.parent.gamemap.engine.message_log.add_message(
                                "You are already wearing two rings.",
                                color.impossible,
                            )
                        return
                else:
                    slot = "armor"
                    identify_on_equip = False

        if getattr(self, slot) == equippable_item:
            self.unequip_from_slot(slot, add_message)
        else:
            if identify_on_equip and not equippable_item.identified:
                equippable_item.identify()
            if self._cannot_remove_cursed(getattr(self, slot), add_message):
                return
            self.equip_to_slot(slot, equippable_item, add_message)
        fighter = getattr(self.parent, "fighter", None)
        if fighter:
            fighter.on_equipment_changed()
