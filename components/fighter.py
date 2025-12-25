from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
import copy
import random
import numpy as np
from i18n import _
from tcod import constants
from tcod.map import compute_fov

import color
from components.base_component import BaseComponent
from render_order import RenderOrder
import tile_types
import loot_tables
import settings
from settings import DEBUG_MODE, PLAYER_DEFENSE_MISS_THRESHOLD
from audio import (
    update_campfire_audio,
    play_pain_sound,
    play_death_sound,
    play_breakable_wall_destroy_sound,
    play_table_destroy_sound,
)

if TYPE_CHECKING:
    from entity import Actor, Obstacle, Item


def _play_sound_if_audible(
    engine,
    callback,
    *args,
    source=None,
    level: int = 1,
    position=None,
    force: bool = False,
    **kwargs,
) -> None:
    if callback is None:
        return
    if engine:
        engine.play_sound_effect(
            callback,
            *args,
            source=source,
            level=level,
            position=position,
            force=force,
            **kwargs,
        )
    else:
        callback(*args, **kwargs)

x = 0

# ESTO NO SÉ SI TIENE ALGUNA UTILIDAD AHORA MISMO (pero creo que no):
turns = 0
gainance = 0


class NaturalWeapon:
    """Simple helper that describes a creature's natural attack."""

    def __init__(
        self,
        name: str,
        min_dmg: int,
        max_dmg: int,
        dmg_bonus: int = 0,
        critical_multiplier: float = 2.0,
    ):
        self.name = name
        self.min_dmg = min_dmg
        self.max_dmg = max_dmg
        self.dmg_bonus = dmg_bonus
        self.critical_multiplier = critical_multiplier

    @property
    def weapon_dmg_dice(self) -> int:
        if self.min_dmg == 0 and self.max_dmg == 0:
            return 0
        return random.randint(self.min_dmg, self.max_dmg)

    @property
    def weapon_dmg_dice_info(self) -> str:
        if self.max_dmg == 0:
            return "0"
        return f"1d{self.max_dmg}"

    @property
    def weapon_dmg_bonus(self) -> int:
        return self.dmg_bonus


class FireStatusMixin:
    """Shared fire-damage logic for any component that can burn."""

    def _init_fire_status(self, fire_resistance: int = 1):
        self.fire_resistance = fire_resistance
        self.is_burning = False
        self.burning_damage = 0

    def apply_fire_damage(self, amount: int, ignite_chance: float = 0.5) -> None:
        damage = max(0, amount)
        if damage <= 0:
            return
        self.take_damage(damage)
        if getattr(self, "hp", 0) <= 0:
            self._extinguish_fire(silent=True)
            return
        chance = ignite_chance if ignite_chance is not None else 0.5
        if random.random() < chance:
            self._ignite(damage)

    def _ignite(self, base_damage: int) -> None:
        next_damage = base_damage - getattr(self, "fire_resistance", 1)
        if next_damage <= 0:
            return
        if getattr(self, "is_burning", False):
            self.burning_damage = max(self.burning_damage, next_damage)
            return
        self.is_burning = True
        self.burning_damage = next_damage
        self._fire_message(
            "You are engulfed in flames!",
            "{name} is engulfed in flames!",
            player_color=color.red,
            creature_color=color.status_effect_applied,
        )

    def update_fire(self) -> None:
        if not getattr(self, "is_burning", False):
            return
        damage = self.burning_damage
        if damage <= 0:
            self._extinguish_fire()
            return
        self._fire_tick_message(damage)
        self.take_damage(damage)
        if getattr(self, "hp", 0) <= 0:
            self._extinguish_fire(silent=True)
            return
        next_damage = damage - getattr(self, "fire_resistance", 1)
        self.burning_damage = next_damage
        if next_damage <= 0:
            self._extinguish_fire()

    def _extinguish_fire(self, silent: bool = False) -> None:
        was_burning = getattr(self, "is_burning", False)
        self.is_burning = False
        self.burning_damage = 0
        if not was_burning or silent:
            return
        self._fire_message(
            "The flames around you go out.",
            "The flames around {name} go out.",
            player_color=color.orange,
            creature_color=color.orange,
        )

    def _fire_message(
        self,
        player_text: str,
        creature_text: str,
        player_color: Tuple[int, int, int] = color.orange,
        creature_color: Tuple[int, int, int] = color.orange,
    ) -> None:
        entity = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not entity or not engine:
            return
        if entity is engine.player:
            engine.message_log.add_message(player_text, player_color)
            return
        try:
            visible = engine.game_map.visible[entity.x, entity.y]
        except Exception:
            visible = False
        if visible:
            engine.message_log.add_message(
                creature_text.format(name=entity.name),
                creature_color,
            )

    def _fire_tick_message(self, damage: int) -> None:
        entity = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not entity or not engine:
            return
        msg = "{name} is scorched for {damage} fire damage!"
        target_name = "You" if entity is engine.player else entity.name
        if entity is engine.player:
            engine.message_log.add_message(
                f"You take {damage} fire damage!",
                color.red,
            )
        else:
            try:
                visible = engine.game_map.visible[entity.x, entity.y]
            except Exception:
                visible = False
            if visible:
                engine.message_log.add_message(
                    msg.format(name=entity.name, damage=damage),
                    color.red,
                )

    def tick_recovery(self) -> None:
        """Passive HP regen helper; safe default for non-healing components."""
        recover_rate = getattr(self, "recover_rate", 0) or 0
        recover_amount = getattr(self, "recover_amount", 0) or 0
        if recover_rate <= 0 or recover_amount <= 0:
            return
        max_hp = getattr(self, "max_hp", None)
        hp = getattr(self, "hp", None)
        if max_hp is None or hp is None:
            return
        if hp >= max_hp:
            setattr(self, "_recover_counter", recover_rate)
            return
        counter = getattr(self, "_recover_counter", recover_rate)
        counter -= 1
        if counter > 0:
            setattr(self, "_recover_counter", counter)
            return
        setattr(self, "_recover_counter", recover_rate)
        new_hp_value = min(max_hp, hp + recover_amount)
        amount_recovered = new_hp_value - hp
        try:
            self.hp = new_hp_value
        except Exception:
            setattr(self, "_hp", new_hp_value)
        self._maybe_show_slime_regen(amount_recovered)

    def _maybe_show_slime_regen(self, amount_recovered: int) -> None:
        """If this entity is a visible slime, announce its regeneration."""
        if amount_recovered <= 0:
            return
        entity = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not entity or not engine:
            return
        if not getattr(self, "is_slime", False):
            return
        try:
            visible = engine.game_map.visible[entity.x, entity.y]
        except Exception:
            visible = False
        if visible:
            engine.message_log.add_message("The slime regenerates!", color.orange)

from components.ai import HostileEnemyV3
class Fighter(FireStatusMixin, BaseComponent):

    parent: Actor

    def __init__(
        self,
        hp: int,
        base_defense: int,
        strength: int,
        recover_rate: int = 50,
        recover_amount: int = 1,
        fov: int = 0,
        foh: int = 6,
        perception: int = 3,
        weapon_proficiency: float = 1.0,
        base_stealth: int = 0,
        aggressivity: int = 0,
        wait_counter: int = 0,
        base_to_hit: int = 0,
        #max_to_hit: int = 6,
        base_armor_value: int = 0,
        temporal_effects: bool = False,
        luck: int = 0,
        critical_chance: float = 0.015,
        satiety: int = 32,
        max_satiety: int = 32,
        stamina: int = 3,
        max_stamina: int = 3,
        is_in_melee: bool = False,
        defending: bool = False,
        to_hit_counter: int = 0,
        to_power_counter: int = 0,
        to_defense_couter: int = 0,
        #energy_points: int = 10,
        #current_energy_points: int = 10,
        current_time_points: int = 10,
        action_time_cost: int = 10,
        can_fortify: bool = False,
        fortified: bool = False,
        woke_ai_cls=HostileEnemyV3,
        poisons_on_hit: bool = False,
        poisonous: int = 0,
        is_poisoned: bool = False,
        poisoned_counter: int = 0,
        poison_dmg: int = 0,
        poison_resistance: int = 0,
        super_memory: bool = False,
        lamp_on: bool = False,
        fire_resistance: int = 1,
        escape_threshold: int = 10,
        natural_weapon: Optional[NaturalWeapon] = None,
        is_slime: bool = False,
        can_split: bool = False,
        slime_generation: int = 0,
        can_pass_closed_doors: bool = False,
        can_open_doors: bool = False,
    ):
        self.max_hp = hp
        self._hp = hp
        self.base_defense = base_defense
        self._base_strength = strength
        self._recover_interval = max(0, recover_rate)
        self._base_recover_amount = max(0, recover_amount)
        self._recover_counter = self._recover_interval
        self._base_fov = fov
        self._base_foh = foh
        self._listen_foh_bonus = 0
        self.perception = perception
        self.weapon_proficiency = weapon_proficiency
        self.base_stealth = base_stealth
        self.location = (0, 0)
        self.aggravated = False
        if is_slime:
            self.aggravated = True
        self.aggressivity = aggressivity
        self.wait_counter = wait_counter
        self.base_to_hit = base_to_hit
        #self.max_to_hit = max_to_hit
        self.base_armor_value = base_armor_value
        self.temporal_effects = temporal_effects
        self._base_luck = luck
        self.satiety = satiety
        self.max_satiety = max_satiety
        self._base_max_stamina = max_stamina
        self._stamina = max(0, min(stamina, self._base_max_stamina))
        self.is_in_melee = is_in_melee
        self.defending = defending
        self.to_hit_counter = to_hit_counter
        self.to_power_counter = to_power_counter
        self.to_defense_counter = to_defense_couter
        self._base_critical_chance = critical_chance
        self._base_super_memory = super_memory
        self.lamp_on = lamp_on
        self.escape_threshold = escape_threshold
        self.natural_weapon = natural_weapon
        self.is_slime = is_slime
        self.can_split = can_split
        self.slime_generation = slime_generation
        self.can_pass_closed_doors = can_pass_closed_doors
        self.can_open_doors = can_open_doors
        self.embedded_projectiles: list["Item"] = []
        self.is_hidden = False
        self._hidden_wait_turns = 0

        #self.energy_points = energy_points
        #self.current_energy_points = current_energy_points

        self.current_time_points = current_time_points
        self.action_time_cost = action_time_cost

        self.can_fortify = can_fortify
        self.fortified = fortified
        
        self.woke_ai_cls = woke_ai_cls
        
        self.poisons_on_hit = poisons_on_hit
        self.poisonous = poisonous
        
        self.is_poisoned = is_poisoned
        self.poisoned_counter = poisoned_counter
        self.poison_dmg = poison_dmg

        self._init_fire_status(fire_resistance)

        # Resistances
        self._base_poison_resistance = poison_resistance
        self.is_blind = False
        self.is_player_confused = False
        self.player_confusion_turns = 0
        self.is_player_paralyzed = False
        self.player_paralysis_turns = 0
        # Cuenta ataques fallidos de enemigos contra el jugador para bonificar defensa.
        self.missed_by_enemy_counter = 0

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        old_hp = getattr(self, "_hp", self.max_hp)
        clamped = max(0, min(value, self.max_hp))
        took_damage = clamped < old_hp
        self._hp = clamped
        if took_damage:
            parent_entity = getattr(self, "parent", None)
            engine = None
            try:
                engine = self.engine
            except Exception:
                engine = None
            player_entity = getattr(engine, "player", None) if engine else None
            force_sound = parent_entity is player_entity
            _play_sound_if_audible(
                engine,
                play_pain_sound,
                parent_entity,
                source=parent_entity,
                level=2,
                force=force_sound,
            )
        if self._hp == 0 and getattr(self.parent, "ai", None):
            self.die()

    def _equipment_bonus(self, attribute: str, default: int = 0):
        parent = getattr(self, "parent", None)
        if parent:
            equipment = getattr(parent, "equipment", None)
            if equipment:
                return getattr(equipment, attribute, default)
        return default

    @property
    def strength_bonus(self) -> int:
        return self._equipment_bonus("strength_bonus")

    @property
    def fov_bonus(self) -> int:
        return self._equipment_bonus("fov_bonus")

    @property
    def max_stamina_bonus(self) -> int:
        return self._equipment_bonus("max_stamina_bonus")

    @property
    def poison_resistance_bonus(self) -> int:
        return self._equipment_bonus("poison_resistance_bonus")

    @property
    def super_memory_bonus(self) -> bool:
        equipment = getattr(self.parent, "equipment", None)
        if equipment:
            return getattr(equipment, "super_memory_bonus", False)
        return False

    @property
    def recover_rate_bonus(self) -> int:
        return self._equipment_bonus("recover_rate_bonus")

    @property
    def base_defense_bonus(self) -> int:
        return self._equipment_bonus("base_defense_bonus")

    @property
    def luck_bonus(self) -> int:
        return self._equipment_bonus("luck_bonus")

    @property
    def strength(self) -> int:
        return self._base_strength + self.strength_bonus

    @strength.setter
    def strength(self, value: int) -> None:
        self._base_strength = value - self.strength_bonus

    @property
    def recover_rate(self) -> int:
        return self._recover_interval

    @recover_rate.setter
    def recover_rate(self, value: int) -> None:
        self._recover_interval = max(0, value)
        self._recover_counter = min(self._recover_counter, self._recover_interval)

    @property
    def recover_amount(self) -> int:
        return self._base_recover_amount + self.recover_rate_bonus

    @recover_amount.setter
    def recover_amount(self, value: int) -> None:
        self._base_recover_amount = max(0, value - self.recover_rate_bonus)

    @property
    def fov(self) -> int:
        return self._base_fov + self.fov_bonus

    @fov.setter
    def fov(self, value: int) -> None:
        self._base_fov = value - self.fov_bonus

    @property
    def foh(self) -> int:
        engine = getattr(self, "engine", None)
        if engine and getattr(engine, "silence_turns", 0) > 0:
            return 0
        return getattr(self, "_base_foh", 0) + getattr(self, "_listen_foh_bonus", 0)

    @foh.setter
    def foh(self, value: int) -> None:
        self._base_foh = value

    @property
    def listen_foh_bonus(self) -> int:
        return getattr(self, "_listen_foh_bonus", 0)

    @listen_foh_bonus.setter
    def listen_foh_bonus(self, value: int) -> None:
        self._listen_foh_bonus = max(0, value)

    @property
    def effective_fov(self) -> int:
        """Return the current sight radius, accounting for lamp state and location."""
        base_fov = max(0, self.fov)
        if getattr(self, "is_blind", False):
            return 1
        engine = getattr(self, "engine", None)
        is_player = bool(engine and getattr(engine, "player", None) is getattr(self, "parent", None))
        if not is_player:
            return base_fov
        in_town = False
        try:
            in_town = bool(engine and engine.game_world.current_floor == 1)
        except Exception:
            in_town = False
        if in_town:
            return base_fov
        lamp_bonus = 5 if self.lamp_on else 0
        return base_fov + lamp_bonus

    @property
    def max_stamina(self) -> int:
        return self._base_max_stamina + self.max_stamina_bonus

    @max_stamina.setter
    def max_stamina(self, value: int) -> None:
        self._base_max_stamina = max(0, value - self.max_stamina_bonus)
        self.stamina = self.stamina

    @property
    def stamina(self) -> int:
        return getattr(self, "_stamina", 0)

    @stamina.setter
    def stamina(self, value: int) -> None:
        max_stamina = self.max_stamina
        clamped = max(0, min(value, max_stamina))
        self._stamina = clamped

    @property
    def poison_resistance(self) -> int:
        return self._base_poison_resistance + self.poison_resistance_bonus

    @poison_resistance.setter
    def poison_resistance(self, value: int) -> None:
        self._base_poison_resistance = value - self.poison_resistance_bonus

    @property
    def super_memory(self) -> bool:
        return self._base_super_memory or self.super_memory_bonus

    @super_memory.setter
    def super_memory(self, value: bool) -> None:
        self._base_super_memory = bool(value)

    @property
    def luck(self) -> int:
        return self._base_luck + self.luck_bonus

    @luck.setter
    def luck(self, value: int) -> None:
        self._base_luck = value - self.luck_bonus

    @property
    def critical_chance(self) -> float:
        return max(0.0, self._base_critical_chance + (self.luck * 0.01))

    @critical_chance.setter
    def critical_chance(self, value: float) -> None:
        self._base_critical_chance = max(0.0, value)

    @property
    def defense(self) -> int:
        if self._is_paralyzed():
            return 0
        blind_penalty = 4 if self.is_blind else 0
        return self.base_defense + self.defense_bonus + self.base_defense_bonus - blind_penalty
        #return self.base_defense + self.defense_bonus + self.to_defense_counter
    
    @property
    def main_hand_weapon(self):
        # if self.parent.equipment.weapon:
        #     return self.parent.equipment.weapon
        # else:
        #     return None
        equipment = getattr(self.parent, "equipment", None)
        if equipment and equipment.weapon:
            return equipment.weapon
        return None

    @property
    def weapon_dmg_dice(self) -> int:
        # if self.parent.equipment and self.parent.equipment.weapon:
        #     return self.parent.equipment.weapon.equippable.weapon_dmg_dice
        # else:
        #     return 0
        equipment = getattr(self.parent, "equipment", None)
        weapon = getattr(equipment, "weapon", None) if equipment else None
        if weapon and weapon.equippable:
            return weapon.equippable.weapon_dmg_dice
        if self.natural_weapon:
            return self.natural_weapon.weapon_dmg_dice
        return 0

    @property
    def weapon_dmg_dice_info(self) -> str:
        # if self.parent.equipment and self.parent.equipment.weapon:
        #     equippable = self.parent.equipment.weapon.equippable
        equipment = getattr(self.parent, "equipment", None)
        weapon = getattr(equipment, "weapon", None) if equipment else None
        if weapon and weapon.equippable:
            equippable = weapon.equippable
            if equippable:
                return f"1d{equippable.max_dmg}"
        if self.natural_weapon:
            return self.natural_weapon.weapon_dmg_dice_info
        return "1d0"

    @property
    def weapon_dmg_bonus(self) -> int:
        # if self.parent.equipment and self.parent.equipment.weapon:
        #     return self.parent.equipment.weapon.equippable.weapon_dmg_bonus
        equipment = getattr(self.parent, "equipment", None)
        weapon = getattr(equipment, "weapon", None) if equipment else None
        if weapon and weapon.equippable:
            return weapon.equippable.weapon_dmg_bonus
        if self.natural_weapon:
            return self.natural_weapon.weapon_dmg_bonus
        return 0
        
    @property
    def weapon_dmg_info(self) -> str:
        # if self.parent.equipment and self.parent.equipment.weapon:
        #     equippable = self.parent.equipment.weapon.equippable
        equipment = getattr(self.parent, "equipment", None)
        weapon = getattr(equipment, "weapon", None) if equipment else None
        if weapon and weapon.equippable:
            equippable = weapon.equippable
            if equippable:
                return f"1d{equippable.max_dmg}+{equippable.dmg_bonus}"
        if self.natural_weapon:
            return f"1d{self.natural_weapon.max_dmg}+{self.natural_weapon.dmg_bonus}"
        return "1d0+0"

    @property
    def natural_weapon_name(self) -> Optional[str]:
        if self.natural_weapon:
            return self.natural_weapon.name
        return None
        
    @property
    def non_weapon_dmg_bonus(self) -> str:
        bonus = 0
        if self.parent.equipment:
            bonus += self.parent.equipment.non_weapon_dmg_bonus
            return bonus
        else:
            return bonus

    # Total de bonus al daño de todo lo EQUIPADO
    @property
    def total_equipment_dmg_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.total_equipment_dmg_bonus
        else:
            return 0

    @property
    def total_fighter_dmg(self) -> int:
        if self.parent.equipment:
            return (self.strength + self.weapon_dmg_dice + self.parent.equipment.total_equipment_dmg_bonus) * self.weapon_proficiency
        else:
            return (self.strength + self.non_weapon_dmg_bonus) * self.weapon_proficiency

    @property
    def stealth(self) -> int:
        return (
            self.base_stealth
            + self.stealth_bonus
            - self.stealth_penalty
            + self._environmental_stealth_bonus()
        )
    
    @property
    def to_hit(self) -> int:
        result = self.base_to_hit + self.to_hit_bonus - self.to_hit_penalty
        if self.is_blind:
            result -= 4  # Blindness hampers accuracy.
        return result
    
    @property
    def armor_value(self) -> int:
        return self.base_armor_value + self.armor_value_bonus

    @property
    def defense_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.defense_bonus
        else:
            return 0
        
    @property
    def stealth_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.stealth_bonus
        else:
            return 0
        
    @property
    def stealth_penalty(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.stealth_penalty
        else:
            return 0

    def has_cloak_equipped(self) -> bool:
        equipment = getattr(self.parent, "equipment", None)
        if not equipment:
            return False
        return bool(getattr(equipment, "cloak", None))

    def _orthogonal_wall_adjacent(self) -> bool:
        """Return True if the actor is orthogonally adjacent to a non-walkable tile."""
        engine = getattr(self, "engine", None)
        actor = getattr(self, "parent", None)
        if not engine or not actor:
            return False
        gamemap = engine.game_map
        deltas = [(0, -1), (-1, 0), (1, 0), (0, 1)]
        for dx, dy in deltas:
            nx, ny = actor.x + dx, actor.y + dy
            if not gamemap.in_bounds(nx, ny):
                continue
            if not gamemap.tiles["walkable"][nx, ny]:
                return True
        return False

    def _transparency_map(self):
        engine = getattr(self, "engine", None)
        if not engine:
            return None
        gamemap = engine.game_map
        try:
            return gamemap.get_transparency_map()
        except Exception:
            return gamemap.tiles["transparent"]

    def is_in_other_creature_fov(self) -> bool:
        """Check if this actor is inside the FOV of any other living actor."""
        actor = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not actor or not engine:
            return False
        gamemap = engine.game_map
        transparency = self._transparency_map()
        if transparency is None:
            return False
        for other in gamemap.actors:
            if other is actor or not getattr(other, "is_alive", False):
                continue
            other_fighter = getattr(other, "fighter", None)
            if not other_fighter:
                continue
            radius = getattr(other_fighter, "fov", 0)
            if radius <= 0:
                continue
            visible = compute_fov(
                transparency,
                (other.x, other.y),
                radius,
                algorithm=settings.FOV_ALGORITHM,
            )
            if bool(visible[actor.x, actor.y]):
                return True
        return False

    def _actor_visible_to_player(self) -> bool:
        actor = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not actor or not engine:
            return False
        if actor is engine.player:
            return True
        try:
            return bool(engine.game_map.visible[actor.x, actor.y])
        except Exception:
            return False

    def _notify_hidden(self) -> None:
        actor = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not actor or not engine:
            return
        if actor is engine.player:
            engine.message_log.add_message("You are now hidden.", color.status_effect_applied)
        elif self._actor_visible_to_player():
            engine.message_log.add_message(f"{actor.name} slips into hiding.", color.status_effect_applied)

    def break_hide(self, reason: str = "", revealer: Optional["Actor"] = None) -> None:
        """Remove hidden state and notify the player if appropriate."""
        actor = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        self._hidden_wait_turns = 0
        if not getattr(self, "is_hidden", False):
            return
        self.is_hidden = False
        if not actor or not engine:
            return

        if actor is engine.player:
            if reason == "collision" and revealer:
                engine.message_log.add_message(
                    f"You are revealed as {revealer.name} bumps into you!",
                    color.descend,
                )
            elif reason == "action":
                engine.message_log.add_message("You leave your hiding spot.", color.descend)
            else:
                engine.message_log.add_message("You are no longer hidden.", color.descend)
            return

        if not self._actor_visible_to_player():
            return

        if reason == "collision" and revealer:
            engine.message_log.add_message(
                f"{actor.name} is revealed when {revealer.name} bumps into them!",
                color.descend,
            )
        elif reason == "action":
            engine.message_log.add_message(f"{actor.name} steps out of hiding.", color.descend)
        else:
            engine.message_log.add_message(f"{actor.name} is revealed.", color.descend)

    def _can_attempt_hide(self) -> bool:
        actor = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not actor or not engine or actor is not engine.player:
            return False

        if getattr(self, "is_in_melee", False):
            return False

        gamemap = engine.game_map
        for other in gamemap.actors:
            if other is actor or not getattr(other, "is_alive", False):
                continue
            if max(abs(other.x - actor.x), abs(other.y - actor.y)) <= 1:
                return False

        return (
            self.has_cloak_equipped()
            and not getattr(self, "lamp_on", False)
            and self._orthogonal_wall_adjacent()
            and not self.is_in_other_creature_fov()
        )

    def handle_post_action(self, is_wait_action: bool, action_name: str = "") -> None:
        """Manage hide/unhide transitions after an action finishes."""
        actor = getattr(self, "parent", None)
        engine = getattr(self, "engine", None)
        if not actor or not engine:
            self.is_hidden = False
            self._hidden_wait_turns = 0
            return

        # Si el sigilo está desactivado globalmente, fuerza estado visible.
        if getattr(settings, "STEALTH_DISABLED", False):
            self.is_hidden = False
            self._hidden_wait_turns = 0
            return

        if actor is not engine.player:
            self.is_hidden = False
            self._hidden_wait_turns = 0
            return

        if is_wait_action:
            if not self._can_attempt_hide():
                self._hidden_wait_turns = 0
                if self.is_hidden:
                    self.break_hide(reason="conditions")
                return

            self._hidden_wait_turns += 1
            if self._hidden_wait_turns >= 4 and not self.is_hidden:
                self.is_hidden = True
                self._hidden_wait_turns = 0
                self._notify_hidden()
            return

        self._hidden_wait_turns = 0
        if self.is_hidden:
            self.break_hide(reason="action")

    def _environmental_stealth_bonus(self) -> int:
        """Situational stealth bonus when the player hugs a wall orthogonally."""
        engine = getattr(self, "engine", None)
        parent = getattr(self, "parent", None)
        if not engine or parent is not getattr(engine, "player", None):
            return 0
        return 1 if self._orthogonal_wall_adjacent() else 0
        
    @property
    def to_hit_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.to_hit_bonus
        else:
            return 0
        
    @property
    def to_hit_penalty(self) -> int:
        penalty = 0
        if self.parent.equipment:
            # Por algún motivo esto está retornando 0
            penalty += self.parent.equipment.to_hit_penalty
        return penalty

    def _is_paralyzed(self) -> bool:
        """Return True when paralysis should nullify defense."""
        try:
            from components.ai import ParalizeEnemy
        except Exception:
            ParalizeEnemy = None
        ai = getattr(self.parent, "ai", None)
        if ParalizeEnemy and isinstance(ai, ParalizeEnemy):
            return True
        return getattr(self, "is_player_paralyzed", False)
        
    @property
    def armor_value_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.armor_value_bonus
        else:
            return 0

    def on_equipment_changed(self) -> None:
        # Keep mutable resources within the new limits after equipping/unequipping.
        self.stamina = self.stamina
    
    def poisoned(self):
        if not self.is_poisoned:
            return

        parent = getattr(self, "parent", None)
        parent_alive = True
        if parent and hasattr(parent, "is_alive"):
            try:
                parent_alive = bool(parent.is_alive)
            except Exception:
                parent_alive = True
        if not parent_alive:
            self.is_poisoned = False
            self.poisoned_counter = 0
            self.poison_dmg = 0
            return

        total_damage = (self.poisoned_counter * self.poison_dmg) - self.poison_resistance
        if total_damage < 0:
            total_damage = 0
        if DEBUG_MODE:
            print("DEBUG: >>> self.poison_resistance = ", self.poison_resistance)
        
        if self.poisoned_counter > 1:
            #self.hp -= self.poison_dmg
            self.hp -= total_damage
            self.poisoned_counter -= 1

            if self.parent.name == self.engine.player.name:
                self.engine.message_log.add_message(
                    f"You are poisoned! You take {total_damage} damage points.",
                    color.red,
                    )
            else:
                # TODO: esto hay que relativilarlo a si es o no visible la criatura.
                self.engine.message_log.add_message(
                    f"{self.parent.name} is poisoned! {self.parent.name} takes {total_damage} damage points.",
                    color.red,
                    )

        else:
            self.poisoned_counter = 0
            self.is_poisoned = False
            if self.parent.name == self.engine.player.name:
                self.engine.message_log.add_message(
                    f"You are no longer poisoned.",
                    color.status_effect_applied,
                    )
            else:
                self.engine.message_log.add_message(
                    f"{self.parent.name} is no longer poisoned.",
                    color.status_effect_applied,
                    )
 
    #def update_energy_points(self):
    #    self.current_energy_points += self.energy_points

    def drop_loot(self):
        inventory_component = getattr(self.parent, "inventory", None)
        # Drop any projectiles that were embedded in this creature, regardless of capacity.
        if getattr(self, "embedded_projectiles", None):
            for proj in list(self.embedded_projectiles):
                try:
                    self.embedded_projectiles.remove(proj)
                except ValueError:
                    pass
                proj.place(self.parent.x, self.parent.y, self.gamemap)

        if not inventory_component:
            return 0
        if inventory_component.capacity <= 0 and not inventory_component.items:
            return 0

        items_to_drop = list(getattr(inventory_component, "items", []) or [])
        for item in items_to_drop:
            try:
                inventory_component.items.remove(item)
            except ValueError:
                pass  # Item already removed elsewhere.
            item.place(self.parent.x, self.parent.y, self.gamemap)

        special_loot = loot_tables.roll_special_drop(getattr(self.parent, "name", ""))
        if special_loot:
            for extra in special_loot:
                extra.spawn(self.gamemap, self.parent.x, self.parent.y)

        return 0

    def _identify_inventory_on_player_death(self) -> None:
        """Reveal any unidentified player items when the feature is enabled."""
        if not getattr(settings, "AUTO_IDENTIFY_INVENTORY_ON_DEATH", False):
            return
        inventory = getattr(self.parent, "inventory", None)
        if not inventory or not getattr(inventory, "items", None):
            return
        message_log = getattr(self.engine, "message_log", None)
        newly_identified = 0
        for item in list(inventory.items):
            if not getattr(item, "identified", False):
                try:
                    item.identify()
                except Exception:
                    continue
                newly_identified += 1
        if newly_identified and message_log:
            message_log.add_message(
                _("As the darkness takes you, your remaining belongings reveal their secrets."),
                color.status_effect_applied,
            )

    def die(self) -> None:

        #self.engine.player.fighter.is_in_melee = False

        original_name = getattr(self.parent, "name", "")
        lowered_name = original_name.lower() if isinstance(original_name, str) else ""
        is_campfire = lowered_name == "campfire"
        is_table = lowered_name == "table"

        if self.engine.player is self.parent:
            self._identify_inventory_on_player_death()
            # TODO: disparar sonido de muerte del Personaje.
            death_message = "You died!"
            death_message_color = color.player_die
        else:
            death_message = f"{self.parent.name} is dead!"
            death_message_color = color.enemy_die
        engine = getattr(self, "engine", None)
        player_entity = getattr(engine, "player", None) if engine else None
        sound_source = getattr(self, "parent", None)
        force_sound = sound_source is player_entity
        if is_table:
            _play_sound_if_audible(
                engine,
                play_table_destroy_sound,
                source=sound_source,
                level=3,
                force=force_sound,
            )
        else:
            _play_sound_if_audible(
                engine,
                play_death_sound,
                sound_source,
                source=sound_source,
                level=2,
                force=force_sound,
            )

        self.parent.char = "%"
        self.parent.color = (160, 160, 160)
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = f"remains of {original_name}"
        self.parent.render_order = RenderOrder.CORPSE

        if self.engine.game_map.visible[self.parent.x, self.parent.y]:
            print(death_message)
            self.engine.message_log.add_message(death_message, death_message_color)

        if is_campfire:
            update_campfire_audio(self.parent, False)

        self.engine.player.level.add_xp(self.parent.level.xp_given)

        if self.parent.name == "Adventurer":
            self.engine.player.fighter.luck -= 1

            if self.parent.level == 8:
                death_message = f"A tremor shakes the walls."
                death_message_color = color.descend
                self.engine.message_log.add_message(death_message, death_message_color)

            else:
                death_message = f"Distant thunder sounds."
                death_message_color = color.descend
                self.engine.message_log.add_message(death_message, death_message_color)

        # if self.parent.name == "Adventurer":
        #     self.engine.player.fighter.luck -= 1

        #     death_message = f"Distant thunder sounds."
        #     death_message_color = color.descend
        #     self.engine.message_log.add_message(death_message, death_message_color)



        return self.drop_loot()
    
    def desintegrate(self) -> None:

        #self.engine.player.fighter.is_in_melee = False

        name = getattr(self.parent, "name", "")
        is_adventurer = bool(name and name.lower() == "adventurer")
        adventurer_loot = []
        if is_adventurer:
            adventurer_loot = [copy.deepcopy(item) for item in self.parent.inventory.items]

        if self.engine.player is self.parent:
            self._identify_inventory_on_player_death()
            death_message = "You died!"
            death_message_color = color.player_die
        else:
            death_message = f"{self.parent.name} take the stairs!"
            death_message_color = color.descend


        self.parent.char = ""
        self.parent.color = None
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = None

        print(death_message)
        self.engine.message_log.add_message(death_message, death_message_color)

        self.engine.player.level.add_xp(self.parent.level.xp_given)

        if is_adventurer:
            self.engine.game_world.register_adventurer_descent(adventurer_loot)

        return 0
    
    def heal(self, amount: int) -> int:
        if self.hp == self.max_hp:
            return 0

        new_hp_value = self.hp + amount

        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp

        amount_recovered = new_hp_value - self.hp

        self.hp = new_hp_value

        return amount_recovered

    def eat(self, amount: int) -> int:
        if self.satiety >= self.max_satiety:
            #self.satiety = self.max_satiety
            return 0
        else:
            self.satiety += amount

        return amount
    
    def autoheal(self):
        """Backward-compatible alias for tick_recovery."""
        return self.tick_recovery()

    def _slime_visible(self) -> bool:
        engine = getattr(self, "engine", None)
        try:
            return bool(engine and engine.game_map.visible[self.parent.x, self.parent.y])
        except Exception:
            return False

    def _absorb_attack_item(self, attacker: Optional["Actor"], attack_item: Optional["Item"]) -> bool:
        if not attack_item:
            return False
        equippable = getattr(attack_item, "equippable", None)
        if not equippable and not getattr(attack_item, "throwable", False):
            return False

        inventory = getattr(self.parent, "inventory", None)
        if not inventory or inventory.capacity <= len(inventory.items):
            return False

        engine = getattr(self, "engine", None)
        # Try to detach from previous owner.
        if attacker:
            equipment = getattr(attacker, "equipment", None)
            if equipment:
                for slot in ("weapon", "armor", "head_armor", "cloak", "artifact", "ring_left", "ring_right"):
                    if getattr(equipment, slot, None) is attack_item:
                        setattr(equipment, slot, None)
            attacker_inventory = getattr(attacker, "inventory", None)
            if attacker_inventory and attack_item in attacker_inventory.items:
                try:
                    attacker_inventory.items.remove(attack_item)
                except ValueError:
                    pass

        # Remove from ground if needed.
        if getattr(attack_item, "parent", None) is not inventory:
            try:
                current_container = attack_item.gamemap
            except Exception:
                current_container = None
            entities = getattr(current_container, "entities", None)
            if entities:
                entities.discard(attack_item)

        attack_item.parent = inventory
        inventory.items.append(attack_item)

        if engine:
            if attacker and attacker is getattr(engine, "player", None):
                engine.message_log.add_message(
                    f"Your {attack_item.name} is absorbed by the slime!",
                    color.orange,
                )
            elif self._slime_visible():
                engine.message_log.add_message(
                    f"The {self.parent.name} absorbs {attack_item.name}.",
                    color.status_effect_applied,
                )
        return True

    def _slime_split_positions(self, gamemap, x: int, y: int):
        positions = [(x, y)]
        offsets = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            try:
                in_bounds = gamemap.in_bounds(nx, ny)
                walkable = gamemap.tiles["walkable"][nx, ny] if in_bounds else False
            except Exception:
                continue
            if not in_bounds or not walkable:
                continue
            if gamemap.get_blocking_entity_at_location(nx, ny):
                continue
            positions.append((nx, ny))
            break
        return positions

    def _spawn_slime_fragment(self, gamemap, x: int, y: int, child_hp: int, child_capacity: int):
        try:
            from entity_factories import slime as slime_proto
        except Exception:
            return None
        fragment = slime_proto.spawn(gamemap, x, y)
        fragment.name = "Small slime"
        fragment.char = "s"
        fragment.fighter.max_hp = child_hp
        fragment.fighter.hp = child_hp
        fragment.fighter.can_split = False
        fragment.fighter.is_slime = True
        fragment.fighter.slime_generation = self.slime_generation + 1
        fragment.fighter.recover_rate = self.recover_rate
        fragment.fighter.recover_amount = self.recover_amount
        fragment.inventory.capacity = child_capacity
        fragment.inventory.items = []
        return fragment

    def _split_slime(self) -> None:
        gamemap = getattr(self, "gamemap", None)
        parent_entity = getattr(self, "parent", None)
        if not gamemap or not parent_entity:
            return
        engine = getattr(self, "engine", None)
        inventory = getattr(parent_entity, "inventory", None)
        items = list(getattr(inventory, "items", []) or [])
        capacity = getattr(inventory, "capacity", 0) if inventory else 0
        if inventory is not None:
            inventory.items = []

        child_capacity = max(0, capacity // 2)
        child_hp = max(1, self.max_hp // 2)

        if parent_entity in gamemap.entities:
            gamemap.entities.discard(parent_entity)

        positions = self._slime_split_positions(gamemap, parent_entity.x, parent_entity.y)
        children = []
        for pos in positions:
            child = self._spawn_slime_fragment(gamemap, pos[0], pos[1], child_hp, child_capacity)
            if child:
                children.append(child)
            if len(children) >= 2:
                break

        visible = self._slime_visible()
        if engine and visible and children:
            engine.message_log.add_message(
                "The slime splits into smaller blobs!",
                color.status_effect_applied,
            )

        # Distribute items among children; drop leftovers.
        random.shuffle(items)
        for item in items:
            placed = False
            for child in children:
                child_inv = getattr(child, "inventory", None)
                if child_inv and child_inv.capacity > len(child_inv.items):
                    child_inv.items.append(item)
                    item.parent = child_inv
                    placed = True
                    break
            if not placed and gamemap:
                item.place(parent_entity.x, parent_entity.y, gamemap)

        self._hp = 0

    def take_damage(
        self,
        amount: int,
        attacker: Optional["Actor"] = None,
        attack_item: Optional["Item"] = None,
    ) -> None:
        if getattr(self, "is_slime", False):
            fatal = amount >= self.hp
            if fatal and getattr(self, "can_split", False):
                self._split_slime()
                return
            if not fatal:
                self._absorb_attack_item(attacker, attack_item)
            self.hp -= amount
            return

        self.hp -= amount
        # Being hit generates noise so the player hears blows on the wall.
        # Entiendo que este ruido ya se está registrando en el MeleeAction
        # de los fighter.py, cuando el atacante hace daño.
        # if getattr(self.engine, "register_noise", None):
        #     try:
        #         self.engine.register_noise(attacker or self.parent, level=3, duration=1, tag="wall_hit")
        #     except Exception:
        #         pass
   
    def gain_temporal_bonus(self, turns, amount, attribute, message_down):

        if attribute == 'strength':
            self.strength += amount
        elif attribute == 'base_to_hit':
            self.base_to_hit += amount
        elif attribute == 'base_stealth':
            self.base_stealth += amount
        elif attribute == 'fov':
            self.fov += amount
            if amount < 0:
                self.is_blind = True

        self.temporal_effects = True
        self.engine.manage_temporal_effects(self.parent, turns, amount, attribute, message_down)
    
    def decrease_power(self, amount: int):
        self.strength -= amount

    def restore_power(self, amount: int):
        self.strength += amount
        
    def gain_power(self, amount: int):
        self.strength += amount

    def apply_player_confusion(self, turns: int) -> None:
        self.is_player_confused = True
        self.player_confusion_turns = max(1, turns)

    def apply_player_paralysis(self, turns: int) -> None:
        self.is_player_paralyzed = True
        self.player_paralysis_turns = max(1, turns)
        self.engine.message_log.add_message(
            "You cannot move; your body is paralyzed!",
            color.status_effect_applied,
        )

    def advance_player_paralysis(self) -> None:
        if not getattr(self, "is_player_paralyzed", False):
            return
        self.player_paralysis_turns -= 1
        if self.player_paralysis_turns <= 0:
            self.is_player_paralyzed = False
            self.player_paralysis_turns = 0
            self.engine.message_log.add_message(
                "You can move again.", color.status_effect_applied
            )

    def clear_player_paralysis(self) -> None:
        if getattr(self, "is_player_paralyzed", False):
            self.is_player_paralyzed = False
            self.player_paralysis_turns = 0
            self.engine.message_log.add_message(
                "You can move again.", color.status_effect_applied
            )

    def advance_player_confusion(self) -> None:
        if not self.is_player_confused:
            return
        self.player_confusion_turns -= 1
        if self.player_confusion_turns <= 0:
            self.is_player_confused = False
            self.player_confusion_turns = 0
            self.engine.message_log.add_message(
                "You are no longer confused.", color.status_effect_applied
            )

    def clear_player_confusion(self) -> None:
        if self.is_player_confused:
            self.is_player_confused = False
            self.player_confusion_turns = 0
            self.engine.message_log.add_message(
                "You are no longer confused.", color.status_effect_applied
            )

    def register_enemy_miss(self) -> None:
        """Aumenta la defensa base del jugador tras varios fallos enemigos."""
        engine = getattr(self, "engine", None)
        player = getattr(engine, "player", None) if engine else None

        if PLAYER_DEFENSE_MISS_THRESHOLD <= 0:
            return
        if player is None or self.parent is not player:
            return

        self.missed_by_enemy_counter += 1
        if self.missed_by_enemy_counter >= PLAYER_DEFENSE_MISS_THRESHOLD:
            self.base_defense += 1
            self.missed_by_enemy_counter = 0
            engine.message_log.add_message(
                _("Your defensive skills are improving!"),
                color.orange,
            )

        
class Door(FireStatusMixin, BaseComponent):

    parent: Obstacle

    def __init__(
            self, hp: int, 
            base_defense: int, 
            strength: int, 
            recover_rate: int = 50, 
            recover_amount: int = 0,
            fov: int = 0, 
            weapon_proficiency: float = 1.0,
            base_stealth: int = 0,
            aggressivity: int = 0,
            wait_counter: int = 0,
            base_to_hit: int = 0,
            base_armor_value: int = 0,
            temporal_effects: bool = False,
            stamina: int = 0,
            max_stamina: int = 0,
            is_in_melee: bool = False,
            to_power_counter: int = 0,
            to_hit_counter: int = 0,
            current_time_points: int = 10,
            action_time_cost: int = 10,
            can_fortify: bool = False,
            fortified: bool = False,
            #woke_ai_cls = HostileEnemy,
            #poisons_on_hit: bool = False,
            is_poisoned: bool = False,
            #poisoned_counter: int = 0,
            #poison_dmg: int = 0,
            fire_resistance: int = 1,
            lock_color: Optional[str] = None,
            ):
        self.max_hp = hp
        self._hp = hp
        self.base_defense = base_defense
        self.strength = strength
        self.recover_rate = recover_rate
        self.recover_amount = recover_amount
        self._recover_counter = self.recover_rate
        self.fov = fov
        self.weapon_proficiency = weapon_proficiency
        self.base_stealth = base_stealth
        self.location = (0, 0)
        self.aggravated = False
        self.aggressivity = aggressivity
        self.wait_counter = wait_counter
        self.base_to_hit = base_to_hit
        self.base_armor_value = base_armor_value
        self.temporal_effects = temporal_effects
        self.stamina = stamina
        self.max_stamina = max_stamina
        self.is_in_melee = is_in_melee
        self.to_power_counter = to_power_counter
        self.to_hit_counter =to_hit_counter
        self.current_time_points = current_time_points
        self.action_time_cost = action_time_cost
        self.can_fortity = can_fortify
        self.fortified = fortified
        
        self.is_poisoned = is_poisoned
        self._init_fire_status(fire_resistance)
        self.is_open = False
        self.lock_color = lock_color
        self.closed_char = "+"
        self.open_char = "-"
        self.closed_color = (93, 59, 0)
        self.open_color = (200, 200, 120)


    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(value, self.max_hp))
        if self._hp == 0 and self.parent.ai:
            self.die()

    @property
    def defense(self) -> int:
        return self.base_defense + self.defense_bonus

    @property
    def power(self) -> int:
        return self.strength + self.weapon_dmg
    
    @property
    def stealth(self) -> int:
        return self.base_stealth + self.stealth_bonus - self.stealth_penalty
    
    @property
    def to_hit(self) -> int:
        return self.base_to_hit + self.to_hit_bonus - self.to_hit_penalty
    
    @property
    def armor_value(self) -> int:
        return self.base_armor_value + self.armor_value_bonus

    @property
    def defense_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.defense_bonus
        else:
            return 0

    @property
    def weapon_dmg(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.weapon_dmg
        else:
            return 0
        
    @property
    def stealth_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.stealth_bonus
        else:
            return 0
        
    @property
    def stealth_penalty(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.armor_value_bonus
        else:
            return 0

    def _environmental_stealth_bonus(self) -> int:
        """Situational stealth bonus when the player hugs a wall orthogonally."""
        engine = getattr(self, "engine", None)
        parent = getattr(self, "parent", None)
        if not engine or parent is not getattr(engine, "player", None):
            return 0
        gamemap = getattr(engine, "game_map", None)
        if not gamemap:
            return 0
        deltas = [(0, -1), (-1, 0), (1, 0), (0, 1)]
        for dx, dy in deltas:
            nx, ny = parent.x + dx, parent.y + dy
            if not gamemap.in_bounds(nx, ny):
                continue
            if not gamemap.tiles["walkable"][nx, ny]:
                return 1
        return 0
        
    @property
    def to_hit_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.stealth_bonus
        else:
            return 0
        
    @property
    def to_hit_penalty(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.armor_value_bonus
        else:
            return 0
        
    @property
    def armor_value_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.armor_value_bonus
        else:
            return 0


    def drop_loot(self):
            inventory_component = getattr(self.parent, "inventory", None)
            if not inventory_component:
                return 0

            items_to_drop = list(getattr(inventory_component, "items", []) or [])
            for item in items_to_drop:
                item.spawn(self.gamemap, self.parent.x, self.parent.y)

            special_loot = loot_tables.roll_special_drop(getattr(self.parent, "name", ""))
            if special_loot:
                for extra in special_loot:
                    extra.spawn(self.gamemap, self.parent.x, self.parent.y)

            return 0

    def sync_with_tile(self) -> None:
        tile = self.engine.game_map.tiles[self.parent.x, self.parent.y]
        self.is_open = bool(np.array_equal(tile, tile_types.open_door))
        self._apply_state(update_tile=False)

    def set_open(self, open_state: bool) -> None:
        if self.is_open == open_state:
            return
        self.is_open = open_state
        self._apply_state(update_tile=True)

    def _apply_state(self, update_tile: bool = True) -> None:
        char = self.open_char if self.is_open else self.closed_char
        color_value = self.open_color if self.is_open else self.closed_color
        self.parent.char = char
        self.parent.color = color_value
        self.parent.blocks_movement = not self.is_open
        if update_tile:
            tile = tile_types.open_door if self.is_open else tile_types.closed_door
            self.engine.game_map.tiles[self.parent.x, self.parent.y] = tile

    def die(self) -> None:
        death_message = f"{self.parent.name} is down!"
        death_message_color = color.enemy_die

        print(death_message)
        self.engine.message_log.add_message(death_message, death_message_color)
        gamemap = self.engine.game_map
        x, y = self.parent.x, self.parent.y
        gamemap.tiles[x, y] = tile_types.floor
        gamemap.entities.discard(self.parent)
        self.engine.player.level.add_xp(self.parent.level.xp_given)
        self.drop_loot()
        if getattr(self.parent, "name", "").lower() == "table":
            _play_sound_if_audible(
                self.engine,
                play_table_destroy_sound,
                source=self.parent,
                level=3,
                force=self.parent is getattr(self.engine, "player", None),
            )
        import entity_factories
        entity_factories.breakable_wall_rubble.spawn(gamemap, x, y)
        return None


    def heal(self, amount: int) -> int:
        if self.hp == self.max_hp:
            return 0

        new_hp_value = self.hp + amount

        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp

        amount_recovered = new_hp_value - self.hp

        self.hp = new_hp_value

        return amount_recovered
    

    def take_damage(
        self,
        amount: int,
        attacker: Optional["Actor"] = None,
        attack_item: Optional["Item"] = None,
    ) -> None:
        self.hp -= amount
    
    
    def decrease_power(self, amount: int):
        self.strength -= amount


    def restore_power(self, amount: int):
        self.strength += amount


class BreakableWallFighter(FireStatusMixin, BaseComponent):
    parent: Obstacle

    def __init__(
        self,
        hp: int,
        base_defense: int = 0,
        strength: int = 0,
        recover_rate: int = 0,
        recover_amount: int = 0,
        base_armor_value: int = 0,
        loot_drop_chance: float = 0.25,
        current_time_points: int = 0,
        action_time_cost: int = 10,
        fire_resistance: int = 1,
    ):
        self.max_hp = hp
        self._hp = hp
        self.base_defense = base_defense
        self.strength = strength
        self.recover_rate = recover_rate
        self.recover_amount = recover_amount
        self._recover_counter = self.recover_rate
        self.base_armor_value = base_armor_value
        self.loot_drop_chance = loot_drop_chance
        self.current_time_points = current_time_points
        self.action_time_cost = action_time_cost
        self.is_poisoned = False
        self.poisoned_counter = 0
        self.poison_dmg = 0
        self.aggravated = False
        self.stamina = 0
        self.weapon_proficiency = 1.0
        self._init_fire_status(fire_resistance)
        self._last_attacker_is_player = False
        self._last_attacker = None

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(value, self.max_hp))
        if self._hp == 0:
            self.die()

    @property
    def defense(self) -> int:
        return self.base_defense + self.defense_bonus

    @property
    def power(self) -> int:
        return self.strength + self.weapon_dmg

    @property
    def armor_value(self) -> int:
        return self.base_armor_value + self.armor_value_bonus

    @property
    def defense_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.defense_bonus
        return 0

    @property
    def weapon_dmg(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.weapon_dmg
        return 0

    @property
    def armor_value_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.armor_value_bonus
        return 0

    def heal(self, amount: int) -> int:
        if self.hp == self.max_hp:
            return 0
        new_hp_value = min(self.hp + amount, self.max_hp)
        amount_recovered = new_hp_value - self.hp
        self.hp = new_hp_value
        return amount_recovered

    def take_damage(
        self,
        amount: int,
        attacker: Optional["Actor"] = None,
        attack_item: Optional["Item"] = None,
    ) -> None:
        self.hp -= amount
        player_entity = getattr(self.engine, "player", None)
        self._last_attacker_is_player = attacker is player_entity
        self._last_attacker = attacker
        # Being hit generates noise so the player hears blows on the wall.
        if getattr(self.engine, "register_noise", None):
            try:
                self.engine.register_noise(self.parent, level=3, duration=1, tag="wall_hit")
            except Exception:
                pass

    def drop_loot(self) -> None:
        inventory = getattr(self.parent.inventory, "items", None)
        if not inventory:
            return None
        if random.random() > self.loot_drop_chance:
            return None

        loot = random.choice(inventory)
        loot.spawn(self.gamemap, self.parent.x, self.parent.y)
        try:
            inventory.remove(loot)
        except ValueError:
            pass
        return None

    def die(self) -> None:
        x, y = self.parent.x, self.parent.y
        gamemap = self.engine.game_map
        death_message = f"The {self.parent.name.lower()} collapses!"
        visible = getattr(gamemap, "visible", None)
        player_can_see = False
        if visible is not None and gamemap.in_bounds(x, y):
            try:
                player_can_see = bool(visible[x, y])
            except Exception:
                player_can_see = False
        last_attacker_player = getattr(self, "_last_attacker_is_player", False)
        if player_can_see or last_attacker_player:
            self.engine.message_log.add_message(death_message, color.enemy_die)
        engine = getattr(self, "engine", None)
        player_entity = getattr(engine, "player", None) if engine else None
        force_sound = bool(last_attacker_player or self.parent is player_entity)
        _play_sound_if_audible(
            engine,
            play_breakable_wall_destroy_sound,
            source=self.parent,
            level=4,
            force=force_sound,
        )
        
        # Extra noise on wall destruction so nearby foes (and the player) can hear it.
        if getattr(self.engine, "register_noise", None):
            try:
                self.engine.register_noise(self.parent, level=4, duration=3, tag="wall_break")
                if self._last_attacker:
                    self.engine.register_noise(
                        self._last_attacker, level=4, duration=3, tag="wall_break"
                    )
            except Exception:
                pass
        gamemap.tiles[x, y] = tile_types.floor
        self.parent.ai = None
        self.parent.blocks_movement = False

        self.drop_loot()
        self.engine.player.level.add_xp(self.parent.level.xp_given)

        gamemap.entities.discard(self.parent)

        import entity_factories

        entity_factories.breakable_wall_rubble.spawn(gamemap, x, y)
