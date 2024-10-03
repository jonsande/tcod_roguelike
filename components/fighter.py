from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

import color
from components.base_component import BaseComponent
from render_order import RenderOrder

if TYPE_CHECKING:
    from entity import Actor, Obstacle

x = 0

# ESTO NO SÉ SI TIENE ALGUNA UTILIDAD AHORA MISMO (pero creo que no):
turns = 0
gainance = 0

from components.ai import HostileEnemy
class Fighter(BaseComponent):

    parent: Actor

    def __init__(
            self, 
            hp: int, 
            base_defense: int, 
            base_power: int, 
            recover_rate: int, 
            fov: int = 0, 
            dmg_mod: Tuple[int, int] = (0, 1),
            base_stealth: int = 0,
            aggressivity: int = 0,
            wait_counter: int = 0,
            base_to_hit: int = 0,
            base_armor_value: int = 0,
            temporal_effects: bool = False,
            luck: int = 0,
            critical_chance: int = 2,
            satiety: int = 32,
            max_satiety: int = 32,
            stamina: int = 3,
            max_stamina: int = 3,
            is_in_melee: bool = False,
            defending: bool = False,
            to_hit_counter: int= 0,
            to_power_counter: int= 0,
            to_defense_couter: int = 0,
            #energy_points: int = 10,
            #current_energy_points: int = 10,
            current_time_points: int = 10,
            action_time_cost: int = 10,
            can_fortify: bool = False,
            fortified: bool = False,
            woke_ai_cls = HostileEnemy,
            poisons_on_hit: bool = False,
            is_poisoned: bool = False,
            poisoned_counter: int = 0,
            poison_dmg: int = 0,
            poison_resistance: int = 0,
            ):
        self.max_hp = hp
        self._hp = hp
        self.base_defense = base_defense
        self.base_power = base_power
        self.recover_rate = recover_rate
        self.fov = fov
        self.dmg_mod = dmg_mod
        self.base_stealth = base_stealth
        self.location = (0, 0)
        self.aggravated = False
        self.aggressivity = aggressivity
        self.wait_counter = wait_counter
        self.base_to_hit = base_to_hit
        self.base_armor_value = base_armor_value
        self.temporal_effects = temporal_effects
        self.luck = luck
        self.satiety = satiety
        self.max_satiety = max_satiety
        self.stamina = stamina
        self.max_stamina = max_stamina
        self.is_in_melee = is_in_melee
        self.defending = defending
        self.to_hit_counter = to_hit_counter
        self.to_power_counter = to_power_counter
        self.to_defense_counter = to_defense_couter
        self.critical_chance = critical_chance + luck

        #self.energy_points = energy_points
        #self.current_energy_points = current_energy_points

        self.current_time_points = current_time_points
        self.action_time_cost = action_time_cost

        self.can_fortify = can_fortify
        self.fortified = fortified
        
        self.woke_ai_cls = woke_ai_cls
        
        self.poisons_on_hit = poisons_on_hit
        
        self.is_poisoned = is_poisoned
        self.poisoned_counter = poisoned_counter
        self.poison_dmg = poison_dmg

        # Resistances
        self.poison_resistance = poison_resistance

        

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
        return self.base_power + self.power_bonus
    
    @property
    def stealth(self) -> int:
        return self.base_stealth + self.stealth_bonus - self.stealth_penalty
    
    @property
    def to_hit(self) -> int:
        result = self.base_to_hit + self.to_hit_bonus - self.to_hit_penalty
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
    def power_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.power_bonus
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
        
    @property
    def to_hit_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.to_hit_bonus
        else:
            return 0
        
    @property
    def to_hit_penalty(self) -> int:
        if self.parent.equipment:
            # Por algún motivo esto está retornando 0
            return self.parent.equipment.to_hit_penalty
        else:
            return 0
        
    @property
    def armor_value_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.armor_value_bonus
        else:
            return 0
    
    def poisoned(self):
        
        if self.is_poisoned:
        
            total_damage = (self.poisoned_counter * self.poison_dmg) - self.poison_resistance
            print(">>>>>>>>>>>>>>> self.poison_resistance = ", self.poison_resistance)
            
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
        import entity_factories
        max_drop = self.parent.inventory.capacity

        if max_drop <= 0:

            return 0
        
        else:

            if self.parent.name == "Adventurer" and self.parent.fighter.hp == 32:
                chances = 12

            else:
                chances = 1 + self.engine.player.fighter.luck
                inventory = self.parent.inventory.items # Esto devuelve una lista

            try:
                loot = entity_factories.drop_roulette(chances, inventory)
                loot.spawn(self.gamemap, self.parent.x, self.parent.y)

            except AttributeError:
                pass

    def die(self) -> None:

        #self.engine.player.fighter.is_in_melee = False

        if self.engine.player is self.parent:
            death_message = "You died!"
            death_message_color = color.player_die
        else:
            death_message = f"{self.parent.name} is dead!"
            death_message_color = color.enemy_die


        self.parent.char = "%"
        self.parent.color = (160, 160, 160)
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = f"remains of {self.parent.name}"
        self.parent.render_order = RenderOrder.CORPSE

        print(death_message)
        self.engine.message_log.add_message(death_message, death_message_color)

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

        if self.engine.player is self.parent:
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
        if self.hp == self.max_hp:
            return 0
        
        # new_hp_value = self.hp + 1
        new_hp_value = self.hp + self.recover_rate

        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp

        self.hp = new_hp_value

    def take_damage(self, amount: int) -> None:
        self.hp -= amount

        
    # ESTA FUNC TIENE QUE SER SUSTITUIDA POR gain_temporal_bounus() de más abajo
    def gain_temporal_power(self, turns, amount):

        self.base_power += amount
        self.temporal_effects = True

        self.engine.message_log.add_message(
            f"You feel strong!",
            color.status_effect_applied,
        )
        import input_handlers
        input_handlers.number_of_turns = turns
        input_handlers.amount_affected = amount

    def gain_temporal_bonus(self, turns, amount, attribute, message_hi, message_down):

        if attribute == 'base_power':
            self.base_power += amount
        if attribute == 'base_to_hit':
            self.base_to_hit += amount
        if attribute == 'base_stealth':
            self.base_stealth += amount

        self.temporal_effects = True

        self.engine.message_log.add_message(
            f"{message_hi}",
            color.status_effect_applied,
        )
        #import input_handlers
        #input_handlers.number_of_turns = turns
        #input_handlers.amount_affected = amount

        self.engine.manage_temporal_effects(turns, amount, attribute, message_down)
    
    def decrease_power(self, amount: int):
        self.base_power -= amount

    def restore_power(self, amount: int):
        self.base_power += amount
        
    def gain_power(self, amount: int):
        self.base_power += amount

        
class Door(BaseComponent):

    parent: Obstacle

    def __init__(
            self, hp: int, 
            base_defense: int, 
            base_power: int, 
            recover_rate: int, 
            fov: int, 
            dmg_mod: Tuple[int, int] = (0, 1),
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
            ):
        self.max_hp = hp
        self._hp = hp
        self.base_defense = base_defense
        self.base_power = base_power
        self.recover_rate = recover_rate
        self.fov = fov
        self.dmg_mod = dmg_mod
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
        return self.base_power + self.power_bonus
    
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
    def power_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.power_bonus
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
            import entity_factories
            max_drop = self.parent.inventory.capacity

            if max_drop <= 0:

                return 0
            
            else:

                chances = 1
                inventory = self.parent.inventory.items # Esto devuelve una lista

                try:
                    loot = entity_factories.drop_roulette(chances, inventory)
                    loot.spawn(self.gamemap, self.parent.x, self.parent.y)

                except AttributeError:
                    
                    return 0


    def die(self) -> None:
        death_message = f"{self.parent.name} is down!"
        death_message_color = color.enemy_die

        self.parent.char = '"'
        #self.parent.color = (200,200,200)
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = f"remains of {self.parent.name}"
        self.parent.render_order = RenderOrder.CORPSE

        
        # Si la puerta es destruida, cambia el tile de su posición
        # por un tile que no bloquee la visión
        """
        die_x = self.parent.spawn_coord[0]
        die_y = self.parent.spawn_coord[1]

        import tile_types
        print(self.engine.game_map.tiles[die_x, die_y])
        print(self.parent.spawn_coord)

        self.engine.game_map.tiles[die_x, die_y] = tile_types.floor        
        #dungeon.tiles[die_x, die_y] = tile_types.floor
        """

        print(death_message)
        self.engine.message_log.add_message(death_message, death_message_color)

        self.engine.player.level.add_xp(self.parent.level.xp_given)

        return self.drop_loot()


    def heal(self, amount: int) -> int:
        if self.hp == self.max_hp:
            return 0

        new_hp_value = self.hp + amount

        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp

        amount_recovered = new_hp_value - self.hp

        self.hp = new_hp_value

        return amount_recovered
    

    def autoheal(self):
        if self.hp == self.max_hp:
            return 0
        
        # new_hp_value = self.hp + 1
        new_hp_value = self.hp + self.recover_rate

        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp

        self.hp = new_hp_value

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
    

    def gain_temporal_power(self, turns, amount):

        self.base_power += amount
        self.temporal_effects = True

        self.engine.message_log.add_message(
            f"You feel strong!",
            color.status_effect_applied,
        )
        import input_handlers
        input_handlers.number_of_turns = turns
        input_handlers.amount_affected = amount

    
    def decrease_power(self, amount: int):
        self.base_power -= amount


    def restore_power(self, amount: int):
        self.base_power += amount