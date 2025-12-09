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
from audio import (
    play_player_footstep,
    play_door_close_sound,
    play_item_pickup_sound,
    play_stair_descend_sound,
    play_melee_attack_sound,
    play_player_stamina_depleted_sound,
)

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

    def __init__(self, entity: Actor, item: Optional[Item] = None):
        super().__init__(entity)
        self.item = item

    def perform(self) -> None:
        actor_location_x = self.entity.x
        actor_location_y = self.entity.y
        inventory = self.entity.inventory

        items_here = [
            item
            for item in self.engine.game_map.items
            if actor_location_x == item.x and actor_location_y == item.y
        ]

        if not items_here:
            raise exceptions.Impossible("There is nothing here to pick up.")

        item_to_pick = self.item if self.item else items_here[0]
        if item_to_pick not in items_here:
            raise exceptions.Impossible("That item is not here.")

        if len(inventory.items) >= inventory.capacity:
            raise exceptions.Impossible("Your inventory is full.")

        self.engine.game_map.entities.remove(item_to_pick)
        item_to_pick.parent = self.entity.inventory
        inventory.items.append(item_to_pick)

        self.engine.message_log.add_message(f"You picked up the {item_to_pick.name}!")
        play_item_pickup_sound(item_to_pick)

        # TIME SYSTEM
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        if DEBUG_MODE:
            print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in PickupAction")
            print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")


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
                    

class IdentifyItemAction(Action):
    """Identify an item from the actor inventory using a scroll."""

    def __init__(self, entity: Actor, scroll: Item, target_item: Item):
        super().__init__(entity)
        self.item = scroll
        self.target_item = target_item

    def perform(self) -> None:
        if not self.item.consumable:
            raise exceptions.Impossible("This scroll has no effect.")
        if self.target_item not in self.entity.inventory.items:
            raise exceptions.Impossible("You must pick an item from your inventory.")
        if getattr(self.target_item, "identified", False):
            raise exceptions.Impossible("That item is already identified.")
        self.item.consumable.activate(self)


class RemoveCurseItemAction(Action):
    """Remove a curse from an item in the actor inventory using a scroll."""

    def __init__(self, entity: Actor, scroll: Item, target_item: Item):
        super().__init__(entity)
        self.item = scroll
        self.target_item = target_item

    def perform(self) -> None:
        if not self.item.consumable:
            raise exceptions.Impossible("This scroll has no effect.")
        if self.target_item not in self.entity.inventory.items:
            raise exceptions.Impossible("You must pick an item from your inventory.")
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

            starting_floor = self.engine.game_world.current_floor

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

            if self.engine.game_world.current_floor >= len(self.engine.game_world.levels):
                raise exceptions.Impossible("You can't descend any further.")

            if not self.engine.perform_floor_transition(self.engine.game_world.advance_floor):
                raise exceptions.Impossible("You can't descend any further.")

            self.engine.message_log.add_message(
                "You descend the staircase.", color.descend
                )
            if (
                self.entity is self.engine.player
                and starting_floor == 1
                and self.engine.game_world.current_floor == 2
                and not getattr(self.engine, "lamp_hint_shown", False)
            ):
                self.engine.lamp_hint_shown = True
                self.engine.message_log.add_message(
                    "Press 'q' to turn on your lamp.",
                    color.orange,
                )
            if self.entity is self.engine.player:
                play_stair_descend_sound()
            print(f"{color.bcolors.OKCYAN}{self.entity.name} descends the staircase.{color.bcolors.ENDC}")

        elif at_upstairs:

            self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
            if DEBUG_MODE:
                print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in TakeStairsAction (ascend)")
                print(f"DEBUG: {bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

            if self.engine.game_world.current_floor <= 1:
                raise exceptions.Impossible("You can't ascend any further.")

            if not self.engine.perform_floor_transition(self.engine.game_world.retreat_floor):
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

        # Stamina check
        if self.entity.fighter.stamina <= 0:
            if self.entity is self.engine.player:
                self.engine.message_log.add_message("You are exhausted!", color.red)
                play_player_stamina_depleted_sound()
            else:
                self.engine.message_log.add_message(f"{self.entity.name} is exhausted!", color.red)
            raise exceptions.Impossible("")

        if self._is_potion(self.item):
            self._handle_potion_throw(target, dest_x, dest_y)
            self._spend_throw_cost()
            return

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

        # Comprobar si atacante y/o objetivo son visibles para el jugador
        # Útil para impresión de mensajes y más.
        target_visible = bool(self.engine.game_map.visible[target.x, target.y])
        attacker_visible = bool(self.engine.game_map.visible[self.entity.x, self.entity.y])

        target_ai = getattr(target, "ai", None)
        target_is_dummy = self.is_dummy_object(target_ai)


        # CÁLCULO DE IMPACTOS
        hits = False
        stealth_attack = False
        attacking_from_hide = getattr(self.entity.fighter, "is_hidden", False)

        # Contra objetivos vivientes
        if not target_is_dummy:
            
            # Ataque sorpresa backstab/stealth/sigilo con bonificador al impacto (beta)
            stealth_allowed = attacking_from_hide or target.fighter.aggravated == False
            if stealth_allowed:
    
                hit_dice = random.randint(1, 6) + (self.entity.fighter.to_hit * self.entity.fighter.weapon_proficiency)
                hit_dice = round(hit_dice) + self.entity.fighter.luck
                
                if hit_dice > target.fighter.defense - self.entity.fighter.stealth:
                    hits = True
                else:
                    hits = False

                if hits:
                    stealth_attack = True
                    if attacker_visible or target_visible:
                        print(f"{self.entity.name} has SUCCESSFULLY executed a stealth attack (VS {target.name})")
                        self.engine.message_log.add_message(
                            f"{self.entity.name} has SUCCESSFULLY executed a stealth attack (VS {target.name})", 
                            color.orange
                            )
                else:
                    stealth_attack = False
                    if attacker_visible or target_visible:
                        print(f"{self.entity.name} FAILED the stealth attack (VS {target.name})!")
                        self.engine.message_log.add_message(
                            f"{self.entity.name} FAILED the stealth attack (VS {target.name})", 
                            color.red
                            )

            # Ataque ordinario (no stealth)
            else:

                hit_dice = random.randint(1, 6) + (self.entity.fighter.to_hit * self.entity.fighter.weapon_proficiency)
                hit_dice = round(hit_dice)
                
                if hit_dice > target.fighter.defense:
                    hits = True

            # Si impacta
            if hits == True:

                # Despertar durmiente en caso de ser golpeado (aun sin daño)
                from components.ai import HostileEnemy, SleepingEnemy
                if isinstance(target, Actor) and isinstance(target.ai, SleepingEnemy):
                    target.ai = HostileEnemy(target)

                # Relativizar colores para mensajes
                if self.entity is self.engine.player:
                    damage_color = color.health_recovered
                else:
                    damage_color = color.red
                
                # Mecánica ataque envenenado
                #Lanzamiento de armas envenenadas:
                if self.entity.fighter.poisons_on_hit == True and self.is_dummy_object(target.ai) == False:

                    poison_roll = random.randint(1, 6)

                    if poison_roll > target.fighter.luck:

                        if self.entity is self.engine.player:
                            if attacker_visible or target_visible:
                                print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                                self.engine.message_log.add_message(
                                    "{target.name} is POISONED! (The {self.entity.name} was poisonous)", 
                                    damage_color
                                    )
                            
                        elif target is self.engine.player:
                            print(f"You are POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                f"You are POISONED! (The {self.entity.name} was poisonous)", 
                                damage_color
                                )

                        else:
                            if attacker_visible or target_visible:
                                print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                                self.engine.message_log.add_message(
                                    f"{target.name} is POISONED! (The {self.entity.name} was poisonous)", 
                                    color.white,
                                    )

                        target.fighter.is_poisoned = True
                        target.fighter.poisoned_counter += self.entity.fighter.poisonous
                        if target.fighter.poisoned_counter < 0:
                            target.fighter.is_poisoned = False
                            target.fighter.poisoned_counter = 0
                        target.fighter.poison_dmg = 1
                        self.entity.fighter.poisons_on_hit = False

                # THROWING DAMAGE CALCULATION
                # Si es un arma...
                if self.item.equippable.equipment_type.name == "WEAPON":

                    strength = self.entity.fighter.strength
                    weapon_dmg_dice_info = self.item.equippable.weapon_dmg_dice_info
                    weapon_dmg_bonus = self.item.equippable.weapon_dmg_bonus
                    non_weapon_dmg_bonus = self.entity.fighter.non_weapon_dmg_bonus
                    total_equipment_dmg_bonus = self.entity.fighter.total_equipment_dmg_bonus
                    proficiency = self.entity.fighter.weapon_proficiency
                    weapon_dmg_dice_roll = self.item.equippable.weapon_dmg_dice
                    
                    if attacker_visible or target_visible:
                        print(f"{bcolors.WARNING}Calculating THROWING damage with the following stats:{bcolors.ENDC}")
                        print("Throwing weapon: ", self.item.name)
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} strength: {strength}")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_dice_info: {weapon_dmg_dice_info}")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_dice_roll: {weapon_dmg_dice_roll}")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} weapon_dmg_bonus: {weapon_dmg_bonus}")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} non_weapon_dmg_bonus: {non_weapon_dmg_bonus}")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} (total_equipment_dmg_bonus: {total_equipment_dmg_bonus})")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} proficiency: {proficiency}")
                        if target.fighter:
                            print(f"{bcolors.WARNING}{target.name}{bcolors.ENDC} armor_value: {target.fighter.armor_value}")
                    
                    # El arma lanzada ya no se encuentra equipada, por eso hay que sumar su bonus aparte
                    damage = ((strength + weapon_dmg_dice_roll + weapon_dmg_bonus + total_equipment_dmg_bonus) * self.entity.fighter.weapon_proficiency) - target.fighter.armor_value
                    damage = round(damage)

                    # Bonificador STEALTH ATTACK al daño
                    if stealth_attack:

                        second_weapon_dmg_dice_roll = self.item.equippable.weapon_dmg_dice
                        damage = damage + strength + second_weapon_dmg_dice_roll

                        if target_visible or attacker_visible:
                            self.engine.message_log.add_message("Successful stealth attack!", damage_color)
                            print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC}: Successful stealth attack! ({damage} dmg points)")
                            print(f"Backstab final damage: {damage}")

                        if DEBUG_MODE:
                            print("DEBUG: DAÑO BACKSTAB EXTRA: ", damage)
                        
                        # Especial para dagas
                        if self.item.name == "Dagger":
                            damage = damage * 1.5
                            damage = round(damage)
                            if DEBUG_MODE:
                                print(f"DEBUG: DAGGER BACKSTAB! (final damage: {damage})")
                        
                        if DEBUG_MODE == True:
                            if self.entity == self.engine.player:
                                print("DEBUG: EXPERIENCIA EXTRA (stealth attack): ", damage)

                        self.engine.player.level.add_xp(target.level.xp_given)

                    if attacker_visible or target_visible:
                        print(f"{bcolors.WARNING}--> Final THROWING damage: {damage}{bcolors.ENDC}")

                else:
                    # Si no es un arma, hacer daño básico
                    if attacker_visible or target_visible:
                        print(f"{bcolors.WARNING}Calculating THROWING damage (NON-WEAPON) with the following stats:{bcolors.ENDC}")
                        print("Throwing weapon: ", self.item.name)
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} strength: {self.entity.fighter.strength}")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} non_weapon_dmg_bonus: {self.entity.fighter.non_weapon_dmg_bonus}")
                        print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC} proficiency: {self.entity.fighter.weapon_proficiency}")
                    damage = (self.entity.fighter.strength + self.entity.fighter.non_weapon_dmg_bonus) * self.entity.fighter.weapon_proficiency - target.fighter.armor_value
                    damage = round(damage)
                    if attacker_visible or target_visible:
                        print(f"{bcolors.WARNING}--> Final THROWING damage (non-weapon): {damage}{bcolors.ENDC}")

  
                attack_desc = f"{self.entity.name.capitalize()} attacks {target.name} ({hit_dice} VS {target.fighter.defense})"

                # Si impacta y hace daño...
                if damage > 0:

                    if attacker_visible or target_visible:
                        print(f"{attack_desc} for {damage} dmg points.")
                        self.engine.message_log.add_message(f"{attack_desc} for {damage} dmg points.", damage_color)
                    # else:
                    #     print(f"You hear sounds of fighting.")
                    #     self.engine.message_log.add_message(f"You hear sounds of fighting.")

                    target.fighter.take_damage(
                        damage,
                        attacker=self.entity,
                        attack_item=self.item,
                    )

                # Si impacta pero no hace daño
                else:

                    if attacker_visible or target_visible:
                        print(f"{attack_desc} but does no damage.")
                        self.engine.message_log.add_message("{attack_desc} but does no damage.", damage_color)
                    # else:
                    #     print(f"You hear sounds of fighting.")
                    #     self.engine.message_log.add_message(f"You hear sounds of fighting.")
            
            # Si no impacta:
            else:

                # Relativizar colores de mensajes
                if self.entity is self.engine.player or self.entity.name == "Adventurer":
                    failure_color = color.red
                else:
                    failure_color = color.health_recovered

                if target_visible or attacker_visible:
                    attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
                    print(f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})")
                    self.engine.message_log.add_message(
                        f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})",
                        failure_color,
                    )
                if target is self.engine.player:
                    target.fighter.register_enemy_miss()

            # Tanto si impacta como si no impacta...

            # Reseteamos la BONIFICACIÓN si la hubiera
            if self.entity.fighter.to_hit_counter > 0:
                self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                self.entity.fighter.to_hit_counter = 0
            if self.entity.fighter.to_defense_counter > 0:
                self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                self.entity.fighter.to_defense_counter = 0

            # Enemigo dado por enterado
            target.fighter.aggravated = True
            self.engine.message_log.add_message(f"{target.name} is aggravated!", color.red)

        # TODO: Contra objetivos no vivientes
        else:
            pass

        self._spend_throw_cost()


    def _is_potion(self, item: Item) -> bool:
        return getattr(item, "char", None) == "!" and item.consumable is not None

    def _handle_potion_throw(self, target: Optional[Actor], dest_x: int, dest_y: int) -> None:
        if self._slime_absorb_potion(target):
            return

        self.engine.message_log.add_message(
            f"You throw the {self.item.name}. The vial shatters on impact!",
            color.orange,
        )
        if target and self.is_dummy_object(target.ai) == False:
            self._apply_potion_effect(target)
        else:
            self.item.consumable.consume()

    def _slime_absorb_potion(self, target: Optional[Actor]) -> bool:
        if not target:
            return False
        fighter = getattr(target, "fighter", None)
        if not fighter or not getattr(fighter, "is_slime", False):
            return False
        inventory = getattr(target, "inventory", None)
        if not inventory or len(inventory.items) >= inventory.capacity:
            return False

        previous_container = getattr(self.item, "parent", None)
        if hasattr(previous_container, "items") and self.item in previous_container.items:
            previous_container.items.remove(self.item)
        else:
            try:
                gamemap = self.item.gamemap
            except Exception:
                gamemap = None
            if gamemap:
                gamemap.entities.discard(self.item)

        self.item.parent = inventory
        inventory.items.append(self.item)

        message = None
        message_color = color.orange
        if self.entity is self.engine.player:
            message = f"Your {self.item.name} is absorbed by the slime!"
        elif self.engine.game_map.visible[target.x, target.y]:
            message = f"The {target.name} absorbs the {self.item.name}!"
            message_color = color.status_effect_applied
        if message:
            self.engine.message_log.add_message(message, message_color)

        return True

    def _apply_potion_effect(self, target: Actor) -> None:
        consumable = self.item.consumable
        if not consumable:
            return

        potion_id = getattr(self.item, "id_name", self.item.name)
        blocked_by_exception = potion_id in POTION_IDENTIFICATION_EXCEPTIONS
        previously_identified = getattr(self.item, "identified", False)
        original_name = self.item.name

        if blocked_by_exception:
            consumable.consume()
            self.engine.message_log.add_message(
                "No parece que la sustancia le afecte a esa criatura.",
                color.impossible,
            )
            return

        adjustments = self._temporarily_reduce_duration(consumable, potion_id)
        allow_identification = True
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
        amount = getattr(consumable, "amount", 1) * 0.5
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
        does_damage = False
        does_a_hit = False
        stealth_attack = False
        attacking_from_hide = getattr(getattr(self.entity, "fighter", None), "is_hidden", False)

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
        target_is_dummy = self.is_dummy_object(target_ai)
        target_fighter = getattr(target, "fighter", None)
        if target_fighter and getattr(target_fighter, "is_hidden", False):
            target_fighter.break_hide(reason="collision", revealer=self.entity)
            if self.entity is self.engine.player:
                self.engine.message_log.add_message(
                    f"You reveal {target.name} as you attack!",
                    color.descend,
                )
            elif target is self.engine.player:
                # Player notified inside break_hide.
                pass
            elif self.engine.game_map.visible[target.x, target.y]:
                self.engine.message_log.add_message(
                    f"{self.entity.name} reveals {target.name} before they can strike.",
                    color.descend,
                )
            self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
            if self.entity is not self.engine.player:
                self.entity.fighter.handle_post_action(False, self.__class__.__name__)
            return
        was_aggravated = getattr(target_fighter, "aggravated", False)
        if target_ai and hasattr(target_ai, "on_attacked"):
            target_ai.on_attacked(self.entity)
        
        # Attacking is noisy: mark a short-lived noise burst so others can hear it.
        attack_noise_tag = "combat_miss"

        # Stamina check
        if self.entity.fighter.stamina <= 0:
            if target_visible or attacker_visible:
                if self.entity is self.engine.player:
                    self.engine.message_log.add_message("You are exhausted!", color.red)
                    play_player_stamina_depleted_sound()
                else:
                    if self.engine.game_map.visible[self.entity.x, self.entity.y] == False:
                        self.engine.message_log.add_message(f"{self.entity.name} is exhausted!")
            raise exceptions.Impossible("")
        
        # Con cada ataque gastamos 1 de stamina
        self.entity.fighter.stamina -= 1

        hit_dice = random.randint(1, 6) + (self.entity.fighter.to_hit * self.entity.fighter.weapon_proficiency)
        hit_dice = round(hit_dice)

        # Otra opción:
        # hit_dice = random.randint(1, 6) + self.entity.fighter.to_hit + self.entity.fighter.weapon_proficiency
        # hit_dice = round(hit_dice)

        # TODO: Hay que revisar todo esto para que funcione como en ThrowItemAction
        # MECÁNICA BACKSTAB/STEALTH/SIGILO (beta)
        
        # Bonificador al impacto
        stealth_allowed = attacking_from_hide or was_aggravated == False
        if target_is_dummy == False:

            if stealth_allowed:
                #import ipdb;ipdb.set_trace()
                #hit_dice = hit_dice + self.entity.fighter.luck + self.entity.fighter.base_stealth
                hit_dice = random.randint(1, 6) + self.entity.fighter.stealth + self.entity.fighter.to_hit + self.entity.fighter.luck
                hit_dice = round(hit_dice)
                stealth_attack = True

        # Si impacta
        if hit_dice > target.fighter.defense:

            does_a_hit = True

            # Relativizar colores
            if self.entity is self.engine.player:
                damage_color = color.health_recovered

                # Despertar durmiente en caso de ser golpeado (aun sin daño)
                from components.ai import HostileEnemy, SleepingEnemy
                if isinstance(target, Actor) and isinstance(target.ai, SleepingEnemy):
                    target.ai = HostileEnemy(target)

            else:
                damage_color = color.red

            if stealth_attack:
                
                if target_visible or attacker_visible:
                    self.engine.message_log.add_message(
                            f"{self.entity.name} BACKSTABS {target.name}!", 
                            damage_color
                            )
                if self.engine.debug == True:
                    print("DEBUG: (Bonificador al impacto) ATAQUE SIGILOSO!")

            # TODO: Hay que rehacer todo esto para que funcione con el nuevo sistema
            # de cálculo de daños.
            # Mecánica ataque envenenado
            if self.entity.fighter.poisons_on_hit == True:

                from components.ai import Dummy
                if not target_is_dummy:

                    poison_roll = random.randint(1, 6)

                    if poison_roll > target.fighter.luck:

                        if self.entity is self.engine.player:
                            if attacker_visible or target_visible:
                                print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                                self.engine.message_log.add_message(
                                    f"{target.name} is POISONED! (The {self.entity.name} was poisonous)", 
                                    damage_color
                                    )
                            
                        elif target is self.engine.player:
                            print(f"You are POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                f"You are POISONED! (The {self.entity.name} was poisonous)", 
                                damage_color
                                )

                        else:
                            if attacker_visible or target_visible:
                                print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                                self.engine.message_log.add_message(
                                    f"{target.name} is POISONED! (The {self.entity.name} was poisonous)", 
                                    color.white,
                                    )

                        target.fighter.is_poisoned = True
                        target.fighter.poisoned_counter += self.entity.fighter.poisonous
                        if target.fighter.poisoned_counter < 0:
                            target.fighter.is_poisoned = False
                            target.fighter.poisoned_counter = 0
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
            main_weapon = self.entity.fighter.main_hand_weapon
            weapon_name = (
                main_weapon.name
                if main_weapon
                else self.entity.fighter.natural_weapon_name
                if self.entity.fighter.natural_weapon_name
                else "None (unarmed attack)"
            )
            print("Weapon: ", weapon_name)
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
            if stealth_attack and stealth_allowed:

                if isinstance(target, Actor):
                    if not target_is_dummy:
                        if was_aggravated == False or attacking_from_hide:

                            # Cálculo de daño Backstab
                            second_weapon_dmg_dice_roll = self.entity.fighter.weapon_dmg_dice
                            damage = damage + strength + second_weapon_dmg_dice_roll
                            damage = round(damage)

                            if DEBUG_MODE:
                                print("DEBUG: DAÑO BACKSTAB: ", damage)

                            # Especial para dagas
                            if main_weapon and main_weapon.name == "Dagger":
                                damage = damage * 1.5
                                damage = round(damage)
                                if DEBUG_MODE:
                                    print(f"DEBUG: DAGGER BACKSTAB! (final damage: {damage})")

                            if target_visible or attacker_visible:
                                self.engine.message_log.add_message("Successful STEALTH attack!", damage_color)
                                print(f"{bcolors.WARNING}{self.entity.name}{bcolors.ENDC}: Successful STEALTH attack! ({damage} dmg points)")
                                print(f"Backstab final damage: {damage}")

                            # Experiencia extra
                            if self.entity == self.engine.player:
                                if self.engine.debug == True:
                                    print("DEBUG: EXPERIENCIA EXTRA (stealth attack): ", damage)
                                self.engine.player.level.add_xp(target.level.xp_given)

                            target.fighter.aggravated = True

            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"

            # BONIFICADOR: atacar e impactar
            # Reducimos en 1 el DefenseValue
            if self.entity.fighter.to_defense_counter > 0:
                self.entity.fighter.base_defense -= 1
                self.entity.fighter.to_defense_counter -= 1

            # Si hace daño...
            if damage > 0:
                
                does_damage = True
                attack_noise_tag = "combat_hit"

                # PENALIZACIÓN por SER DAÑADO
                if not target_is_dummy:
                    if target.fighter.to_hit_counter > 0:
                        target.fighter.base_to_hit -= target.fighter.to_hit_counter
                        target.fighter.to_hit_counter = 0
                    if target.fighter.to_defense_counter > 0:
                        target.fighter.base_defense -= target.fighter.to_defense_counter
                        target.fighter.to_defense_counter = 0

                # BONIFICADOR POR DAÑAR
                if self.entity.fighter.to_hit_counter < 3:
                    self.entity.fighter.base_to_hit += 1
                    self.entity.fighter.to_hit_counter += 1


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
                    print(f"{attack_desc} and HITS ({hit_dice} VS {target.fighter.defense}) for {damage} dmg points!")
                    self.engine.message_log.add_message(
                        f"{attack_desc} and HITS ({hit_dice} VS {target.fighter.defense}) for {damage} dmg points!", damage_color
                    )
                play_melee_attack_sound(self.entity, "hit_damage", target_is_dummy=target_is_dummy)

                target.fighter.take_damage(
                    damage,
                    attacker=self.entity,
                    attack_item=main_weapon,
                )

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
                    if target is self.engine.player:
                        failure_color = color.health_recovered
                    else:
                        failure_color = color.red
                    print(f"{attack_desc} but does no damage.")
                    self.engine.message_log.add_message(
                        f"{attack_desc} but does no damage.", failure_color
                    )
                play_melee_attack_sound(self.entity, "hit_no_damage", target_is_dummy=target_is_dummy)
        
        # Si no impacta:
        else:

            stealth_attack = False

            # Relativizar colores
            if self.entity is self.engine.player or self.entity.name == "Adventurer":
                failure_color = color.red
            else:
                failure_color = color.health_recovered
            
            # En caso de que combate sea entre jugador y adventurer
            if self.entity is self.engine.player and target.name == "Adventurer":
                failure_color = color.red
            elif self.entity.name == "Adventurer" and target is self.engine.player:
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
            if target is self.engine.player:
                target.fighter.register_enemy_miss()
            play_melee_attack_sound(self.entity, "miss", target_is_dummy=target_is_dummy)


        # Ajustes de BONIFICACIONES FINALES

        # Reducimos en 1 el To-Hit
        # if self.entity.fighter.to_hit_counter > 0:
        #     self.entity.fighter.base_to_hit -= 1
        #     self.entity.fighter.to_hit_counter -= 1

        # Si no hizo daño, Reseteamos el To-Hit:
        if does_damage == False:
            if self.entity.fighter.to_hit_counter > 0:
                self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                self.entity.fighter.to_hit_counter = 0
                
        # Reducimos en 1 el DefenseValue
        # if self.entity.fighter.to_defense_counter > 0:
        #     self.entity.fighter.base_defense -= 1
        #     self.entity.fighter.to_defense_counter -= 1

        # Si no impactó, Reseteamos to_defense bonus
        if does_a_hit == False:
            if self.entity.fighter.to_defense_counter > 0:
                self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                self.entity.fighter.to_defense_counter = 0

        # Con cada ataque reducimos 1 el defense bonus acumulado
        # Sistema antiguo. Ahora reseteamos todo el bonus de defensa al atacar.
        # if self.entity.fighter.to_defense_counter > 1:
        #     self.entity.fighter.base_defense -= 1
        #     self.entity.fighter.to_defense_counter -= 1

        if self.entity is not self.engine.player:
            self.entity.fighter.handle_post_action(False, self.__class__.__name__)

        ## ...o reducimos a 0 el defense bonus acumulado
        ##if self.entity.fighter.to_defense_counter >= 1:
        ##    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
        ##    self.entity.fighter.to_defense_counter = 0
        
        # Calculo de impacto
        # El cálculo de imparto es una tirada de 1d6 + to_hit vs defensa del objetivo
        #hit_dice = random.randint(1, 6) + self.entity.fighter.to_hit
        # El cálculo de imparto es una tirada de 1d6 + (to_hit * weapon_proficiency) vs defensa del objetivo

        # Register final attack noise (hit or miss).
        if getattr(self.engine, "register_noise", None):
            self.engine.register_noise(self.entity, level=2, duration=2, tag=attack_noise_tag)

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
        move_dx, move_dy = self.dx, self.dy
        can_pass_closed_doors = getattr(self.entity.fighter, "can_pass_closed_doors", False)
        can_open_doors = getattr(self.entity.fighter, "can_open_doors", False)
        is_closed_door = game_map.is_closed_door(dest_x, dest_y)

        def _finalize_non_player_action() -> None:
            fighter = getattr(self.entity, "fighter", None)
            if fighter and self.entity is not self.engine.player:
                fighter.handle_post_action(False, self.__class__.__name__)

        if not game_map.in_bounds(dest_x, dest_y):
            if self.engine.game_world.current_floor == 1:
                if (
                    self.entity is self.engine.player
                    and any(getattr(item, "id_name", "") == "The Artifact" for item in self.entity.inventory.items)
                ):
                    self.engine.message_log.add_message("You escape with The Artifact!", color.ascend)
                    self.engine.player.ai = None
                    return
                raise exceptions.Impossible("Debo recuperar el artefacto.")
            else:
                raise exceptions.Impossible("That way is blocked.")
        blocked_tile = not game_map.tiles["walkable"][dest_x, dest_y]

        # Intentar abrir puerta incluso si el tile es walkable.
        if is_closed_door and not can_pass_closed_doors:
            if can_open_doors and game_map.try_open_door(dest_x, dest_y, actor=self.entity):
                door_opened = True
            else:
                raise exceptions.Impossible("That way is blocked.")
        elif blocked_tile and not (is_closed_door and can_pass_closed_doors):
            # Otros tiles no walkable (o puertas si no se puede pasar ni abrir).
                raise exceptions.Impossible("That way is blocked.")

        # Comprobar entidad bloqueante.
        blocking_entity = game_map.get_blocking_entity_at_location(dest_x, dest_y)
        if blocking_entity:
            hidden_fighter = getattr(blocking_entity, "fighter", None)
            if hidden_fighter and getattr(hidden_fighter, "is_hidden", False):
                hidden_fighter.break_hide(reason="collision", revealer=self.entity)
                if self.entity is self.engine.player:
                    self.engine.message_log.add_message(
                        f"You bump into {blocking_entity.name} and reveal them!",
                        color.descend,
                    )
                elif blocking_entity is self.engine.player:
                    # Player gets notified via break_hide; no extra message needed.
                    pass
                elif self.engine.game_map.visible[blocking_entity.x, blocking_entity.y]:
                    self.engine.message_log.add_message(
                        f"{self.entity.name} bumps into {blocking_entity.name}, revealing them.",
                        color.descend,
                    )
                self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
                _finalize_non_player_action()
                return
            if is_closed_door and can_pass_closed_doors:
                pass
            elif door_opened:
                blocking_entity = game_map.get_blocking_entity_at_location(dest_x, dest_y)
                if blocking_entity:
                    raise exceptions.Impossible("That way is blocked.")
            else:
                raise exceptions.Impossible("That way is blocked.")

        if door_opened:
            if self.entity is self.engine.player:
                self.engine.message_log.add_message("You open the door.", color.white)
            # Opening a door creates noise that can be heard for a couple of turns.
            if getattr(self.engine, "register_noise", None):
                self.engine.register_noise(self.entity, level=2, duration=2, tag="door")
        else:
            # Si en MELEE
            if self.entity.fighter.is_in_melee:
                # BONIFICADOR a la defensa
                if self.entity.fighter.to_defense_counter < 3:
                    self.entity.fighter.base_defense += 1
                    self.entity.fighter.to_defense_counter += 1

                # BONIFICACIÓN a To Hit
                # To-Hit +1
                # if self.entity.fighter.to_hit_counter < 3:
                #     self.entity.fighter.base_to_hit += 1
                #     self.entity.fighter.to_hit_counter += 1
                
                # PENALIZACIÓN a To Hit
                # To-Hit -1
                # if self.entity.fighter.to_hit_counter >= 1:
                #     self.entity.fighter.base_to_hit -= 1
                #     self.entity.fighter.to_hit_counter -= 1

                # To-hit reset
                if self.entity.fighter.to_hit_counter > 0:
                    self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                    self.entity.fighter.to_hit_counter = 0

                self.entity.move(move_dx, move_dy)            
                player_moved = True
            
            # Si no en MELEE 
            else:
                # Reseteamos BONIFICACIÓN a la defensa
                if self.entity.fighter.to_defense_counter > 0:
                    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                    self.entity.fighter.to_defense_counter = 0
                # Reseteamos BONIFICACIÓN al to_hit
                if self.entity.fighter.to_hit_counter > 0:
                    self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                    self.entity.fighter.to_hit_counter = 0

                self.entity.move(move_dx, move_dy)
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

        if player_moved:
            if getattr(self.engine, "register_noise", None):
                is_flying = getattr(self.entity, "is_flying", False) or getattr(getattr(self.entity, "fighter", None), "is_flying", False)
                tag = "flutter" if is_flying else "footsteps"
                self.engine.register_noise(self.entity, level=1, duration=1, tag=tag)
        if player_moved and self.entity is self.engine.player:
            play_player_footstep()
        # Especial de slimes
        elif player_moved and getattr(self.entity.fighter, "is_slime", False):
            inventory = getattr(self.entity, "inventory", None)
            if inventory and len(inventory.items) < inventory.capacity:
                items_here = [
                    item
                    for item in self.engine.game_map.items
                    if self.entity.x == item.x and self.entity.y == item.y
                ]
                for item in list(items_here):
                    if len(inventory.items) >= inventory.capacity:
                        break
                    self.engine.game_map.entities.remove(item)
                    item.parent = inventory
                    inventory.items.append(item)
                    if self.engine.game_map.visible[self.entity.x, self.entity.y]:
                        self.engine.message_log.add_message(
                            f"The slime absorved the {item.name}!", color.orange
                        )

        _finalize_non_player_action()
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
        opener = getattr(self.entity, "fighter", None)
        if opener and not getattr(opener, "can_open_doors", False):
            raise exceptions.Impossible("You can't open that.")
        if fighter.is_open:
            raise exceptions.Impossible("The door is already open.")
        fighter.set_open(True)
        if self.entity is self.engine.player:
            self.engine.message_log.add_message("You open the door.", color.white)
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
        # Closing a door also makes noise.
        if getattr(self.engine, "register_noise", None):
            self.engine.register_noise(self.entity, level=2, duration=2, tag="door")
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost


class WaitAction(Action):
    def perform(self) -> None:
        """
        Wait. Gain +1 to To-Hit and +1 to Defense.
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
            # if self.entity is self.engine.player:
            #     import ipdb;ipdb.set_trace()
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
            # Punto de defensa  y To-Hit GRATIS (e.e. sin gasto de estamina)
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
            


        # Si en melee:
        else: 

            # Stamina check:
            if self.entity.fighter.stamina > 0:

                #self.entity.fighter.defense_bonus += self.entity.fighter.base_defense + self.entity.fighter.armor_value - self.entity.fighter.aggressivity
                self.entity.fighter.stamina -= 1

                # BONIFICADOR a la defensa
                # Límite de bonificación a la defensa por maniobras tácticas
                if self.entity.fighter.to_defense_counter < 3: # Para tener un max de 3 puntos aquí hay que poner 3, no 4. No entiendo por qué.
                    self.entity.fighter.base_defense += 1
                    self.entity.fighter.to_defense_counter += 1

                # BONIFICADOR a to hit
                if self.entity.fighter.to_hit_counter < 3: # Para tener un max de 3 puntos aquí hay que poner 3, no 4. No entiendo por qué.
                    self.entity.fighter.base_to_hit += 1
                    self.entity.fighter.to_hit_counter += 1
     
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
                
                ## Defense reset
                if self.entity.fighter.to_defense_counter > 0:
                    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                    self.entity.fighter.to_defense_counter = 0
                
                # To-Hit reset
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

        if self.entity is self.engine.player:
            self._handle_listen_through_door()

        # Hidden/stealth maintenance for non-player actors (players handled in input_handlers).
        fighter = getattr(self.entity, "fighter", None)
        if fighter and self.entity is not self.engine.player:
            fighter.handle_post_action(True, self.__class__.__name__)

        # TIME SYSTEM
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        if DEBUG_MODE:
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in WaitAction.")
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")
        #pass

    def _handle_listen_through_door(self) -> None:
        """Gestiona la escucha tras una puerta al esperar varios turnos."""
        engine = self.engine
        gamemap = engine.game_map
        px, py = self.entity.x, self.entity.y
        current_pos = (px, py)

        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        adjacent_doors = []
        for dx, dy in deltas:
            nx, ny = px + dx, py + dy
            if gamemap.in_bounds(nx, ny) and gamemap.is_closed_door(nx, ny):
                adjacent_doors.append(((nx, ny), (dx, dy)))

        if not adjacent_doors:
            engine.reset_listen_state()
            return

        prev_door = getattr(engine, "_listen_door_position", None)
        chosen = next((info for info in adjacent_doors if info[0] == prev_door), None)
        if not chosen:
            chosen = adjacent_doors[0]
        door_pos, (dx, dy) = chosen

        if (
            getattr(engine, "_listen_wait_position", None) != current_pos
            or door_pos != prev_door
        ):
            engine._listen_wait_turns = 0

        engine._listen_wait_position = current_pos
        engine._listen_door_position = door_pos
        engine._listen_wait_turns += 1

        if engine._listen_wait_turns < 4:
            return

        engine._listen_wait_turns = 0
        engine.message_log.add_message(
            "You try to listen through the door",
            color.white,
        )
        roll = random.randint(1, 6)
        if DEBUG_MODE:
            print(f"DEBUG: Listen roll 1d6 -> {roll}")

        listen_origin_x = door_pos[0] + dx
        listen_origin_y = door_pos[1] + dy
        if not gamemap.in_bounds(listen_origin_x, listen_origin_y):
            listen_origin_x, listen_origin_y = door_pos

        heard_something = False
        if roll >= 4:
            for actor in gamemap.actors:
                if not isinstance(actor, Actor):
                    continue
                if actor is self.entity or not actor.is_alive:
                    continue
                dot = (actor.x - door_pos[0]) * dx + (actor.y - door_pos[1]) * dy
                if dot < 0:
                    continue
                if actor.distance(listen_origin_x, listen_origin_y) <= 5:
                    heard_something = True
                    break

        if heard_something and roll >= 4:
            engine.message_log.add_message(
                "You hear something on the other side",
                color.orange,
            )
        else:
            engine.message_log.add_message(
                "You don't hear nothing",
                color.white,
            )


class PassAction(Action):
    def perform(self) -> None:
        pass
    
    
class ToogleLightAction(Action):
    def perform(self):
        fighter = self.engine.player.fighter
        in_town = getattr(self.engine.game_world, "current_floor", 0) == 1

        if in_town:
            self.engine.message_log.add_message(
                "Daylight already lights everything here.",
                color.descend,
            )
            return 0

        if fighter.lamp_on:
            fighter.lamp_on = False
            fighter.base_stealth += 2
            self.engine.message_log.add_message("You turn OFF your lamp", color.descend)
        else:
            fighter.lamp_on = True
            fighter.base_stealth -= 2
            self.engine.message_log.add_message("You turn ON your lamp", color.enemy_die)

        if DEBUG_MODE:
            print(f"DEBUG: PLAYER BASE FOV: {fighter.fov}, lamp_on={fighter.lamp_on}")

        self.engine.update_fov()
        return 0
    

#class DefendAction(Action):
#    def perform(self):
#        pass


class BumpAction(ActionWithDirection):

    def perform(self) -> None:
        target = self.target_actor
        if target:
            target_fighter = getattr(target, "fighter", None)
            if target_fighter and getattr(target_fighter, "is_hidden", False):
                target_fighter.break_hide(reason="collision", revealer=self.entity)
                if self.entity is self.engine.player:
                    self.engine.message_log.add_message(
                        f"You bump into {target.name} and reveal them!",
                        color.descend,
                    )
                elif target is self.engine.player:
                    # Player notified inside break_hide.
                    pass
                elif self.engine.game_map.visible[target.x, target.y]:
                    self.engine.message_log.add_message(
                        f"{self.entity.name} bumps into {target.name}, revealing them.",
                        color.descend,
                    )
                # Spend the turn even though no attack occurs.
                self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
                if self.entity is not self.engine.player:
                    self.entity.fighter.handle_post_action(False, self.__class__.__name__)
                return
            self_name = getattr(self.entity, "name", "").lower()
            target_name = getattr(target, "name", "").lower()
            if self_name == "adventurer" and target_name == "adventurer":
                return WaitAction(self.entity).perform()
            if target_name in ("el viejo", "the old man"):
                ai = getattr(target, "ai", None)
                if self.entity is self.engine.player and hasattr(ai, "on_player_bump"):
                    ai.on_player_bump()
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
