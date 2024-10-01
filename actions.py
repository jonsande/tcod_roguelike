# Aquí se definen las acciones (acciones-tipo) a las que se llamará
# desde input_handlers.py

# We define three classes: Action, EscapeAction, and MovementAction. 
# EscapeAction and MovementAction are sub-classes of Action.

from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING

import color
from entity import Actor
import exceptions
import random

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Entity, Item

from color import bcolors


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
                print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in PickupAction")
                print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

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
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in DropItem")
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

        self.entity.inventory.drop(self.item)


class EquipAction(Action):
    def __init__(self, entity: Actor, item: Item):
        super().__init__(entity)

        self.item = item

    def perform(self) -> None:

        # TIME SYSTEM
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in EquipAction")
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

        self.entity.equipment.toggle_equip(self.item)


class TakeStairsAction(Action):
    def perform(self) -> None:
        """
        Take the stairs, if any exist at the entity's location.
        """

        # Pasar de nivel otorga experiencia
        #for e in self.engine.game_map.downstairs_location:
            #if (self.entity.x, self.entity.y) == e:
        if (self.entity.x, self.entity.y) == self.engine.game_map.downstairs_location:

            # TIME SYSTEM
            # Bajar escaleras gasta puntos de tiempo
            #self.entity.fighter.current_energy_points -= 10
            self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in TakeStairsAction")
            print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")

            if self.engine.game_world.current_floor > 1:
                xp_amount = (self.engine.game_world.current_floor * 5) + 10
                self.entity.level.add_xp(xp_amount)
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You descend the staircase.", color.descend
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

        target = self.target_actor

        if not target:
            raise exceptions.Impossible("Invalid target")
        
        if self.entity.fighter.stamina <= 0:
            self.engine.message_log.add_message("You are exhausted!", color.red)
            raise exceptions.Impossible("")
        
        hit_dice = random.randint(1, 6) + self.entity.fighter.to_hit

        # Desequipar objeto (si está equipado)
        if self.entity.equipment.item_is_equipped(self.item):
            self.entity.equipment.toggle_equip(self.item)

        # Colocar el objeto lanzado en la casilla del objetivo
        self.engine.player.inventory.throw(self.item, self.target_actor.x, self.target_actor.y)

        # Mecánica backstab/stealth/sigilo (beta)
        # Bonificador al impacto
        if self.is_dummy_object(target.ai) == False:
            if target.fighter.aggravated == False:
                #import ipdb;ipdb.set_trace()
                hit_dice += self.entity.fighter.luck
                print("DEBUG: ATAQUE SIGILOSO!")

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

                    if poison_roll >= 1:

                        if self.entity is self.engine.player:
                            print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                f"{target.name} is POISONED! (The {self.entity.name} was poisonous)", damage_color
                            )
                        else:
                            print(f"Your are POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                f"You are POISONED! (The {self.entity.name} was poisonous)", damage_color
                            )

                        target.fighter.is_poisoned = True
                        target.fighter.poisoned_counter += 5
                        target.fighter.poison_dmg = 1
                        self.entity.fighter.poisons_on_hit = False

            damage = self.entity.fighter.power + random.randint(self.entity.fighter.dmg_mod[0], self.entity.fighter.dmg_mod[1]) - target.fighter.armor_value

            # Mecánica backstab/stealth/sigilo (beta)
            # Bonificador al daño
            if isinstance(target, Actor):
                if self.is_dummy_object(target.ai) == False:
                    if target.fighter.aggravated == False:
                        damage = (damage + self.entity.fighter.luck) * 2
                        print("DEBUG: DAÑO BACKSTAB EXTRA: ", damage)
                        target.fighter.aggravated = True

            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"

            # Si hace daño...
            if damage > 0:
                
                print(f"{attack_desc} for {damage} hit points ({hit_dice} VS {target.fighter.defense})")
                self.engine.message_log.add_message(
                    f"{attack_desc} for {damage} hit points ({hit_dice} VS {target.fighter.defense})", damage_color
                )
                target.fighter.hp -= damage

            # Si no hace daño
            else:

                # Reseteamos la BONIFICACIÓN
                #if self.entity.fighter.to_hit_counter > 0:
                    # se resta el bonificador al daño...
                    #self.entity.fighter.base_power -= self.entity.fighter.to_power_counter
                    # ...o a la tirada de daño
                    #self.entity.fighter.dmg_mod[1] -= self.entity.fighter.to_power_counter
                    # ...o al to hit
                    #self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter

                    # reseteamos el contador de bonificación
                    #self.entity.fighter.to_hit_counter = 0


                print(f"{attack_desc} but does no damage.")
                self.engine.message_log.add_message(
                    f"{attack_desc} but does no damage."
                )
        
        # Si no impacta:
        else:

            # Reseteamos la BONIFICACIÓN
            if self.entity.fighter.to_hit_counter > 0:
                # se resta el bonificador al daño...
                #self.entity.fighter.base_power -= self.entity.fighter.to_power_counter
                # ...o a la tirada de daño
                #self.entity.fighter.dmg_mod[1] -= self.entity.fighter.to_power_counter
                # ...o al to hit
                #self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                self.entity.fighter.base_to_hit -= 1

                # reseteamos el contador de bonificación
                #self.entity.fighter.to_hit_counter = 0
                self.entity.fighter.to_hit_counter -= 1


            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"

            print(f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})")
            self.engine.message_log.add_message(
                f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})"
            )

        # Con cada ataque gastamos 1 de stamina
        self.entity.fighter.stamina -= 1

        # TIME SYSTEM
        # Con cada ataque gastamos el coste de puntos de tiempo por acción de cada luchador 
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in MeleeAction")
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")


        # Con cada ataque reducimos 1 el defense bonus acumulado

        if self.entity.fighter.to_defense_counter > 1:
            self.entity.fighter.base_defense -= 1
            self.entity.fighter.to_defense_counter -= 1

        # ...o reducimos a 0 el defense bonus acumulado
        #if self.entity.fighter.to_defense_counter >= 1:
        #    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
        #    self.entity.fighter.to_defense_counter = 0


class MeleeAction(ActionWithDirection):

    # def is_door_object(self, obj):
    #     from components.fighter import Door  # Importa la clase Door
    #     return isinstance(obj, Door)  # Comprueba si obj es una instancia de Door
    
    def is_dummy_object(self, obj):
        #from components.fighter import Door  # Importa la clase Door
        from components.ai import Dummy
        #from entity import Obstacle
        #return isinstance(obj, Door)  # Comprueba si obj es una instancia de Door
        return isinstance(obj, Dummy)

    def perform(self) -> None:

        target = self.target_actor

        if not target:
            raise exceptions.Impossible("Nothing to attack.")
        
        if self.entity.fighter.stamina <= 0:
            self.engine.message_log.add_message("You are exhausted!", color.red)
            raise exceptions.Impossible("")
        
        hit_dice = random.randint(1, 6) + self.entity.fighter.to_hit

        # Mecánica backstab/stealth/sigilo (beta)
        # Bonificador al impacto
        if self.is_dummy_object(target.ai) == False:

            if target.fighter.aggravated == False:
                #import ipdb;ipdb.set_trace()
                hit_dice += self.entity.fighter.luck
                print("DEBUG: ATAQUE SIGILOSO!")

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
            
            # Mecánica ataque envenenado
            if self.entity.fighter.poisons_on_hit == True:

                from components.ai import Dummy
                #if isinstance(target.ai, Dummy) == False:
                if self.is_dummy_object(target.ai) == False:

                    poison_roll = random.randint(1, 6)

                    if poison_roll >= 1:

                        if self.entity is self.engine.player:
                            print(f"{target.name} is POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                f"{target.name} is POISONED! (The {self.entity.name} was poisonous)", damage_color
                            )
                        else:
                            print(f"Your are POISONED! (The {self.entity.name} was poisonous)")
                            self.engine.message_log.add_message(
                                f"You are POISONED! (The {self.entity.name} was poisonous)", damage_color
                            )

                        target.fighter.is_poisoned = True
                        target.fighter.poisoned_counter += 5
                        target.fighter.poison_dmg = 1
                        self.entity.fighter.poisons_on_hit = False

            damage = self.entity.fighter.power + random.randint(self.entity.fighter.dmg_mod[0], self.entity.fighter.dmg_mod[1]) - target.fighter.armor_value
            
            # Mecánica backstab/stealth/sigilo (beta)
            # Bonificador al daño
            #from components.ai import Dummy
            #if isinstance(target, Actor) and target.ai_cls != Dummy:
            if isinstance(target, Actor):
            #if not self.is_dummy_object(target.fighter):
                if self.is_dummy_object(target.ai) == False:
                    if target.fighter.aggravated == False:
                        damage = (damage + self.entity.fighter.luck) * 2
                        print("DEBUG: DAÑO BACKSTAB EXTRA: ", damage)
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
                    #self.entity.fighter.base_power += 1
                    ### A.2) ... o la tirada de daño
                    #self.entity.fighter.dmg_mod[1] += 1

                    ## B) Los impactos aumentan el To Hit:
                    #self.entity.fighter.base_to_hit += 1

                    # Contabilizamos el bonus:
                    #self.entity.fighter.to_hit_counter += 1

                    # DEBUG
                    #print(f"power_hits_counter: {power_hits_counter}")
                    #print(f"base_power: {self.entity.fighter.base_power}")

                print(f"{attack_desc} for {damage} hit points ({hit_dice} VS {target.fighter.defense})")
                self.engine.message_log.add_message(
                    f"{attack_desc} for {damage} hit points ({hit_dice} VS {target.fighter.defense})", damage_color
                )
                target.fighter.hp -= damage

            # Si no hace daño
            else:

                # Reseteamos la BONIFICACIÓN
                #if self.entity.fighter.to_hit_counter > 0:
                    # se resta el bonificador al daño...
                    #self.entity.fighter.base_power -= self.entity.fighter.to_power_counter
                    # ...o a la tirada de daño
                    #self.entity.fighter.dmg_mod[1] -= self.entity.fighter.to_power_counter
                    # ...o al to hit
                    #self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter

                    # reseteamos el contador de bonificación
                    #self.entity.fighter.to_hit_counter = 0


                print(f"{attack_desc} but does no damage.")
                self.engine.message_log.add_message(
                    f"{attack_desc} but does no damage."
                )
        
        # Si no impacta:
        else:

            # Reseteamos la BONIFICACIÓN
            if self.entity.fighter.to_hit_counter > 0:
                # se resta el bonificador al daño...
                #self.entity.fighter.base_power -= self.entity.fighter.to_power_counter
                # ...o a la tirada de daño
                #self.entity.fighter.dmg_mod[1] -= self.entity.fighter.to_power_counter
                # ...o al to hit
                #self.entity.fighter.base_to_hit -= self.entity.fighter.to_hit_counter
                self.entity.fighter.base_to_hit -= 1

                # reseteamos el contador de bonificación
                #self.entity.fighter.to_hit_counter = 0
                self.entity.fighter.to_hit_counter -= 1


            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"

            print(f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})")
            self.engine.message_log.add_message(
                f"{attack_desc} but FAILS ({hit_dice}vs{target.fighter.defense})"
            )

        # Con cada ataque gastamos 1 de stamina
        self.entity.fighter.stamina -= 1

        # TIME SYSTEM
        # Con cada ataque gastamos el coste de puntos de tiempo por acción de cada luchador 
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in MeleeAction")
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")


        # Con cada ataque reducimos 1 el defense bonus acumulado

        if self.entity.fighter.to_defense_counter > 1:
            self.entity.fighter.base_defense -= 1
            self.entity.fighter.to_defense_counter -= 1

        # ...o reducimos a 0 el defense bonus acumulado
        #if self.entity.fighter.to_defense_counter >= 1:
        #    self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
        #    self.entity.fighter.to_defense_counter = 0


class MovementAction(ActionWithDirection):

    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy

        # Si en MELEE
        if self.entity.fighter.is_in_melee:

            if not self.engine.game_map.in_bounds(dest_x, dest_y):
                # Destination is out of bounds.
                raise exceptions.Impossible("That way is blocked.")
            if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
                # Destination is blocked by a tile.
                raise exceptions.Impossible("That way is blocked.")
            if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
                # Destination is blocked by an entity.
                raise exceptions.Impossible("That way is blocked.")

            # BONIFICADOR a la defensa
            if self.entity.fighter.to_defense_counter < 3:
                self.entity.fighter.base_defense += 1
                self.entity.fighter.to_defense_counter += 1
            
            # PENALIZACIÓN a To Hit
            if self.entity.fighter.to_hit_counter >= 1:
                self.entity.fighter.base_to_hit -= 1
                self.entity.fighter.to_hit_counter -= 1

            self.entity.move(self.dx, self.dy)            
           
        # Si no en MELEE 
        else:

            if not self.engine.game_map.in_bounds(dest_x, dest_y):
                # Destination is out of bounds.
                raise exceptions.Impossible("That way is blocked.")
            if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
                # Destination is blocked by a tile.
                raise exceptions.Impossible("That way is blocked.")
            if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
                # Destination is blocked by an entity.
                raise exceptions.Impossible("That way is blocked.")
            
            # Reseteamos BONIFICADOR a la defensa
            if self.entity.fighter.to_defense_counter > 0:
                self.entity.fighter.base_defense -= self.entity.fighter.to_defense_counter
                self.entity.fighter.to_defense_counter = 0

            self.entity.move(self.dx, self.dy)

        # Reseteamos toda BONIFICACIÓN

        # Reseteamos power bonus
        #if self.entity.fighter.to_power_counter >= 1:
        #    self.entity.fighter.base_power -= self.entity.fighter.to_power_counter
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
        if self.entity.fighter.stamina < self.entity.fighter.max_stamina:
            self.entity.fighter.stamina += 1
            #print(f"{self.entity.name}: stamina: {self.entity.fighter.stamina}")

        # TIME SYSTEM
        #self.entity.fighter.current_energy_points -= 10
        self.entity.fighter.current_time_points -= self.entity.fighter.action_time_cost
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in MovementAction")
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")


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
            #self.entity.fighter.base_power -= self.entity.fighter.to_power_counter
            #self.entity.fighter.dmg_mod[1] -= self.entity.fighter.to_power_counter
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
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: spends {self.entity.fighter.action_time_cost} t-pts in WaitAction.")
        print(f"{bcolors.OKBLUE}{self.entity.name}{bcolors.ENDC}: {self.entity.fighter.current_time_points} t-pts left.")
        #pass


class PassAction(Action):
    def perform(self) -> None:
        pass
    
    
class ToogleLightAction(Action):
    def perform(self):
        print(f"PLAYER FOV: {self.engine.player.fighter.fov}")
        if self.engine.player.fighter.fov == 6:
            self.engine.player.fighter.base_stealth += 1
            self.engine.player.fighter.fov = 1
            #print(f"PLAYER FOV: {self.engine.player.fighter.fov}")
            self.engine.message_log.add_message("You turn off your lamp", color.descend)
            return 0
        if self.engine.player.fighter.fov == 1:
            self.engine.player.fighter.fov = 6
            self.engine.player.fighter.base_stealth -= 1
            #print(f"PLAYER FOV: {self.engine.player.fighter.fov}")
            self.engine.message_log.add_message("You turn on your lamp", color.descend)
            return 0
    

#class DefendAction(Action):
#    def perform(self):
#        pass


class BumpAction(ActionWithDirection):

    def perform(self) -> None:
        if self.target_actor:
            return MeleeAction(self.entity, self.dx, self.dy).perform()

        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()
        