# Aquí definimios el item consumible base y diseñamos los efectos de los items "consumibles"

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import actions
import color
import components.ai
import components.inventory
from components.base_component import BaseComponent
from exceptions import Impossible
from input_handlers import (
    ActionOrHandler,
    AreaRangedAttackHandler,
    SingleRangedAttackHandler,
)

if TYPE_CHECKING:
    from entity import Actor, Item


class Consumable(BaseComponent):
    parent: Item

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
            """
            # Identificación automática por consumo:
            import gc
            from entity import Item
            #self.parent.identified == True
            for obj in gc.get_objects():
                if isinstance(obj, Item):
                    # Para que sólo identifique el mismo tipo de item que se consuma:
                    if obj.id_name == entity.id_name:
                        obj.identify()
            """

class ConfusionConsumable(Consumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns

    #def get_action(self, consumer: Actor) -> Optional[actions.Action]:
    def get_action(self, consumer: Actor) -> SingleRangedAttackHandler:
        self.engine.message_log.add_message(
            "Select a target location.", color.needs_target
        )
        #self.engine.event_handler = SingleRangedAttackHandler(
        return SingleRangedAttackHandler(
            self.engine,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )
        #return None

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        target = action.target_actor

        if not self.engine.game_map.visible[action.target_xy]:
            raise Impossible("You cannot target an area that you cannot see.")
        if not target:
            raise Impossible("You must select an enemy to target.")
        if target is consumer:
            raise Impossible("You cannot confuse yourself!")

        self.engine.message_log.add_message(
            f"The eyes of the {target.name} look vacant, as it starts to stumble around!",
            color.status_effect_applied,
        )
        target.ai = components.ai.ConfusedEnemy(
            entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
        )
        self.consume()
        self.parent.identify()

class SelfConfusionConsumable(Consumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns


    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        target = consumer


        self.engine.message_log.add_message(
            f"What... what was I doing?",
            color.status_effect_applied,
        )
        target.ai = components.ai.ConfusedEnemy(
            entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
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

        self.engine.message_log.add_message(
            f"The {target.name} is blinded!",
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

class ParalisisConsumable(Consumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns

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
            raise Impossible("You cannot apply Paralisis scroll on yourself!")

        self.engine.message_log.add_message(
            f"The skin of the {target.name} look gray, as it starts to paralize!",
            color.status_effect_applied,
        )
        target.ai = components.ai.ParalizeEnemy(
            entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns,
        )
        
        self.consume() 
        self.parent.identify()

class PowerConsumable(Consumable):

    def __init__(self, number_of_turns: int, amount: int):
        self.number_of_turns = number_of_turns
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity

        #consumer.fighter.gain_temporal_power(self.number_of_turns, self.amount)
        consumer.fighter.gain_temporal_bonus(
            self.number_of_turns, self.amount, 
            "base_power",
            "You feel strong!",
        )

        self.consume()
        self.parent.identify()
        # import ipdb;ipdb.set_trace()
        
class TemporalEffectConsumable(Consumable):

    def __init__(self, number_of_turns: int, amount: int, attribute_affected: str, message_hi: str, message_down: str):
        self.number_of_turns = number_of_turns
        self.amount = amount
        self.attribute_affected = attribute_affected
        self.message_hi = message_hi
        self.message_down = message_down

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity

        #consumer.fighter.gain_temporal_power(self.number_of_turns, self.amount)
        consumer.fighter.gain_temporal_bonus(
            self.number_of_turns, 
            self.amount, 
            self.attribute_affected,
            self.message_hi,
            self.message_down,
        )
        # import ipdb;ipdb.set_trace()
        self.consume()
        self.parent.identify()

class RestoreStaminaConsumable(Consumable):

    def __init__(self):
        pass

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity

        consumer.fighter.stamina = consumer.fighter.max_stamina
        self.engine.message_log.add_message(
            f"You feel energized!",
            color.status_effect_applied,
        )

        self.consume()
        self.parent.identify()

class HealingConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount_recovered = consumer.fighter.heal(self.amount)

        if amount_recovered > 0:
            self.engine.message_log.add_message(
                f"You consume the {self.parent.name}, and recover {amount_recovered} HP!",
                color.health_recovered,
            )
            self.consume()
            self.parent.identify()
            
        else:
            #raise Impossible(f"Your health is already full.")
            self.engine.message_log.add_message(
                f"Puagggh!"
            )
            self.consume()
            
class StrenghtConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount_recovered = consumer.fighter.gain_power(self.amount)

        self.engine.message_log.add_message(
            f"You feel strong!",
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
                self.engine.message_log.add_message(
                    f"You consume the {self.parent.name}",
                    color.health_recovered,
                )
                if self.engine.player.fighter.satiety >= self.engine.player.fighter.max_satiety:
                    self.engine.player.fighter.satiety = self.engine.player.fighter.max_satiety
                    self.engine.message_log.add_message("You are full")
                
                self.consume()

            if amount_recovered < 0:
                self.engine.message_log.add_message(
                    f"Rotten food!",
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

        self.engine.message_log.add_message(
            f"You take {self.amount} damage points!",
            color.red,
        )
        self.consume()
        self.parent.identify()
        """
        for i in self.engine.game_map.entities:
                print(i)
                self.parent.identify()
        """
        
class PosionConsumable(Consumable):
    def __init__(self, amount: int, counter: int):
        self.amount = amount
        self.counter = counter

    def activate(self, action: actions.ItemAction) -> None:
        #import ipdb;ipdb.set_trace()
        if self.parent.identified == False:

            consumer = action.entity
            consumer.fighter.is_poisoned = True
            consumer.fighter.poison_dmg = self.amount
            consumer.fighter.poisoned_counter = self.counter
            
            self.consume()
            self.parent.identify()

        else:
            # self.parent.identify()
            # if self.parent.id_name == 'Posion potion' and self.parent.identified == False and self.parent.name != 'Posion potion':
            #     self.parent.identify()
            consumer = action.entity
            consumer.fighter.poisons_on_hit = True
            self.consume()

            self.engine.message_log.add_message("You smear the edge of your weapon with poison.", color.descend)
        
class AntidoteConsumable(Consumable):
    def __init__(self):
        pass

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        if consumer.fighter.is_poisoned == True:
            consumer.fighter.is_poisoned = False
            consumer.fighter.poisoned_counter = 0
            self.engine.message_log.add_message(
            f"You are no longer poisoned.",
            color.green,
            )
            
        else:
            self.engine.message_log.add_message(
            f"This potion does nothing.",
            color.white,
            )
        
        self.consume()
        self.parent.identify()


class FireballDamageConsumable(Consumable):
    def __init__(self, damage: int, radius: int):
        self.damage = damage
        self.radius = radius

    def get_action(self, consumer: Actor) -> AreaRangedAttackHandler:
        self.engine.message_log.add_message(
            "Select a target location.", color.needs_target
        )
        return AreaRangedAttackHandler(
            self.engine,
            radius=self.radius,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )

    def activate(self, action: actions.ItemAction) -> None:
        target_xy = action.target_xy

        if not self.engine.game_map.visible[target_xy]:
            self.parent.identify()
            raise Impossible("You cannot target an area that you cannot see.")

        targets_hit = False
        for actor in self.engine.game_map.actors:
            if actor.distance(*target_xy) <= self.radius:
                self.engine.message_log.add_message(
                    f"The {actor.name} is engulfed in a fiery explosion, taking {self.damage} damage!"
                )
                actor.fighter.take_damage(self.damage)
                targets_hit = True

        if not targets_hit:
            self.parent.identify()
            raise Impossible("There are no targets in the radius.")
        
        self.consume()
        self.parent.identify()

class LightningDamageConsumable(Consumable):
    def __init__(self, damage: int, maximum_range: int):
        self.damage = damage
        self.maximum_range = maximum_range

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
                f"A lighting bolt strikes the {target.name} with a loud thunder, for {self.damage} damage!"
            )
            target.fighter.take_damage(self.damage)
            self.consume()
            self.parent.identify()
        else:
            self.parent.identify()
            raise Impossible("No enemy is close enough to strike.")