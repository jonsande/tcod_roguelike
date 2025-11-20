# Aquí se definen las acciones (acciones-tipo) a las que se llamará
# desde input_handlers.py

# We define three classes: Action, EscapeAction, and MovementAction. 
# EscapeAction and MovementAction are sub-classes of Action.

from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, List

import color
from entity import Actor
import exceptions
import random
from settings import DEBUG_MODE
from audio import play_player_footstep, play_door_open_sound, play_door_close_sound

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Entity, Item

from color import bcolors

POTION_IDENTIFICATION_EXCEPTIONS = {
    "Antidote",
    "Potion of Flash Sight",
    "Potion of True Sight",
    "Amphetamine brew",
}
PRECISION_POTION_ID = "Amphetamine brew"
POTION_IDENTIFICATION_DESCRIPTIONS = {
    "Health potion": "{target} parece recuperar sus heridas.",
    "Strength potion": "Los músculos de {target} se tensan con nueva fuerza.",
    "Poison potion": "La piel de {target} adquiere un matiz enfermizo.",
    "Power brew": "{target} aprieta los puños con furia renovada.",
    "Restore stamina Potion": "{target} respira con energía renovada.",
    "Potion of Lasting Vigor": "{target} mantiene una postura más firme.",
    "Life potion": "{target} parece más resistente.",
    "Potion of True Sight": "Los ojos de {target} centellean con visión aguda.",
    "Potion of Flash Sight": "{target} examina el entorno con rapidez febril.",
    "Potion of Blinding Darkness": "{target} palpa el aire a ciegas.",
    "Confusion potion": "{target} luce completamente desorientado.",
    "Self paralysis potion": "{target} queda rígido como una estatua.",
    "Petrification potion": "{target} se vuelve de piedra.",
}


# la clase padre 'acción'
class Action:

    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.entity.gamemap.engine

    def perform(self) -> None:
        """Perform this action with the objects needed to determine its scope.

        `self.engine` is the scope this action is being performed in.

        `self.entity` is the object performing the action.

        This method must be overridden by Action subclasses.
        """
        raise NotImplementedError()
    

class PickupAction(Action):
    """Pickup an item and add it to the inventory, if there is room for it."""

    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> None:
        actor_location_x = self.entity.x
        actor_location_y = self.entity.y
        inventory = self.entity.inventory

        for item in self.engine.game_map.items:
            if actor_location_x == item.x and actor_location_y == item.y:
                if len(inventory.items) >= inventory.capacity:
                    raise exceptions.Impossible("Your inventory is full.")

                self.engine.game_map.entities.remove(item)
                item.parent = self.entity.inventory
                inventory.items.append(item)

                self.engine.message_log.add_message(f"You picked up the {item.name}!")

                # TIME SYSTEM
                #self.entity.fighter.current_energy_points -= 10
                self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
                if DEBUG_MODE:
                    print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in PickupAction")
                    print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

                return

        raise exceptions.Impossible("There is nothing here to pick up.")


class ItemAction(Action):
    def __init__(
        self, entity: Actor, item: Item, target_xy: Optional[Tuple[int, int]] = None
    ):
        super().__init__(entity)
        self.item = item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(*self.target_xy)

    def perform(self) -> None:
        """Invoke the items ability, this action will be given to provide context."""
        if self.item.consumable:
            self.item.consumable.activate(self)
                    

class DropItem(ItemAction):
    def perform(self) -> None:
        if self.entity.equipment.item_is_equipped(self.item):
            self.entity.equipment.toggle_equip(self.item)

        #TIME SYSTEM
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        if DEBUG_MODE:
            print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in DropItem")
            print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

        self.entity.inventory.drop(self.item)


class EquipAction(Action):
    def __init__(self, entity: Actor, item: Item):
        super().__init__(entity)

        self.item = item

    def perform(self) -> None:

        # TIME SYSTEM
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        if DEBUG_MODE:
            print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in EquipAction")
            print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

        self.entity.equipment.toggle_equip(self.item)


class TakeStairsAction(Action):
    def perform(self) -> None:
        """
        Take the stairs, if any exist at the entity's location.
        """

        at_downstairs = (
            self.engine.game_map.downstairs_location
            and (self.entity.x, self.entity.y) == self.engine.game_map.downstairs_location
        )
        at_upstairs = (
            self.engine.game_map.upstairs_location
            and (self.entity.x, self.entity.y) == self.engine.game_map.upstairs_location
        )

        if at_downstairs:

            # TIME SYSTEM
            # Bajar escaleras gasta puntos de tiempo
            #self.entity.fighter.current_energy_points -= 10
            self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
            if DEBUG_MODE:
                print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in TakeStairsAction")
                print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

            if self.engine.game_world.current_floor > 1:

                # Se gana experiencia por bajar escaleras (proporcional al nivel de mazmorra)
                # y por enemigos que no hayan sido provocados (stealth system)
                unaware_enemies = 0

                for entity in set(self.engine.game_map.actors) - {self.engine.player}:

                    if entity.fighter.aggravated == False:
                        # Las entidades dummie también cuentan, pues
                        # la idea es dar puntos por no hacer ruido.
                        unaware_enemies += 1
                        if self.engine.debug == True:
                            print(f"DEBUG: {entity.name} aggravated: {entity.fighter.aggravated}")

                print(f"DEBUG: Unaware_enemies = {unaware_enemies}")

                xp_amount = (self.engine.game_world.current_floor * 2) + (unaware_enemies * self.engine.game_world.current_floor)
                self.entity.level.add_xp(xp_amount)

                print(f"Total level xp gained: [{self.engine.game_world.current_floor} (current floor) * 5] + [{unaware_enemies} (unaware enemies) * {self.engine.game_world.current_floor} (current floor)")
            
            # Reinicia el contador para la generación de monstruos
            self.engine.spawn_monsters_counter = 0

            if not self.engine.game_world.advance_floor():
                raise exceptions.Impossible("You can't descend any further.")

            self.engine.message_log.add_message(
                "You descend the staircase.", color.descend
                )
            print(f"{color.bcolors.OKCYAN}{self.entity.name} descends the staircase.{color.bcolors.ENDC}")

        elif at_upstairs:

            self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
            if DEBUG_MODE:
                print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in TakeStairsAction (ascend)")
                print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

            if not self.engine.game_world.retreat_floor():
                raise exceptions.Impossible("You can't ascend any further.")

            self.engine.spawn_monsters_counter = 0

            self.engine.message_log.add_message(
                "You ascend the staircase.", color.ascend
            )
        else:
            raise exceptions.Impossible("There are no stairs here.")


class ActionWithDirection(Action):

    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)

        self.dx = dx
        self.dy = dy

    @property
    def dest_xy(self) -> Tuple[int, int]:
        """Returns this actions destination."""
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        """Return the blocking entity at this actions destination.."""
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)
    
    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(*self.dest_xy)

    def perform(self) -> None:
        raise NotImplementedError()


class ThrowItemAction(Action):
    def __init__(self, entity: Actor, item: Item, target_xy: Tuple[int, int]) -> None:
        super().__init__(entity)
        self.item = item
        self.target_xy = target_xy

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(*self.target_xy)

    def is_dummy_object(self, obj):
        from components.ai import Dummy
        return isinstance(obj, Dummy)

    def perform(self) -> None:
        
        if self.item.throwable == False:
            raise exceptions.Impossible("You can't throw this")

        dest_x, dest_y = self.target_xy

        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            raise exceptions.Impossible("Invalid target")

        if not self.engine.game_map.visible[dest_x, dest_y]:
            raise exceptions.Impossible("You cannot target a location you cannot see.")

        max_distance = 4 + self.entity.fighter.strength
        if self.entity.distance(dest_x, dest_y) > max_distance:
            raise exceptions.Impossible("That target is too far away.")

        path = self._compute_throw_path(self.entity.x, self.entity.y, dest_x, dest_y)
        self._animate_throw(path)

        target = self.target_actor
        if self._is_potion(self.item):
            self._handle_potion_throw(target, dest_x, dest_y)
            self._spend_throw_cost()
            return

        if self.entity.fighter.stamina <= 0:
            self.engine.message_log.add_message("You are exhausted!", color.red)
            raise exceptions.Impossible("")
        
        # TODO: el cálculo de impacto hay que rediseñarlo
        hit_dice = random.randint(1, 6) + self.entity.fighter.to_hit

        # Desequipar objeto (si está equipado)
        if self.entity.equipment.item_is_equipped(self.item):
            self.entity.equipment.toggle_equip(self.item)

        # Colocar el objeto lanzado en la casilla del objetivo
        self.entity.inventory.throw(self.item, dest_x, dest_y)

        # Bugfix: reset mouse location after throwing an item
        self.engine.mouse_location = (0, 0)

        if not target:
            self._spend_throw_cost()
            return

        # Mecánica backstab/stealth/sigilo (beta)
        # Bonificador al impacto
        if self.is_dummy_object(target.ai) == False:
            if target.fighter.aggravated == False:
                #import ipdb;ipdb.set_trace()
                #TODO: Revisar este hit_dice
                hit_dice = hit_dice + self.entity.fighter.luck + self.entity.fighter.base_stealth
                if self.engine.debug == True:
                    print("DEBUG: (Bonificador al impacto) ATAQUE SIGILOSO!")

        # Si impacta
        if hit_dice > target.fighter.defense:

            if self.entity is self.engine.player:
                damage_color = color.health_recovered
                # Despertar durmiente en caso de ser golpeado (aun sin daño)
                from components.ai import HostileEnemy, SleepingEnemy
                if isinstance(target, Actor) and isinstance(target.ai, SleepingEnemy):
                    target.ai = HostileEnemy(target)
            else:
                damage_color = color.red
            
            # Mecánica ataque envenenado
            if self.entity.fighter.poisons_on_hit == True:

                from components.ai import Dummy
                #if isinstance(target.ai, Dummy) == False:
                if self.is_dummy_object(target.ai) == False:

                    poison_roll = random.randint(1, 6)

                    if poison_roll > 1:

                        if self.entity is self.engine.player:
                            print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                "{target.name} is POISONED! (The {self.entity.name} was poisonous)", 
                                damage_color
                                )
                            
                        else:
                            print(f"Your are POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                "You are POISONED! (The {self.entity.name} was poisonous)", 
                                damage_color
                                )

                        target.fighter.is_poisoned = True
                        target.fighter.poisoned_counter += 5
                        target.fighter.poison_dmg = 1
                        self.entity.fighter.poisons_on_hit = False

            #damage = self.entity.fighter.power + random.randint(self.entity.fighter.weapon_proficiency[0], self.entity.fighter.weapon_proficiency[1]) - target.fighter.armor_value
            
            # if hasattr(self.item, 'equippable'):
            #     weapon_dmg = getattr(self.item.equippable.weapon_dmg, "weapon_dmg", 0) #Creo que esta sería la manera más simple de hacerlo.
            # damage = (self.entity.fighter.strength + (weapon_dmg * self.entity.fighter.weapon_proficiency)) - target.fighter.armor_value
            # damage = round(damage)

            # TODO: Revisar fórmula de daño al lanzar objetos. Tener en cuenta que pueden
            # lanzarse armas como dagas y objetos que no son armas.
            total_equipment_dmg_bonus = getattr(self.entity.fighter, "total_equipment_dmg", 0)
            print(f"DEBUG: total_equipment_dmg en ThrowItemAction: {total_equipment_dmg_bonus}")
            damage = ((self.entity.fighter.strength + total_equipment_dmg_bonus) * self.entity.fighter.weapon_proficiency) - target.fighter.armor_value
            damage = round(damage)

            # THROWING DAMAGE CALCULATION
            if self.item.equippable.equipment_type.name == "WEAPON":

                strength = self.entity.fighter.strength
                weapon_dmg_dice_info = self.item.equippable.weapon_dmg_dice_info
                weapon_dmg_bonus = self.item.equippable.weapon_dmg_bonus
                no_weapon_dmg_bonus = self.entity.fighter.non_weapon_dmg_bonus
                total_equipment_dmg_bonus = self.entity.fighter.total_equipment_dmg_bonus
                proficiency = self.entity.fighter.weapon_proficiency
                weapon_dmg_dice_roll = self.item.equippable.weapon_dmg_dice
                
                print(f"{bcolors.WARNING}Calculating THROWING damage with the following stats:{bcolors.ENDC}")
                print("Throwing weapon: ", self.item.name)
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} strength: {strength}")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_dice_info: {weapon_dmg_dice_info}")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_dice_roll: {weapon_dmg_dice_roll}")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_bonus: {weapon_dmg_bonus}")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} no_weapon_dmg_bonus: {no_weapon_dmg_bonus}")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} (total_equipment_dmg_bonus: {total_equipment_dmg_bonus})")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} proficiency: {proficiency}")
                if target.fighter:
                    print(f"{bcolors.WARNING}{target.name}{bcolors.ENDC} armor_value: {target.fighter.armor_value}")
        
                #total_equipment_dmg_bonus = getattr(self.entity.fighter, "total_equipment_dmg_bonus", 0)
                #import ipdb;ipdb.set_trace()
                # El arma lanzada ya no se encuentra equipada, por eso hay que sumar su bonus aparte
                damage = ((strength + weapon_dmg_dice_roll + weapon_dmg_bonus + total_equipment_dmg_bonus) * self.entity.fighter.weapon_proficiency) - target.fighter.armor_value
                damage = round(damage)
                print(f"{bcolors.WARNING}--> Final THROWING damage: {damage}{bcolors.ENDC}")

            else:
                # Si no es un arma, hacer daño básico
                print(f"{bcolors.WARNING}Calculating THROWING damage (NON-WEAPON) with the following stats:{bcolors.ENDC}")
                print("Throwing weapon: ", self.item.name)
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} strength: {self.entity.fighter.strength}")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} no_weapon_dmg_bonus: {self.entity.fighter.non_weapon_dmg_bonus}")
                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} proficiency: {self.entity.fighter.weapon_proficiency}")
                damage = (self.entity.fighter.strength + self.entity.fighter.non_weapon_dmg_bonus) * self.entity.fighter.weapon_proficiency - target.fighter.armor_value
                damage = round(damage)
                print(f"{bcolors.WARNING}--> Final THROWING damage (non-weapon): {damage}{bcolors.ENDC}")


            # Mecánica backstab/stealth/sigilo (beta)
            # Bonificador al daño
            if isinstance(target, Actor):
                if self.is_dummy_object(target.ai) == False:
                    if target.fighter.aggravated == False:
                        damage = (damage + self.entity.fighter.luck) * 2

                        if self.engine.debug == True:
                            print("DEBUG: DAÑO BACKSTAB EXTRA: ", damage)

                        self.engine.message_log.add_message("Successful stealth attack!", damage_color)

                        # Experiencia extra
                        if self.entity == self.engine.player:
                            if self.engine.debug == True:
                                print("DEBUG: EXPERIENCIA EXTRA (stealth attack): ", damage)
                            self.engine.player.level.add_xp(target.level.xp_given)

                        target.fighter.aggravated = True

            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name} ({hit_dice} VS {target.fighter.defense})"

            # Si hace daño...
            if damage > 0:

                print(f"{attack_desc} for {damage} dmg points.")
                self.engine.message_log.add_message(f"{attack_desc} for {damage} dmg points.", damage_color)

                target.fighter.hp -= damage

            # Si no hace daño
            else:

                # Reseteamos la BONIFICACIÓN
                #if self.entity.fighter.to_hit_counter > 0:
                    # se resta el bonificador al daño...
                    #self.entity.fighter.strength -= self.entity.fighter.to_power_counter
                    # ...o a la tirada de daño
                    #self.entity.fighter.weapon_proficiency[1] -= self.entity.fighter.to_power_counter
                    # ...o al to hit
                    #self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter

                    # reseteamos el contador de bonificación
                    #self.entity.fighter.to_hit_counter = 0


                print(f"{attack_desc} but does no damage.")

                self.engine.message_log.add_message("{attack_desc} but does no damage.", damage_color)
        
        # Si no impacta:
        else:

            if self.entity is self.engine.player or self.entity.name == "Adventurer":
                failure_color = color.red
            else:
                failure_color = color.health_recovered
            

            # Reseteamos la BONIFICACIÓN
            if self.entity.fighter.to_hit_counter > 0:
                # se resta el bonificador al daño...
                #self.entity.fighter.strength -= self.entity.fighter.to_power_counter
                # ...o a la tirada de daño
                #self.entity.fighter.weapon_proficiency[1] -= self.entity.fighter.to_power_counter
                # ...o al to hit
                #self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                self.entity.fighter.base_to_hit -= 1

                # reseteamos el contador de bonificación
                #self.entity.fighter.to_hit_counter = 0
                self.entity.fighter.to_hit_counter -= 1


            # if target_visible or attacker_visible:
            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
            print(f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})")
            self.engine.message_log.add_message(
                f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})",
                failure_color,
            )

        self._spend_throw_cost()


    def _is_potion(self, item: Item) -> bool:
        return getattr(item, "char", None) == "!" and item.consumable is not None

    def _handle_potion_throw(self, target: Optional[Actor], dest_x: int, dest_y: int) -> None:
        self.engine.message_log.add_message(
            f"You throw the {self.item.name}. The vial shatters on impact!",
            color.orange,
        )
        if target and self.is_dummy_object(target.ai) == False:
            self._apply_potion_effect(target)
        else:
            self.item.consumable.consume()

    def _apply_potion_effect(self, target: Actor) -> None:
        consumable = self.item.consumable
        if not consumable:
            return

        potion_id = getattr(self.item, "id_name", self.item.name)
        adjustments = self._temporarily_reduce_duration(consumable, potion_id)
        previously_identified = getattr(self.item, "identified", False)
        original_name = self.item.name
        blocked_by_exception = potion_id in POTION_IDENTIFICATION_EXCEPTIONS
        allow_identification = not blocked_by_exception
        special_message = "The creature's pupils dilate." if potion_id == PRECISION_POTION_ID else None
        effect_applied = True
        previous_suppression = getattr(consumable, "_suppress_effect_messages", False)
        consumable._suppress_effect_messages = (
            potion_id == PRECISION_POTION_ID and target is not self.engine.player
        )
        consumable._effect_message_emitted = False

        try:
            if potion_id == "Poison potion":
                effect_applied = self._apply_poison_splash(target, consumable)
            else:
                action = ItemAction(target, self.item, (target.x, target.y))
                consumable.activate(action)
        except exceptions.Impossible:
            effect_applied = False
        finally:
            self._restore_duration(consumable, adjustments)
            consumable._suppress_effect_messages = previous_suppression

        potion_identified_now = bool(getattr(self.item, "identified", False))
        effect_described = getattr(consumable, "_effect_message_emitted", False)

        if potion_id == "Poison potion" and not effect_applied:
            allow_identification = False

        if not effect_applied:
            allow_identification = False

        if not allow_identification:
            self.item.name = original_name
            self.item.identified = previously_identified
            if special_message and potion_id == PRECISION_POTION_ID:
                self.engine.message_log.add_message(special_message, color.status_effect_applied)
            elif not previously_identified:
                self.engine.message_log.add_message(
                    "No parece que la sustancia le afecte a esa criatura.",
                    color.impossible,
                )
            return

        if special_message and potion_id == PRECISION_POTION_ID:
            self.engine.message_log.add_message(
                special_message,
                color.status_effect_applied,
            )

        if not previously_identified and potion_identified_now:
            if not effect_described:
                self._log_identification_description(potion_id, target)
            self.engine.message_log.add_message(
                "The potion has been identified.",
                color.status_effect_applied,
            )

    def _temporarily_reduce_duration(self, consumable, potion_id: str) -> dict:
        adjustments = {}
        if hasattr(consumable, "number_of_turns"):
            original = consumable.number_of_turns
            consumable.number_of_turns = max(1, original // 2)
            adjustments["number_of_turns"] = original
        if hasattr(consumable, "min_turns"):
            original_min = consumable.min_turns
            consumable.min_turns = max(1, original_min // 2)
            adjustments["min_turns"] = original_min
        if hasattr(consumable, "max_turns"):
            original_max = consumable.max_turns
            reduced_max = max(1, original_max // 2)
            if hasattr(consumable, "min_turns"):
                reduced_max = max(consumable.min_turns, reduced_max)
            consumable.max_turns = reduced_max
            adjustments["max_turns"] = original_max
        if potion_id == "Poison potion":
            if hasattr(consumable, "counter"):
                original_counter = consumable.counter
                consumable.counter = max(1, original_counter // 2)
                adjustments["counter"] = original_counter
            if hasattr(consumable, "amount"):
                original_amount = consumable.amount
                consumable.amount = max(1, original_amount // 2)
                adjustments["amount"] = original_amount
        return adjustments

    def _restore_duration(self, consumable, adjustments: dict) -> None:
        for attr, value in adjustments.items():
            setattr(consumable, attr, value)
        return

    def _apply_poison_splash(self, target: Actor, consumable) -> bool:
        amount = getattr(consumable, "amount", 1)
        target.fighter.poisons_on_hit = True

        if target.fighter.poison_resistance >= amount:
            if self.item.consumable:
                self.item.consumable.consume()
            return False

        action = ItemAction(target, self.item, (target.x, target.y))
        consumable.activate(action)
        target.fighter.poisons_on_hit = True
        return True

    def _log_identification_description(self, potion_id: str, target: Actor) -> None:
        template = POTION_IDENTIFICATION_DESCRIPTIONS.get(potion_id)
        if template:
            self.engine.message_log.add_message(
                template.format(target=target.name),
                color.status_effect_applied,
            )
        else:
            self.engine.message_log.add_message(
                f"{target.name} reacciona al efecto de la poción.",
                color.status_effect_applied,
            )

    def _spend_throw_cost(self) -> None:
        self.entity.fighter.stamina -= 1
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        if DEBUG_MODE:
            print(
                f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in ThrowItemAction"
            )
            print(
                f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left."
            )

    def _compute_throw_path(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        path: List[Tuple[int, int]] = []
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while not (x == x1 and y == y1):
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
            path.append((x, y))
        return path

    def _animate_throw(self, path: List[Tuple[int, int]]) -> None:
        if not path:
            return
        frames = []
        total = len(path)
        for index, (x, y) in enumerate(path):
            if not self.engine.game_map.in_bounds(x, y):
                continue
            char = "*" if index < total - 1 else "o"
            frames.append(([(x, y, char, color.orange)], 0.03))
        if frames:
            self.engine.queue_animation(frames)


class MeleeAction(ActionWithDirection):

    def is_dummy_object(self, obj):
        #from components.fighter import Door  # Importa la clase Door
        from components.ai import Dummy
        #from entity import Obstacle
        #return isinstance(obj, Door)  # Comprueba si obj es una instancia de Door
        return isinstance(obj, Dummy)

    def perform(self) -> None:

        target = self.target_actor

        # Comprobar si atacante y/o objetivo son visibles para el jugador
        # Útil para impresión de mensajes y más.
        if self.engine.game_map.visible[target.x, target.y] == False:
            target_invisible = True
            target_visible = False
        else:
            target_invisible = False
            target_visible = True
        if self.engine.game_map.visible[self.entity.x, self.entity.y] == False:
            attacker_invisible = True
            attacker_visible = False
        else:
            attacker_visible = True
            attacker_invisible = False

        if not target:
            raise exceptions.Impossible("Nothing to attack.")

        target_ai = getattr(target, "ai", None)
        if target_ai and hasattr(target_ai, "on_attacked"):
            target_ai.on_attacked(self.entity)
        
        if self.entity.fighter.stamina <= 0:
            if target_visible or attacker_visible:
                if self.entity is self.engine.player:
                    self.engine.message_log.add_message("You are exhausted!", color.red)
                else:
                    self.engine.message_log.add_message(f"{self.entity.name} is exhausted!")
            raise exceptions.Impossible("")
        
        # Calculo de impacto
        # El cálculo de imparto es una tirada de 1d6 + to_hit vs defensa del objetivo
        #hit_dice = random.randint(1, 6) + self.entity.fighter.to_hit
        # El cálculo de imparto es una tirada de 1d6 + (to_hit * weapon_proficiency) vs defensa del objetivo
        hit_dice = random.randint(1, 6) + (self.entity.fighter.to_hit * self.entity.fighter.weapon_proficiency)
        hit_dice = round(hit_dice)

        # Otra opción:
        # hit_dice = random.randint(1, 6) + self.entity.fighter.to_hit + self.entity.fighter.weapon_proficiency
        # hit_dice = round(hit_dice)

        # TODO: Hay que revisar todo esto para que funcione con el nuevo sistema
        # de cálculo de daños.
        # Mecánica backstab/stealth/sigilo (beta)
        # Bonificador al impacto
        if self.is_dummy_object(target.ai) == False:

            if target.fighter.aggravated == False:
                #import ipdb;ipdb.set_trace()
                #hit_dice = hit_dice + self.entity.fighter.luck + self.entity.fighter.base_stealth
                hit_dice = random.randint(1, 6) + self.entity.fighter.base_stealth + ((self.entity.fighter.to_hit + self.entity.fighter.luck) * self.entity.fighter.weapon_proficiency)
                hit_dice = round(hit_dice)
                if self.engine.debug == True:
                    print("DEBUG: (Bonificador al impacto) ATAQUE SIGILOSO!")

        # Si impacta
        if hit_dice > target.fighter.defense:

            if self.entity is self.engine.player:
                damage_color = color.health_recovered

                # Despertar durmiente en caso de ser golpeado (aun sin daño)
                #import ipdb;ipdb.set_trace()
                from components.ai import HostileEnemy, SleepingEnemy
                if isinstance(target, Actor) and isinstance(target.ai, SleepingEnemy):
                    target.ai = HostileEnemy(target)

            else:
                damage_color = color.red
            
            # TODO: Hay que rehacer todo esto para que funcione con el nuevo sistema
            # de cálculo de daños.
            # Mecánica ataque envenenado
            if self.entity.fighter.poisons_on_hit == True:

                from components.ai import Dummy
                #if isinstance(target.ai, Dummy) == False:
                if self.is_dummy_object(target.ai) == False:

                    poison_roll = random.randint(1, 6)

                    if poison_roll >= 1:

                        if self.entity is self.engine.player:
                            if target_visible or attacker_visible:
                                print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                                self.engine.message_log.add_message(
                                    f"{target.name} is POISONED! (The {self.entity.name} was poisonous)", damage_color
                                )
                        else:
                            if target_visible or attacker_visible:
                                print(f"Your are POISONED! (The {self.entity.name} was poisonous)")
                                self.engine.message_log.add_message(
                                    f"You are POISONED! (The {self.entity.name} was poisonous)", damage_color
                                )

                        target.fighter.is_poisoned = True
                        target.fighter.poisoned_counter += 5
                        target.fighter.poison_dmg = 1
                        self.entity.fighter.poisons_on_hit = False

            #damage = self.entity.fighter.power + random.randint(self.entity.fighter.weapon_proficiency[0], self.entity.fighter.weapon_proficiency[1]) - target.fighter.armor_value
            
            # MELEE DAMAGE CALCULATION
            strength = self.entity.fighter.strength
            weapon_dmg_dice_info = self.entity.fighter.weapon_dmg_dice_info
            weapon_dmg_bonus = self.entity.fighter.weapon_dmg_bonus
            no_weapon_dmg_bonus = self.entity.fighter.non_weapon_dmg_bonus
            total_equipment_dmg_bonus = self.entity.fighter.total_equipment_dmg_bonus
            proficiency = self.entity.fighter.weapon_proficiency
            weapon_dmg_dice_roll = self.entity.fighter.weapon_dmg_dice
            
            print(f"{bcolors.WARNING}Calculating MELEE damage with the following stats:{color.bcolors.ENDC}")
            if self.entity.fighter.main_hand_weapon is not None:
                print("Weapon: ", self.entity.fighter.main_hand_weapon.name)
            else:
                print("Weapon: None (unarmed attack)")
            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} strength: {strength}")
            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_dice_info: {weapon_dmg_dice_info}")
            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_dice_roll: {weapon_dmg_dice_roll}")
            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_bonus: {weapon_dmg_bonus}")
            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} no_weapon_dmg_bonus: {no_weapon_dmg_bonus}")
            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} total_equipment_dmg_bonus: {total_equipment_dmg_bonus}")
            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} proficiency: {proficiency}")
            print(f"{bcolors.WARNING}{target.name}{bcolors.ENDC} armor_value: {target.fighter.armor_value}")
      
            #total_equipment_dmg_bonus = getattr(self.entity.fighter, "total_equipment_dmg_bonus", 0)
            #import ipdb;ipdb.set_trace()
            damage = ((strength + weapon_dmg_dice_roll + total_equipment_dmg_bonus) * self.entity.fighter.weapon_proficiency) - target.fighter.armor_value
            damage = round(damage)
            print(f"{bcolors.WARNING}--> Final MELEE damage: {damage}{bcolors.ENDC}")

            # Mecánica backstab/stealth/sigilo (beta)
            # Bonificador al daño
            if isinstance(target, Actor):
                if self.is_dummy_object(target.ai) == False:
                    if target.fighter.aggravated == False:

                        #damage = (damage + self.entity.fighter.luck) * 2
                        damage = ((strength + weapon_dmg_dice_roll + total_equipment_dmg_bonus + self.entity.fighter.luck) * self.entity.fighter.weapon_proficiency) - target.fighter.armor_value
                        damage = round(damage)

                        if self.engine.debug == True:
                            print("DEBUG: DAÑO BACKSTAB EXTRA: ", damage)

                        if target_visible or attacker_visible:
                            self.engine.message_log.add_message("Successful stealth attack!", damage_color)
                            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC}: Successful stealth attack!")
                            print(f"Backstab damage applied: {damage}")

                        # Experiencia extra
                        if self.entity == self.engine.player:
                            if self.engine.debug == True:
                                print("DEBUG: EXPERIENCIA EXTRA (stealth attack): ", damage)
                            self.engine.player.level.add_xp(target.level.xp_given)

                        target.fighter.aggravated = True

            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"


            # Si hace daño...
            if damage > 0:
                
                # PENALIZACIÓN por SER DAÑADO
                

                # BONIFICACIÓN por dañar
                # Limitamos la bonificación:
                #if self.entity.fighter.to_hit_counter < 1:
                
                    # Opciones de bonificación:

                    ## A) Los impactos aumentan el poder (daño)...
                    ### A.1) ... el daño base 
                    #self.entity.fighter.strength += 1
                    ### A.2) ... o la tirada de daño
                    #self.entity.fighter.weapon_proficiency[1] += 1

                    ## B) Los impactos aumentan el To Hit:
                    #self.entity.fighter.base_to_hit += 1

                    # Contabilizamos el bonus:
                    #self.entity.fighter.to_hit_counter += 1

                    # DEBUG
                    #print(f"power_hits_counter: {power_hits_counter}")
                    #print(f"strength: {self.entity.fighter.strength}")


                # Efectos sonoros y otros efectos singulares
                # if target is self.engine.player:
                #     if self.entity.name == "Monkey":
                #         if self.entity.equipment.main_hand_weapon is not None:
                #             weapon_name = self.entity.equipment.main_hand_weapon.name
                #             self.engine.message_log.add_message(f"{self.entity.name} has a {weapon_name}!", color.orange)
                        # TODO: sound effects
                        #self.engine.sound_manager.play_sound("monkey_attack_player.wav")
                    # elif self.entity.name == "Goblin":
                    #     #self.engine.sound_manager.play_sound("goblin_attack_player.wav")
                    #     pass

                if target_visible or attacker_visible:
                    print(f"{attack_desc} and hits ({hit_dice} VS {target.fighter.defense}) for {damage} dmg points!")
                    self.engine.message_log.add_message(
                        f"{attack_desc} and hits for {damage} dmg points!", damage_color
                    )

                target.fighter.hp -= damage

            # Si no hace daño
            else:

                # Reseteamos la BONIFICACIÓN
                #if self.entity.fighter.to_hit_counter > 0:
                    # se resta el bonificador al daño...
                    #self.entity.fighter.strength -= self.entity.fighter.to_power_counter
                    # ...o a la tirada de daño
                    #self.entity.fighter.weapon_proficiency[1] -= self.entity.fighter.to_power_counter
                    # ...o al to hit
                    #self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter

                    # reseteamos el contador de bonificación
                    #self.entity.fighter.to_hit_counter = 0

                if target_visible or attacker_visible:
                    print(f"{attack_desc} but does no damage.")
                    self.engine.message_log.add_message(
                        f"{attack_desc} but does no damage.", damage_color
                    )
        
        # Si no impacta:
        else:

            # TODO: Configurar colores en caso de que el combate sea entre jugador y 
            # adventurers.
            if self.entity is self.engine.player or self.entity.name == "Adventurer":
                failure_color = color.red
            else:
                failure_color = color.health_recovered

            # Reseteamos la BONIFICACIÓN
            # Con el nuevo sistema  reseteamos la bonificación cada vez que se ataca,
            # independientemente de que se falle o no
            #if self.entity.fighter.to_hit_counter > 0:
                ## se resta el bonificador al daño...
                ## self.entity.fighter.strength -= self.entity.fighter.to_power_counter
                ## ...o a la tirada de daño
                ## self.entity.fighter.weapon_proficiency[1] -= self.entity.fighter.to_power_counter
                ## ...o al to hit
                ## self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                #self.entity.fighter.base_to_hit -= 1

                # reseteamos el contador de bonificación
                #self.entity.fighter.to_hit_counter = 0
                #self.entity.fighter.to_hit_counter -= 1


            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"

            if target_visible or attacker_visible:
                print(f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})")
                self.engine.message_log.add_message(
                    f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})", 
                    failure_color,
                )

        # Con cada ataque gastamos 1 de stamina
        self.entity.fighter.stamina -= 1


        # Y reseteamos la BONIFICACIÓN
        # Reseteamos to-hit bonus
        # Reseteamos to_defense bonus
        if self.entity.fighter.to_hit_counter > 0:
            self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
            self.entity.fighter.to_hit_counter = 0
        if self.entity.fighter.to_defense_counter > 0:
            self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
            self.entity.fighter.to_defense_counter = 0

        # Con cada ataque reducimos 1 el defense bonus acumulado
        # Sistema antiguo. Ahora reseteamos todo el bonus de defensa al atacar.
        # if self.entity.fighter.to_defense_counter > 1:
        #     self.entity.fighter.base_defense -= 1
        #     self.entity.fighter.to_defense_counter -= 1

        ## ...o reducimos a 0 el defense bonus acumulado
        ##if self.entity.fighter.to_defense_counter >= 1:
        ##    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
        ##    self.entity.fighter.to_defense_counter = 0


        # TIME SYSTEM
        # Con cada ataque gastamos el coste de puntos de tiempo por acción de cada luchador 
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} time points in MeleeAction")
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} time points left.")



class MovementAction(ActionWithDirection):

    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy
        game_map = self.engine.game_map
        door_opened = False
        player_moved = False

        if not game_map.in_bounds(dest_x, dest_y):
            raise exceptions.Impossible("That way is blocked.")
        if not game_map.tiles["walkable"][dest_x, dest_y]:
            if game_map.try_open_door(dest_x, dest_y):
                door_opened = True
            else:
                raise exceptions.Impossible("That way is blocked.")
        if not door_opened and game_map.get_blocking_entity_at_location(dest_x, dest_y):
            raise exceptions.Impossible("That way is blocked.")

        if door_opened:
            if self.entity is self.engine.player:
                self.engine.message_log.add_message("You open the door.", color.white)
                play_door_open_sound()
        else:
            # Si en MELEE
            if self.entity.fighter.is_in_melee:
                # BONIFICADOR a la defensa
                if self.entity.fighter.to_defense_counter < 3:
                    self.entity.fighter.base_defense += 1
                    self.entity.fighter.to_defense_counter += 1
                
                # PENALIZACIÓN a To Hit
                if self.entity.fighter.to_hit_counter >= 1:
                    self.entity.fighter.base_to_hit -= 1
                    self.entity.fighter.to_hit_counter -= 1

                self.entity.move(self.dx, self.dy)            
                player_moved = True
            
            # Si no en MELEE 
            else:
                # Reseteamos BONIFICACIÓN a la defensa
                if self.entity.fighter.to_defense_counter > 0:
                    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                    self.entity.fighter.to_defense_counter = 0

                self.entity.move(self.dx, self.dy)
                player_moved = True

        # Reseteamos toda BONIFICACIÓN

        # Reseteamos power bonus
        #if self.entity.fighter.to_power_counter >= 1:
        #    self.entity.fighter.strength -= self.entity.fighter.to_power_counter
        #    self.entity.fighter.to_power_counter = 0
        # Reseteamos to-hit bonus
        #if self.entity.fighter.to_hit_counter >= 1:
        #    self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
        #    self.entity.fighter.to_hit_counter = 0
        # Reseteamos defense bonus
        #if self.entity.fighter.to_defense_counter >= 1:
        #    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
        #    self.entity.fighter.to_defense_counter = 0

        # Recuperamos stamina al movernos
        if not door_opened and self.entity.fighter.stamina < self.entity.fighter.max_stamina:
            self.entity.fighter.stamina += 1
            #print(f"{self.entity.name}: stamina: {self.entity.fighter.stamina}")

        if player_moved and self.entity is self.engine.player:
            play_player_footstep()

        # TIME SYSTEM
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        if DEBUG_MODE:
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in MovementAction")
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")


class OpenDoorAction(ActionWithDirection):
    def __init__(self, entity: Actor, dx: int, dy: int, door: Actor):
        super().__init__(entity, dx, dy)
        self.door = door

    def perform(self) -> None:
        fighter = getattr(self.door, "fighter", None)
        if not fighter or not hasattr(fighter, "set_open"):
            raise exceptions.Impossible("You can't open that.")
        if fighter.is_open:
            raise exceptions.Impossible("The door is already open.")
        fighter.set_open(True)
        if self.entity is self.engine.player:
            self.engine.message_log.add_message("You open the door.", color.white)
            play_door_open_sound()
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost


class OpenChestAction(Action):
    def __init__(self, entity: Actor, chest):
        super().__init__(entity)
        self.chest = chest

    def perform(self) -> None:
        if not self.chest:
            raise exceptions.Impossible("There is nothing to open.")
        self.chest.open()
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost


class CloseDoorAction(Action):
    _NEIGHBOR_DELTAS = [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
    ]

    def perform(self) -> None:
        gamemap = self.engine.game_map
        px, py = self.entity.x, self.entity.y
        open_doors = [
            (px + dx, py + dy)
            for dx, dy in self._NEIGHBOR_DELTAS
            if gamemap.in_bounds(px + dx, py + dy)
            and gamemap.is_open_door(px + dx, py + dy)
        ]

        if not open_doors:
            raise exceptions.Impossible("There is no open door nearby.")

        target_x, target_y = open_doors[0]
        blocker = gamemap.get_blocking_entity_at_location(target_x, target_y)
        if blocker:
            raise exceptions.Impossible("Something blocks the doorway.")

        gamemap.close_door(target_x, target_y)
        if self.entity is self.engine.player:
            self.engine.message_log.add_message("You close the door.", color.descend)
            play_door_close_sound()
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost


class WaitAction(Action):
    def perform(self) -> None:
        """
        if self.entity.fighter.stamina < self.entity.fighter.max_stamina:
            self.entity.fighter.stamina += 1
        pass
        """

        # Accion de esperar resetea el tipo de BONIFICACIÓN por impactos, 
        # indiferentemente de si se está o no en melee:
        #if self.entity.fighter.to_hit_counter >= 1:
            #self.entity.fighter.strength -= self.entity.fighter.to_power_counter
            #self.entity.fighter.weapon_proficiency[1] -= self.entity.fighter.to_power_counter
        #    self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter

        #    self.entity.fighter.to_hit_counter = 0

        # Si no en melee
        if not self.entity.fighter.is_in_melee:

            # Recuperamos stamina
            if self.entity.fighter.stamina < self.entity.fighter.max_stamina:
                self.entity.fighter.stamina += 1
                #print(f"{self.entity.name}: stamina: {self.entity.fighter.stamina}")

            # Reseteamos to-hit bonus
            if self.entity.fighter.to_hit_counter > 0:
                self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                self.entity.fighter.to_hit_counter = 0

            # Reseteamos defense bonus
            if self.entity.fighter.to_defense_counter > 0:
                self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                self.entity.fighter.to_defense_counter = 0


            # FORTIFICAR: 
            # Punto de defensa GRATIS (e.e. sin gasto de estamina)
            # si el enemigo está a 1 de distancia
            #import render_functions
            #if self.engine.player.fighter.can_fortify == True:
            if self.engine.player.fighter.fortified == True:

                self.entity.fighter.base_defense += 1
                self.entity.fighter.to_defense_counter += 1
                self.entity.fighter.base_to_hit += 1
                self.entity.fighter.to_hit_counter += 1

                self.engine.player.fighter.fortified = False


            """
            for entity in set(self.engine.game_map.actors) - {self.engine.player}:
                if entity.is_alive:
                    #if self.engine.game_map.visible[entity.x, entity.y]:
                    distance = int(entity.distance(self.engine.player.x, self.engine.player.y))
                    if distance <= 1:
                        self.engine.player.fighter.fortified = True
                        print(f">>>>>>>>>>>>>>>>>>>>>> Fortify: {self.engine.player.fighter.fortified} <<<<<<<<<<<<<<<<<<<<<<<<<<<")
                        #break
            """
            


        # En melee:
        else: 

            # Si queda stamina:
            if self.entity.fighter.stamina > 0:

                #self.entity.fighter.defense_bonus += self.entity.fighter.base_defense + self.entity.fighter.armor_value - self.entity.fighter.aggressivity
                self.entity.fighter.stamina -= 1

                # BONIFICADOR a la defensa
                if self.entity.fighter.to_defense_counter < 3:
                    self.entity.fighter.base_defense += 1
                    self.entity.fighter.to_defense_counter += 1


                # BONIFICADOR a to hit  
                self.entity.fighter.base_to_hit += 1
                self.entity.fighter.to_hit_counter +=1
     
                #print(f"{self.entity.name}: stamina: {self.entity.fighter.stamina}")
                #print(f"{self.entity.name}: base_defense: {self.entity.fighter.base_defense}")
                #print(f"{self.entity.name}: base_to_hit {self.entity.fighter.base_to_hit}")
                #print(f"{to_hit_bonus_counter}")

            # Si no queda stamina
            else:

                # Reseteamos BONIFICACIÓN

                # Defense bonus:
                ## Pierde defensa al doble de rápido...
                #if self.entity.fighter.to_defense_counter == 1:
                #    self.entity.fighter.to_defense_counter -= 1
                #    self.entity.fighter.base_defense -= 1

                #if self.entity.fighter.to_defense_counter >= 2:
                #    self.entity.fighter.to_defense_counter -= 2
                #    self.entity.fighter.base_defense -= 2
                
                ## ...o pierde defensa de golpe
                if self.entity.fighter.to_defense_counter > 0:
                    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                    self.entity.fighter.to_defense_counter = 0
                
                # To hit bonus
                ## A) De golpe pierde todo el bonus
                if self.entity.fighter.to_hit_counter > 0:
                    self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                    self.entity.fighter.to_hit_counter = 0

                ## B) Lo pierde progresivamente
                #if self.entity.fighter.to_hit_counter > 0:
                #    self.entity.fighter.base_to_hit -= 1
                #    self.entity.fighter.to_hit_counter -= 1

                # Hemos perdido el turno, así que
                # recuperamos 1 de stamina
                self.entity.fighter.stamina += 1

        # TIME SYSTEM
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        if DEBUG_MODE:
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in WaitAction.")
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")
        #pass


class PassAction(Action):
    def perform(self) -> None:
        pass
    
    
class ToogleLightAction(Action):
    def perform(self):
        if DEBUG_MODE:
            print(f"DEBUG: PLAYER FOV: {self.engine.player.fighter.fov}")

        # if self.engine.player.fighter.lamp_on == False:
        #     self.engine.player.fighter.lamp_on == True
        #     self.engine.player.fighter.fov += 4
        #     self.engine.player.fighter.base_stealth += 1
        #     self.engine.message_log.add_message("You turn ON your lamp", color.descend)
        #     return 0
        # if self.engine.player.fighter.lamp_on == True:
        #     self.engine.player.fighter.lamp_on == False
        #     self.engine.player.fighter.fov -= 4
        #     self.engine.player.fighter.base_stealth -= 1
        #     self.engine.message_log.add_message("You turn OFF your lamp", color.enemy_die)
        #     return 0
        
        if self.engine.player.fighter.fov == 6:
            self.engine.player.fighter.base_stealth += 1
            self.engine.player.fighter.fov = 1
            #print(f"PLAYER FOV: {self.engine.player.fighter.fov}")
            self.engine.message_log.add_message("You turn OFF your lamp", color.descend)
            return 0
        if self.engine.player.fighter.fov == 1:
            self.engine.player.fighter.fov = 6
            self.engine.player.fighter.base_stealth -= 1
            #print(f"PLAYER FOV: {self.engine.player.fighter.fov}")
            self.engine.message_log.add_message("You turn ON your lamp", color.enemy_die)
            return 0
    

#class DefendAction(Action):
#    def perform(self):
#        pass


class BumpAction(ActionWithDirection):

    def perform(self) -> None:
        target = self.target_actor
        if target:
            self_name = getattr(self.entity, "name", "").lower()
            target_name = getattr(target, "name", "").lower()
            if self_name == "adventurer" and target_name == "adventurer":
                return WaitAction(self.entity).perform()
            if getattr(target, "name", "").lower() == "door":
                fighter = getattr(target, "fighter", None)
                if fighter and hasattr(fighter, "set_open"):
                    if getattr(fighter, "is_open", False):
                        target = None
                    else:
                        return OpenDoorAction(self.entity, self.dx, self.dy, target).perform()
            if target:
                return MeleeAction(self.entity, self.dx, self.dy).perform()
        return MovementAction(self.entity, self.dx, self.dy).perform()
