# Aquí definimios el item consumible base y diseñamos los efectos de los items "consumibles"

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Dict, List, Tuple
import random

import actions
import color
import components.ai
import components.inventory
from components.base_component import BaseComponent
from exceptions import Impossible
from input_handlers import (
    ActionOrHandler,
    AreaRangedAttackHandler,
    InventoryIdentifyHandler,
    InventoryRemoveCurseHandler,
    SingleRangedAttackHandler,
)

if TYPE_CHECKING:
    from entity import Actor, Item, Obstacle


class Consumable(BaseComponent):
    parent: Item

    TEMPORAL_EFFECT_TEXTS: Dict[str, Dict[str, str]] = {
        "Power brew": {
            "player_hi": "You feel strong!",
            "creature_hi": "{name} looks strong!",
            "player_end": "You feel weak.",
            "creature_end": "{name} seems to lose strength.",
        },
        "Amphetamine brew": {
            "player_hi": "You feel sharp!",
            "creature_hi": "{name}'s pupils dilate sharply.",
            "player_end": "Your senses dull again.",
            "creature_end": "{name} looks less focused.",
        },
    }

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        """Try to return the action for this item."""
        return actions.ItemAction(consumer, self.parent)

    def activate(self, action: actions.ItemAction) -> None:
        """Invoke this items ability.

        `action` is the context for this activation.
        """
        raise NotImplementedError()
    
    def consume(self) -> None:
        """Remove the consumed item from its containing inventory."""
        entity = self.parent
        inventory = entity.parent
        if isinstance(inventory, components.inventory.Inventory):
            inventory.items.remove(entity)

    def _clear_confusion(self, target: Actor) -> None:
        cleared = False
        if target is self.engine.player:
            if target.fighter.is_player_confused:
                target.fighter.clear_player_confusion()
                cleared = True
        else:
            ai = target.ai
            if isinstance(ai, components.ai.ConfusedEnemy):
                target.ai = ai.previous_ai
                cleared = True
        if cleared and target is not self.engine.player and self.engine.game_map.visible[target.x, target.y]:
            self.engine.message_log.add_message(
                f"{target.name} regains its senses.",
                color.status_effect_applied,
            )

    def _effect_message(
        self,
        recipient: Actor,
        player_text: Optional[str],
        creature_text: Optional[str],
        color_value=color.status_effect_applied,
        **fmt,
    ) -> None:
        if getattr(self, "_suppress_effect_messages", False):
            self._effect_message_emitted = False
            return False

        text: Optional[str] = None
        data = {"name": recipient.name, **fmt}
        if recipient is self.engine.player:
            if player_text:
                text = player_text.format(**data)
        elif creature_text and self.engine.game_map.visible[recipient.x, recipient.y]:
            text = creature_text.format(**data)
        if text:
            self.engine.message_log.add_message(text, color_value)
            self._effect_message_emitted = True
            return True
        self._effect_message_emitted = False
        return False

    def _resolve_temporal_texts(
        self,
        default_player_hi: Optional[str],
        default_creature_hi: Optional[str],
        default_end: Optional[str],
    ):
        key = getattr(self, "message_key", None)
        if not key and hasattr(self, "parent"):
            key = getattr(self.parent, "id_name", None)
        config = self.TEMPORAL_EFFECT_TEXTS.get(key or "", {})
        player_hi = default_player_hi or config.get("player_hi") or "You feel different."
        creature_hi = default_creature_hi or config.get("creature_hi") or "{name} looks affected."
        player_end = default_end or config.get("player_end") or "The effect wears off."
        creature_end = config.get("creature_end") or player_end
        return player_hi, creature_hi, player_end, creature_end

SCROLL_IDENTIFICATION_DESCRIPTIONS: Dict[str, str] = {
    "Confusion scroll": "{target} titubea bajo las runas chispeantes.",
    "Paralisis scroll": "Las sigilosas runas atrapan a {target} en el sitio.",
    "Lightning scroll": "El aire cruje y un rayo alcanza a {target}.",
    "Fireball scroll": "La explosión ígnea iluminó las runas: {affected} objetivo(s) quedaron ardiendo.",
    "Descend scroll": "Un remolino de runas te arrastra hasta el siguiente nivel.",
    "Teleport scroll": "Las runas chispean y el aire distorsiona mientras desapareces.",
    "Prodigious memory scroll": "Tus pasos recientes quedaron grabados en tu mente como si el mapa entero se hubiera movido contigo.",
    "Identify scroll": "Las runas arden y revelan la verdadera identidad del objeto.",
    "Remove curse scroll": "Las runas brillan y las ataduras oscuras del objeto se desvanecen.",
}

class ScrollConsumable(Consumable):
    target_prompt = "Select a target location."
    safe_effect_when_empty: Optional[str] = None
    empty_effect_color = color.orange

    def activate(self, action: actions.ItemAction) -> None:
        previously_identified = getattr(self.parent, "identified", False)
        setattr(self, "_effect_message_emitted", False)
        context = self._activate_scroll(action) or {}
        if context.get("affected", 0) == 0 and self.safe_effect_when_empty:
            self.engine.message_log.add_message(
                self.safe_effect_when_empty,
                self.empty_effect_color,
            )
        self.consume()
        if not previously_identified:
            self.parent.identify()
            effect_emitted = bool(getattr(self, "_effect_message_emitted", False))
            message = None if effect_emitted else self._format_identification_description(context)
            if message:
                self.engine.message_log.add_message(message, color.status_effect_applied)

    def _activate_scroll(self, action: actions.ItemAction) -> Optional[Dict[str, object]]:
        raise NotImplementedError()

    def _format_identification_description(self, context: Dict[str, object]) -> Optional[str]:
        affected = context.get("affected") if context else None
        if affected is not None and affected <= 0:
            return None
        description = SCROLL_IDENTIFICATION_DESCRIPTIONS.get(getattr(self.parent, "id_name", ""))
        if not description:
            return None
        safe_context = dict(context)
        return description.format(**safe_context)

    def _ensure_visible_location(self, target_xy) -> None:
        if not self.engine.game_map.visible[target_xy]:
            raise Impossible("You cannot target an area that you cannot see.")

    def _require_visible_target(
        self,
        action: actions.ItemAction,
        *,
        allow_self: bool = False,
        max_range: Optional[int] = None,
        missing_target_error: str = "You must select an enemy to target.",
        self_target_error: str = "You cannot target yourself.",
        target_too_far_error: Optional[str] = "Target too far.",
    ):
        self._ensure_visible_location(action.target_xy)
        target = action.target_actor
        if not target:
            raise Impossible(missing_target_error)
        consumer = action.entity
        if not allow_self and target is consumer:
            raise Impossible(self_target_error)
        if max_range is not None and target.distance(consumer.x, consumer.y) > max_range:
            raise Impossible(target_too_far_error or "Target too far.")
        return target


class SingleTargetScrollConsumable(ScrollConsumable):
    allow_self_target = False
    max_range: Optional[int] = None
    missing_target_error = "You must select an enemy to target."
    self_target_error = "You cannot target yourself."
    target_too_far_error = "Target too far."

    def get_action(self, consumer: Actor) -> SingleRangedAttackHandler:
        self.engine.message_log.add_message(
            self.target_prompt,
            color.needs_target,
        )
        return SingleRangedAttackHandler(
            self.engine,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )

    def _activate_scroll(self, action: actions.ItemAction) -> Optional[Dict[str, object]]:
        target = self._select_target(action)
        return self._apply_to_target(action, target)

    def _select_target(self, action: actions.ItemAction) -> Actor:
        try:
            return self._require_visible_target(
                action,
                allow_self=self.allow_self_target,
                max_range=self.max_range,
                missing_target_error=self.missing_target_error,
                self_target_error=self.self_target_error,
                target_too_far_error=self.target_too_far_error,
            )
        except Impossible:
            if not self.parent.identified and action.entity:
                return action.entity
            raise

    def _apply_to_target(self, action: actions.ItemAction, target: Actor) -> Optional[Dict[str, object]]:
        raise NotImplementedError()


class AreaTargetScrollConsumable(ScrollConsumable):
    missing_targets_error = "There are no targets in the radius."

    def __init__(self, radius: int):
        self.radius = radius

    def get_action(self, consumer: Actor) -> AreaRangedAttackHandler:
        self.engine.message_log.add_message(
            self.target_prompt,
            color.needs_target,
        )
        return AreaRangedAttackHandler(
            self.engine,
            radius=self.radius,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )

    def _activate_scroll(self, action: actions.ItemAction) -> Optional[Dict[str, object]]:
        if not self._try_ensure_visible_location(action):
            action = actions.ItemAction(action.entity, self.parent, (action.entity.x, action.entity.y))
        hits = self._apply_area_effect(action)
        return {"affected": hits}

    def _try_ensure_visible_location(self, action: actions.ItemAction) -> bool:
        try:
            self._ensure_visible_location(action.target_xy)
            return True
        except Impossible:
            if not self.parent.identified and action.entity:
                return False
            raise

    def _apply_area_effect(self, action: actions.ItemAction) -> int:
        raise NotImplementedError()

class TargetedConfusionConsumable(SingleTargetScrollConsumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns
    missing_target_error = "You must select an enemy to target."
    self_target_error = "You cannot confuse yourself!"

    def _apply_to_target(self, action: actions.ItemAction, target: Actor) -> Optional[Dict[str, object]]:
        self._effect_message(
            target,
            "Your eyes look vacant as you start to stumble around!",
            "The eyes of {name} look vacant, as it starts to stumble around!",
            color.status_effect_applied,
        )
        if target is self.engine.player:
            target.fighter.apply_player_confusion(self.number_of_turns)
        else:
            target.ai = components.ai.ConfusedEnemy(
                entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
            )
        return {"target": target.name}

class ConfusionConsumable(Consumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        target = consumer

        self._effect_message(
            consumer,
            "What... what was I doing?",
            "{name} looks completely confused.",
            color.status_effect_applied,
        )
        if consumer is self.engine.player:
            consumer.fighter.apply_player_confusion(self.number_of_turns)
        else:
            target.ai = components.ai.ConfusedEnemy(
                entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
            )
        self.consume()
        self.parent.identify()


class ParalysisConsumable(Consumable):
    def __init__(self, min_turns: int = 12, max_turns: int = 32):
        self.min_turns = min_turns
        self.max_turns = max_turns

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        turns = random.randint(self.min_turns, self.max_turns)
        self._clear_confusion(consumer)
        self._effect_message(
            consumer,
            "Your muscles seize up; you cannot move!",
            "{name}'s muscles seize up; it cannot move!",
            color.status_effect_applied,
        )
        if consumer is self.engine.player:
            consumer.fighter.apply_player_paralysis(turns)
        else:
            consumer.ai = components.ai.ParalizeEnemy(
                entity=consumer, previous_ai=consumer.ai, turns_remaining=turns,
            )
        self.consume()
        self.parent.identify()


class PetrifyConsumable(Consumable):
    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        self._clear_confusion(consumer)
        self._effect_message(
            consumer,
            "Your body turns to stone. You cannot move anymore.",
            "{name} turns to stone and cannot move anymore.",
            color.status_effect_applied,
        )
        consumer.ai = components.ai.ParalizeEnemy(
            entity=consumer, previous_ai=consumer.ai, turns_remaining=999999,
        )
        self.consume()
        self.parent.identify()

class BlindConsumable(Consumable):
    def __init__(self, number_of_turns: int, uses: int = 1):
        self.number_of_turns = number_of_turns
        #self.uses = uses

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
        target = action.target_actor

        if not self.engine.game_map.visible[action.target_xy]:
            raise Impossible("You cannot target an area that you cannot see.")
        if not target:
            raise Impossible("You must select an enemy to target.")
        if target is consumer:
            raise Impossible("Too bad idea.")
        if target.distance(consumer.x, consumer.y) > 2:
            raise Impossible("Target too far.")

        self._effect_message(
            target,
            "You are blinded!",
            "{name} is blinded!",
            color.status_effect_applied,
        )
        target.ai = components.ai.ParalizeEnemy(
            entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
        )
        
        if self.parent.uses == 0:
            self.consume()
        else:
            self.parent.uses -= 1
            
        self.parent.identify()        

class ParalisisConsumable(SingleTargetScrollConsumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns
    missing_target_error = "You must select an enemy to target."
    self_target_error = "You cannot apply Paralisis scroll on yourself!"

    def _select_target(self, action: actions.ItemAction) -> Actor:
        try:
            return super()._select_target(action)
        except Impossible:
            return action.entity

    def _apply_to_target(self, action: actions.ItemAction, target: Actor) -> Optional[Dict[str, object]]:
        self._effect_message(
            target,
            "Your skin turns gray as paralysis sets in!",
            "The skin of {name} turns gray as it becomes paralyzed!",
            color.status_effect_applied,
        )
        if target is self.engine.player:
            target.fighter.apply_player_paralysis(self.number_of_turns)
        else:
            target.ai = components.ai.ParalizeEnemy(
                entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
            )
        return {"target": target.name}

class PowerConsumable(Consumable):

    def __init__(self, number_of_turns: int, amount: int):
        self.number_of_turns = number_of_turns
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity

        self._effect_message(
            consumer,
            "You feel strong!",
            "{name} looks strong!",
            color.status_effect_applied,
        )
        consumer.fighter.gain_temporal_bonus(
            self.number_of_turns,
            self.amount,
            "strength",
            "You feel weak.",
        )

        self.consume()
        self.parent.identify()
        # import ipdb;ipdb.set_trace()
        
class TemporalEffectConsumable(Consumable):

    def __init__(
        self,
        number_of_turns: int,
        amount: int,
        attribute_affected: str,
        message_hi: Optional[str] = None,
        message_down: Optional[str] = None,
        creature_message_hi: Optional[str] = None,
        message_key: Optional[str] = None,
    ):
        self.number_of_turns = number_of_turns
        self.amount = amount
        self.attribute_affected = attribute_affected
        self.message_hi = message_hi
        self.creature_message_hi = creature_message_hi or message_hi
        self.message_down = message_down
        self.message_key = message_key

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        player_hi, creature_hi, player_end, creature_end = self._resolve_temporal_texts(
            self.message_hi,
            self.creature_message_hi,
            self.message_down,
        )
        self._effect_message(
            consumer,
            player_hi,
            creature_hi,
            color.status_effect_applied,
        )
        end_message = player_end if consumer is self.engine.player else creature_end
        consumer.fighter.gain_temporal_bonus(
            self.number_of_turns,
            self.amount,
            self.attribute_affected,
            end_message,
        )
        self.consume()
        self.parent.identify()

class RestoreStaminaConsumable(Consumable):

    def __init__(self):
        pass

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity

        consumer.fighter.stamina = consumer.fighter.max_stamina
        self._effect_message(
            consumer,
            "You feel energized!",
            "{name} looks energized!",
            color.status_effect_applied,
        )

        self.consume()
        self.parent.identify()


class IncreaseMaxStaminaConsumable(Consumable):
    def __init__(self, amount: int = 1):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        consumer.fighter.max_stamina += self.amount
        consumer.fighter.stamina = consumer.fighter.max_stamina
        self._effect_message(
            consumer,
            "You feel an enduring vigor surge through your body.",
            "{name} stands with enduring vigor.",
            color.status_effect_applied,
        )
        self.consume()
        self.parent.identify()


class IncreaseMaxHPConsumable(Consumable):
    def __init__(self, amount: int = 8):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        self._clear_confusion(consumer)
        consumer.fighter.max_hp += self.amount
        consumer.fighter.hp += self.amount
        self._effect_message(
            consumer,
            "Your life essence deepens permanently.",
            "{name} looks hardier.",
            color.status_effect_applied,
        )
        self.consume()
        self.parent.identify()


class IncreaseFOVConsumable(Consumable):
    def __init__(self, amount: int = 1):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        consumer.fighter.fov += self.amount
        self._effect_message(
            consumer,
            "Everything seems clearer than before.",
            "{name} seems to focus on everything at once.",
            color.status_effect_applied,
        )
        self.consume()
        self.parent.identify()


class BlindnessConsumable(Consumable):
    def __init__(self, min_turns: int = 12, max_turns: int = 32, amount: int = -32):
        self.min_turns = min_turns
        self.max_turns = max_turns
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        duration = random.randint(self.min_turns, self.max_turns)
        self._effect_message(
            consumer,
            "Darkness engulfs you; you can barely see anything!",
            "{name} gropes blindly!",
            color.status_effect_applied,
        )
        consumer.fighter.gain_temporal_bonus(
            duration,
            self.amount,
            "fov",
            "Shapes slowly emerge again around you.",
        )
        self.consume()
        self.parent.identify()


class TemporalFOVConsumable(Consumable):
    def __init__(self, min_turns: int = 12, max_turns: int = 32, amount: int = 6):
        self.min_turns = min_turns
        self.max_turns = max_turns
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        duration = random.randint(self.min_turns, self.max_turns)
        self._effect_message(
            consumer,
            "Your senses sharpen dramatically!",
            "{name} scans the surroundings with sharp senses!",
            color.status_effect_applied,
        )
        consumer.fighter.gain_temporal_bonus(
            duration,
            self.amount,
            "fov",
            "Your sight returns to normal.",
        )
        self.consume()
        self.parent.identify()

class HealingConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        self._clear_confusion(consumer)
        amount_recovered = consumer.fighter.heal(self.amount)

        if amount_recovered > 0:
            self._effect_message(
                consumer,
                "You consume the {item}, and recover {amount} HP!",
                "{name} consumes the {item}, recovering {amount} HP!",
                color.health_recovered,
                item=self.parent.name,
                amount=amount_recovered,
            )
            self.consume()
            self.parent.identify()
            
        else:
            #raise Impossible(f"Your health is already full.")
            self._effect_message(
                consumer,
                "Puagggh!",
                "No parece que la sustancia le afecte a esa criatura.",
                color.impossible,
            )
            self.consume()
            
class StrenghtConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount_recovered = consumer.fighter.gain_power(self.amount)

        self._effect_message(
            consumer,
            "You feel strong!",
            "{name} suddenly looks stronger!",
            color.health_recovered,
        )
        self.consume()
        self.parent.identify()

class FoodConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:

        consumer = action.entity

        if self.engine.player.fighter.satiety >= self.engine.player.fighter.max_satiety:
            #self.engine.message_log.add_message("You are not hungry")
            raise Impossible(f"You are not hungry")

        else:
            amount_recovered = consumer.fighter.eat(self.amount)

            if amount_recovered > 0:
                self._effect_message(
                    consumer,
                    "You consume the {item}.",
                    "{name} consumes the {item}.",
                    color.health_recovered,
                    item=self.parent.name,
                )
                if self.engine.player.fighter.satiety >= self.engine.player.fighter.max_satiety:
                    self.engine.player.fighter.satiety = self.engine.player.fighter.max_satiety
                    self._effect_message(
                        consumer,
                        "You are full.",
                        None,
                        color.health_recovered,
                    )
                
                self.consume()

            if amount_recovered < 0:
                self._effect_message(
                    consumer,
                    "Rotten food!",
                    "{name} spits out the rotten food!",
                    color.red,
                )
                self.consume()


            self.parent.identify()
       
class DamageConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        consumer.fighter.take_damage(self.amount)

        self._effect_message(
            consumer,
            "You take {amount} damage points!",
            "{name} writhes in pain!",
            color.red,
            amount=self.amount,
        )
        self.consume()
        self.parent.identify()
        """
        for i in self.engine.game_map.entities:
                print(i)
                self.parent.identify()
        """
        
class PoisonConsumable(Consumable):
    def __init__(self, amount: int, counter: int):
        self.amount = amount
        self.counter = counter

    def activate(self, action: actions.ItemAction) -> None:
        #import ipdb;ipdb.set_trace()
        if self.parent.identified == False:

            consumer = action.entity
            consumer.fighter.is_poisoned = True
            consumer.fighter.poison_dmg = self.amount
            poison_roll = random.randint(1, 6)
            if poison_roll <= consumer.fighter.luck:
                counter_total = self.counter - random.randint(1, 6) - consumer.fighter.poison_resistance
                if counter_total > 0:
                    consumer.fighter.poisoned_counter = counter_total
                else:
                    consumer.fighter.poisoned_counter = 0
                    self._effect_message(
                        consumer,
                        "You are poison resistant.",
                        "{name} is poison resistant.",
                        color.descend,
                    )
            else:
                counter_total = self.counter - consumer.fighter.poison_resistance
                if counter_total > 0:
                    consumer.fighter.poisoned_counter = counter_total
                else:
                    consumer.fighter.poisoned_counter = 0
                    self._effect_message(
                        consumer,
                        "You are poison resistant.",
                        "{name} is poison resistant.",
                        color.descend,
                    )
            
            self.consume()
            self.parent.identify()

        # Si la poción está identificada, el consumidor envenena su ataque.
        else:
            consumer = action.entity
            consumer.fighter.poisons_on_hit = True
            self.consume()

            # TODO: Relativizar mensaje, para que "weapon" sea dinámico.
            self._effect_message(
                consumer,
                "You smear the edge of your weapon with poison.",
                "{name} smears the edge of their weapon with poison.",
                color.descend,
            )
        
class AntidoteConsumable(Consumable):
    def __init__(self):
        pass

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        if consumer.fighter.is_poisoned == True:
            consumer.fighter.is_poisoned = False
            consumer.fighter.poisoned_counter = 0
            self._effect_message(
                consumer,
                "You are no longer poisoned.",
                "{name} is no longer poisoned.",
                color.green,
            )
            
        else:
            self._effect_message(
                consumer,
                "This potion does nothing.",
                "The potion seems to do nothing to {name}.",
                color.white,
            )
        
        self.consume()
        self.parent.identify()


class FireballDamageConsumable(AreaTargetScrollConsumable):
    target_prompt = "Select a target location."
    scatter_chance = 0.35
    safe_effect_when_empty = "The fireball roars outward, but nothing was close enough to burn."

    def __init__(self, damage: int, radius: int):
        super().__init__(radius=radius)
        self.damage = damage

    def _apply_area_effect(self, action: actions.ItemAction) -> int:
        original_target = action.target_xy
        detonation_center = self._resolve_actual_center(original_target)
        hits = 0
        if detonation_center != original_target:
            self.engine.message_log.add_message(
                "The fireball veers off and detonates nearby!",
                color.orange,
            )
        self._animate_fireball(detonation_center)
        targets = self._gather_fire_targets()
        for entity in targets:
            if entity.distance(*detonation_center) <= self.radius:
                self._effect_message(
                    entity,
                    "You are engulfed in a fiery explosion, taking {damage} damage!",
                    "{name} is engulfed in a fiery explosion, taking {damage} damage!",
                    color.red,
                    damage=self.damage,
                )
                ignite_chance = self._resolve_ignite_chance(entity)
                entity.fighter.apply_fire_damage(self.damage, ignite_chance=ignite_chance)
                hits += 1
        return hits

    def _resolve_actual_center(self, target_xy):
        if random.random() >= self.scatter_chance:
            return target_xy
        x, y = target_xy
        offsets = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1),
        ]
        candidates = []
        game_map = self.engine.game_map
        for dx, dy in offsets:
            candidate = (x + dx, y + dy)
            if game_map.in_bounds(*candidate):
                candidates.append(candidate)
        if not candidates:
            return target_xy
        return random.choice(candidates)

    def _resolve_ignite_chance(self, target) -> Optional[float]:
        name = getattr(target, "name", "").lower()
        if name == "door":
            return 1.0
        return None

    def _gather_fire_targets(self):
        targets = []
        for entity in set(self.engine.game_map.entities):
            fighter = getattr(entity, "fighter", None)
            if fighter:
                targets.append(entity)
        return targets

    def _animate_fireball(self, center: Tuple[int, int]) -> None:
        tiles = self._collect_blast_tiles(center)
        if not tiles:
            return
        patterns = [
            ([".", "`", ","], color.orange, 0.04),
            (["*", "+", "x"], color.red, 0.05),
            ([".", " "], color.yellow, 0.04),
        ]
        frames = []
        for chars, fg, duration in patterns:
            glyphs = [
                (tx, ty, random.choice(chars), fg)
                for (tx, ty) in tiles
            ]
            frames.append((glyphs, duration))
        self.engine.queue_animation(frames)

    def _collect_blast_tiles(self, center: Tuple[int, int]) -> List[Tuple[int, int]]:
        cx, cy = center
        tiles: List[Tuple[int, int]] = []
        game_map = self.engine.game_map
        for dx in range(-self.radius, self.radius + 1):
            for dy in range(-self.radius, self.radius + 1):
                tx = cx + dx
                ty = cy + dy
                if not game_map.in_bounds(tx, ty):
                    continue
                if dx * dx + dy * dy <= self.radius * self.radius:
                    tiles.append((tx, ty))
        return tiles

class LightningDamageConsumable(ScrollConsumable):
    def __init__(self, minimum_damage: int = 9, maximum_damage: int = 15, maximum_range: int = 12):
        self.minimum_damage = minimum_damage
        self.maximum_damage = maximum_damage
        self.maximum_range = maximum_range

    def _activate_scroll(self, action: actions.ItemAction) -> Optional[Dict[str, object]]:
        consumer = action.entity
        target, path = self._select_target(consumer)
        damage = random.randint(self.minimum_damage, self.maximum_damage)
        self._animate_lightning(path)
        self._effect_message(
            target,
            "A lightning bolt strikes you with a loud thunder, for {damage} damage!",
            "A lightning bolt strikes {name} with a loud thunder, for {damage} damage!",
            color.red,
            damage=damage,
        )
        target.fighter.take_damage(damage)
        return {"target": target.name, "affected": 1}

    def _select_target(self, consumer: Actor) -> Tuple[Actor, List[Tuple[int, int]]]:
        candidates = []
        best_distance = float("inf")
        for actor in self.engine.game_map.actors:
            if actor is consumer:
                continue
            path = self._find_path_to(consumer, actor)
            if not path:
                continue
            distance = len(path)
            if distance < best_distance:
                best_distance = distance
                candidates = [(actor, path)]
            elif distance == best_distance:
                candidates.append((actor, path))
        if candidates:
            return random.choice(candidates)
        return consumer, [(consumer.x, consumer.y)]

    def _find_path_to(self, start: Actor, goal: Actor) -> Optional[List[Tuple[int, int]]]:
        if start is goal:
            return [(start.x, start.y)]
        from collections import deque

        game_map = self.engine.game_map
        start_pos = (start.x, start.y)
        goal_pos = (goal.x, goal.y)
        queue = deque([start_pos])
        visited = {start_pos}
        parents = {start_pos: None}
        distances = {start_pos: 0}

        while queue:
            x, y = queue.popleft()
            dist = distances[(x, y)]
            if dist >= self.maximum_range:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not game_map.in_bounds(nx, ny):
                    continue
                if (nx, ny) in visited:
                    continue
                if (nx, ny) != goal_pos:
                    if not game_map.tiles["walkable"][nx, ny]:
                        continue
                    blocking = game_map.get_blocking_entity_at_location(nx, ny)
                    if blocking and blocking is not goal:
                        continue
                visited.add((nx, ny))
                parents[(nx, ny)] = (x, y)
                distances[(nx, ny)] = dist + 1
                if not game_map.tiles["walkable"][nx, ny]:
                    continue
                queue.append((nx, ny))
                if (nx, ny) == goal_pos:
                    path = []
                    current = (nx, ny)
                    while current:
                        path.append(current)
                        current = parents[current]
                    path.reverse()
                    return path
        return None

    def _animate_lightning(self, path: List[Tuple[int, int]]) -> None:
        if not path:
            return
        frames = []
        chars = ["-", "=", "~"]
        colors = [color.blue, color.white, color.orange]
        for char, fg in zip(chars, colors):
            glyphs = [
                (x, y, char, fg)
                for (x, y) in path
                if self.engine.game_map.in_bounds(x, y)
            ]
            frames.append((glyphs, 0.04))
        self.engine.queue_animation(frames)


class DescendScrollConsumable(ScrollConsumable):
    """Transport the reader to a random free tile on the next floor."""

    def _activate_scroll(self, action: actions.ItemAction) -> Optional[Dict[str, object]]:
        consumer = action.entity
        game_world = self.engine.game_world
        if game_world.current_floor >= len(game_world.levels):
            raise Impossible("You can't descend any further.")

        def random_spawn(next_map):
            return game_world._find_random_free_tile(next_map)

        if not self.engine.perform_floor_transition(
            lambda: game_world.advance_floor(spawn_selector=random_spawn)
        ):
            raise Impossible("You can't descend any further.")
        self._effect_message(
            consumer,
            "Un remolino de runas se abre bajo ti y caes en el siguiente nivel.",
            "{name} desaparece en un remolino de runas.",
            color.descend,
        )
        return {"affected": 1}


class TeleportScrollConsumable(ScrollConsumable):
    """Move the reader to a random free tile on the current floor."""

    def _activate_scroll(self, action: actions.ItemAction) -> Optional[Dict[str, object]]:
        consumer = action.entity
        game_world = self.engine.game_world
        current_map = self.engine.game_map
        x, y = game_world._find_random_free_tile(current_map)
        consumer.place(x, y, current_map)
        self.engine.update_fov()
        self._effect_message(
            consumer,
            "Las runas estallan y apareces en un punto inesperado del mapa.",
            "{name} desaparece en un destello de runas.",
            color.status_effect_applied,
        )
        return {"affected": 1}


class IdentificationScrollConsumable(ScrollConsumable):
    """Let the reader identify an unidentified inventory item."""

    def _unidentified_items(self, consumer: Actor):
        return [
            item
            for item in consumer.inventory.items
            if not getattr(item, "identified", False) and item is not self.parent
        ]

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        if not self._unidentified_items(consumer):
            self.engine.message_log.add_message(
                "No tienes objetos sin identificar en tu inventario.",
                color.impossible,
            )
            return None
        return InventoryIdentifyHandler(self.engine, self.parent)

    def _activate_scroll(self, action: actions.IdentifyItemAction) -> Optional[Dict[str, object]]:
        consumer = action.entity
        target_item = getattr(action, "target_item", None)
        if not target_item:
            raise Impossible("Debes elegir un objeto para identificar.")
        if target_item not in consumer.inventory.items:
            raise Impossible("Sólo puedes identificar objetos de tu inventario.")
        if getattr(target_item, "identified", False):
            raise Impossible("Ese objeto ya está identificado.")
        target_item.identify()
        self.engine.message_log.add_message(
            f"Identificas {target_item.name}.",
            color.status_effect_applied,
        )
        return {"affected": 1, "item": target_item.name}


class ProdigiousMemoryConsumable(ScrollConsumable):
    """Grant the reader permanent super memory for the current campaign."""

    def _activate_scroll(self, action: actions.ItemAction) -> Optional[Dict[str, object]]:
        consumer = action.entity
        if consumer is self.engine.player:
            consumer.fighter.super_memory = True
        self._effect_message(
            consumer,
            "Las runas se enlazan con tu mente y recuerdas cada rincón de la mazmorra.",
            "{name} parece caminar conociendo cada rincón.",
            color.status_effect_applied,
        )
        return {"affected": 1}


class RemoveCurseConsumable(ScrollConsumable):
    """Remove the cursed status from a single item in the inventory."""

    target_prompt = "Selecciona un objeto a liberar de su maldición."

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        if not consumer.inventory.items:
            self.engine.message_log.add_message(
                "No tienes objetos en tu inventario.",
                color.impossible,
            )
            return None
        return InventoryRemoveCurseHandler(self.engine, self.parent)

    def _activate_scroll(self, action: actions.RemoveCurseItemAction) -> Optional[Dict[str, object]]:
        consumer = action.entity
        target_item = getattr(action, "target_item", None)
        if not target_item:
            raise Impossible("Debes elegir un objeto.")
        if target_item not in consumer.inventory.items:
            raise Impossible("Sólo puedes afectar a objetos de tu inventario.")
        equippable = getattr(target_item, "equippable", None)
        if not equippable:
            self._effect_message(
                consumer,
                "Nada sucede; el objeto no está encantado.",
                None,
                color.impossible,
            )
            return {"affected": 0, "item": target_item.name}
        if not getattr(equippable, "cursed", False):
            self._effect_message(
                consumer,
                "Sientes que no hay maldición que romper en ese objeto.",
                None,
                color.orange,
            )
            return {"affected": 0, "item": target_item.name}
        equippable.cursed = False
        self._effect_message(
            consumer,
            f"Sientes cómo las runas liberan tu {target_item.name}.",
            "{name} brilla un instante mientras una maldición se rompe.",
            color.status_effect_applied,
        )
        return {"affected": 1, "item": target_item.name}
