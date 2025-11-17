from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType

if TYPE_CHECKING:
    from entity import Item

import random


class Equippable(BaseComponent):
    parent: Item

    def __init__(
        self,
        equipment_type: EquipmentType,
        power_bonus: int = 0,
        defense_bonus: int = 0,
        stealth_bonus: int = 0,
        stealth_penalty: int = 0,
        to_hit_bonus: int = 0,
        to_hit_penalty: int = 0,
        armor_value_bonus: int = 0,
    ):
        self.equipment_type = equipment_type

        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.stealth_bonus = stealth_bonus
        self.stealth_penalty = stealth_penalty
        self.to_hit_bonus = to_hit_bonus
        self.to_hit_penalty = to_hit_penalty
        self.armor_value_bonus = armor_value_bonus

#class Powered(BaseComponent):
#    parent: Item
#    
#    def __init__(self) -> None:
#        super().__init__()

"""
from input_handlers import SingleRangedAttackHandler
import color
import actions
from exceptions import Impossible
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from entity import Actorclass LeatherArmor(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.ARMOR, 
            power_bonus=0, 
            defense_bonus=0, 
            stealth_bonus=0,
            stealth_penalty=1,
            to_hit_bonus=0,
            to_hit_penalty=1,
            armor_value_bonus=1,
        )
class RangedEquipable(BaseComponent):
    parent: Item
    
    def __init__(self, damage: int, maximum_range: int):
        self.damage = damage
        self.maximum_range = maximum_range

    def get_action(self, consumer: Actor) -> SingleRangedAttackHandler:
        self.engine.message_log.add_message(
            "Select a target location.", color.needs_target
        )
        return SingleRangedAttackHandler(
            self.engine,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        target = None
        closest_distance = self.maximum_range + 1.0

        for actor in self.engine.game_map.actors:
            if actor is not consumer and self.parent.gamemap.visible[actor.x, actor.y]:
                distance = consumer.distance(actor.x, actor.y)

                if distance < closest_distance:
                    target = actor
                    closest_distance = distance

        if target:
            self.engine.message_log.add_message(
                f"You shoot {target.name} with a loud thunder, for {self.damage} damage!"
            )
            target.fighter.take_damage(self.damage)
            #self.consume()
            #self.parent.identify()
        else:
            #self.parent.identify()
            raise Impossible("No enemy is close enough to Fire.")

class Revolver(RangedEquipable):
    def __init__(self, damage: int, maximum_range: int, ammo: int):
        self.damage = damage
        self.maximum_range = maximum_range
        self.ammo = ammo
        
        #super().__init__(equipment_type=EquipmentType.RANGEDWEAPON)
"""

class Dagger(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=3, stealth_bonus=1, to_hit_bonus=1)

class DaggerPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            power_bonus=3+random.randint(1,3), 
            stealth_bonus=1, 
            to_hit_bonus=1,
            )
        


class ShortSword(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=4, to_hit_bonus=1)


class ShortSwordPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=4+random.randint(1, 3), to_hit_bonus=1)


class LongSword(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=5, stealth_penalty=1, to_hit_penalty=0)


class LongSwordPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=5+random.randint(1, 3), stealth_penalty=1, to_hit_penalty=0)


class Spear(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=5, to_hit_bonus=1)


class SpearPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=5+random.randint(1, 3), to_hit_bonus=1)


class LeatherArmor(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.ARMOR, 
            power_bonus=0, 
            defense_bonus=0, 
            stealth_bonus=0,
            stealth_penalty=1,
            to_hit_bonus=0,
            to_hit_penalty=1,
            armor_value_bonus=1,
        )
        #self.parent.info=f"Stealth Penalty: {self.stealth_penalty}",
        #super().__init__(equipment_type=EquipmentType.ARMOR, armor_value_bonus=1, stealth_penalty=1, to_hit_penalty=1)

class ChainMail(Equippable):
    def __init__(self) -> None:
        #super().__init__(equipment_type=EquipmentType.ARMOR, armor_value_bonus=3, stealth_penalty=3)
        super().__init__(equipment_type=EquipmentType.ARMOR, armor_value_bonus=5, stealth_penalty=3, to_hit_penalty=3)


class Grial(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARTEFACT, defense_bonus=3, to_hit_bonus=2)
        #self.parent.identify()

class GoblinAmulet(Equippable):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARTEFACT, defense_bonus=4, stealth_bonus=4, to_hit_penalty=6)
        #self.parent.identify()