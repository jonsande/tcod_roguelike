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
        equipment_type: EquipmentType, # Actualmente weapon, armor, artifact, pero aquí podrían añadirse tipos más específicos, como MeleeWeapon, etc.
        min_dmg: int = 0,
        max_dmg: int = 0,
        dmg_bonus: int = 0,
        defense_bonus: int = 0,
        stealth_bonus: int = 0,
        stealth_penalty: int = 0,
        to_hit_bonus: int = 0,
        to_hit_penalty: int = 0,
        armor_value_bonus: int = 0,
    ):
        self.equipment_type = equipment_type

        #self.weapon_dmg = weapon_dmg # Ahora esto es una propiedad.
        self.min_dmg = min_dmg
        self.max_dmg = max_dmg
        self.dmg_bonus = dmg_bonus
        self.defense_bonus = defense_bonus
        self.stealth_bonus = stealth_bonus
        self.stealth_penalty = stealth_penalty
        self.to_hit_bonus = to_hit_bonus
        self.to_hit_penalty = to_hit_penalty
        self.armor_value_bonus = armor_value_bonus
    
    @property
    def weapon_dmg_dice(self) -> int:
        if self.min_dmg == 0 and self.max_dmg == 0:
            return 0
        else:
            return random.randint(self.min_dmg, self.max_dmg)

    @property
    def weapon_dmg_dice_info(self) -> str:
        output = f"1d{self.max_dmg}"
        return output
    
    @property
    def weapon_dmg_bonus(self) -> int:
        return self.dmg_bonus
    
    @property
    def weapon_dmg_total(self) -> int:
        return self.weapon_dmg_dice + self.dmg_bonus
        
    @property
    def weapon_dmg_total_info(self) -> str:
        if self.damage_bonus == 0:
            output = f"1d{self.max_dmg}"
        else:
            output = f"1d{self.max_dmg}+{self.dmg_bonus}"
        return output


class Dagger(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=4,
            dmg_bonus=0,
            defense_bonus=1,
            stealth_bonus=1, 
            to_hit_bonus=1,
            )

class DaggerPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=4,
            dmg_bonus=2,
            defense_bonus=1,
            stealth_bonus=1, 
            to_hit_bonus=2,
            )
        
class ShortSword(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=6,
            dmg_bonus=0,
            defense_bonus=1,
            stealth_bonus=0, 
            to_hit_bonus=1,
            )


class ShortSwordPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=6,
            dmg_bonus=2,
            defense_bonus=1,
            stealth_bonus=0, 
            to_hit_bonus=2,
            )


class LongSword(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=8,
            dmg_bonus=0,
            defense_bonus=1,
            stealth_penalty=1, 
            )


class LongSwordPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=8,
            dmg_bonus=2,
            defense_bonus=1,
            stealth_penalty=0, 
            )


class Spear(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=8,
            dmg_bonus=0,
            defense_bonus=2,
            to_hit_bonus=1,
            )


class SpearPlus(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.WEAPON, 
            min_dmg=1, 
            max_dmg=8,
            dmg_bonus=2,
            defense_bonus=2,
            to_hit_bonus=2,
            )


class LeatherArmor(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.ARMOR, 
            dmg_bonus = 0, 
            defense_bonus=-1,
            stealth_bonus=0,
            stealth_penalty=1,
            to_hit_bonus=0,
            to_hit_penalty=0,
            armor_value_bonus=2,
        )
        #self.parent.info=f"Stealth Penalty: {self.stealth_penalty}",
        #super().__init__(equipment_type=EquipmentType.ARMOR, armor_value_bonus=1, stealth_penalty=1, to_hit_penalty=1)

class ChainMail(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.ARMOR, 
            armor_value_bonus=5,
            defense_bonus=-2,
            stealth_penalty=3,
            to_hit_penalty=2,
            )

class Grial(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.ARTIFACT, 
            defense_bonus=3, 
            to_hit_bonus=2
            )
        #self.parent.identify()

class GoblinAmulet(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.ARTIFACT, 
            defense_bonus=4, 
            stealth_bonus=4, 
            to_hit_penalty=6
            )
        #self.parent.identify()


class PlainRing(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class AccuracyRing(Equippable):
    def __init__(self) -> None:
        super().__init__(
            equipment_type=EquipmentType.RING,
            to_hit_bonus=1,
        )
