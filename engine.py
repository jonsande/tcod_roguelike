"""'Engine' class will take the responsibilities of drawing 
the map and entities, as well as handling the player’s input."""

from __future__ import annotations

import random

import lzma
import pickle
from typing import TYPE_CHECKING

from tcod.context import Context
from tcod.console import Console
from tcod.map import compute_fov
from tcod import constants

import components.ai
import components.base_component
import exceptions
from message_log import MessageLog
import color
import render_functions
from entity import Actor

if TYPE_CHECKING:
    from entity import Actor, Obstacle
    from game_map import GameMap, GameWorld
    
#import gc
import components.fighter
#import entity_factories


# Calendario:
#calendar = {}


class Engine:

    game_map: GameMap
    game_world: GameWorld

    def __init__(self, player: Actor, debug: bool = False):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.player = player
        self.turn = 0
        self.autoheal_counter = 0
        self.satiety_counter = 0
        self.temporal_effects = []
        self.center_room_array = []
        self.identified_items = []
        self.debug = debug

    def clock(self):
        """
        # EXTRA TURN CONDITIONS
        for entity in set(self.game_map.actors) - {self.player}:
            
            if entity.fighter.current_time_points > 20:

                print(f"{color.bcolors.OKCYAN}{entity.name} {color.bcolors.OKCYAN}EXTRA TURN{color.bcolors.ENDC}!")
                
                #entity.fighter.current_time_points = 0

                #for entity in set(self.game_map.actors) - {self.player}:
                if entity.ai:
                    try:
                        entity.ai.perform()
                    except exceptions.Impossible:
                        entity.fighter.current_time_points = 0
                        print(f"{color.bcolors.OKCYAN}{entity.name}{color.bcolors.ENDC}: {entity.fighter.current_time_points} t-pts.")
                        pass  # Ignore impossible action exceptions from AI.

                entity.fighter.current_time_points = 0
                print(f"{color.bcolors.OKCYAN}{entity.name}{color.bcolors.ENDC}: {entity.fighter.current_time_points} t-pts.")
        """

        self.turn += 1
        """
        # TIME SYSTEM

        print(f"\n{color.bcolors.WARNING}¡The clock tiks!{color.bcolors.ENDC}")
        print("\nAll actors gain 10 t-pts")

        for entity in set(self.game_map.actors):

            #if entity.fighter.current_time_points < 0:
            #    entity.fighter.current_time_points = 0

            entity.fighter.current_time_points += 10
            print(f"{entity.name}: {entity.fighter.current_time_points} t-pts")
        """

            
    def what_time_it_is(self):
        return self.turn
    

    def restore_time_pts(self):
        print(f"\n{color.bcolors.WARNING}End turn fase{color.bcolors.ENDC}")
        print("All actors gain 10 t-pts")

        for entity in set(self.game_map.actors):

            #if entity.fighter.current_time_points < 0:
            #    entity.fighter.current_time_points = 0

            entity.fighter.current_time_points += 10
            print(f"{entity.name}: {entity.fighter.current_time_points} t-pts")


    def extra_turn_manager(self):
        # EXTRA TURN CONDITIONS
        for entity in set(self.game_map.actors) - {self.player}:
            
            if entity.fighter.current_time_points > 20:

                if self.debug == True:
                    print(f"{color.bcolors.OKCYAN}{entity.name} {color.bcolors.OKCYAN}EXTRA TURN{color.bcolors.ENDC}!")
                
                #entity.fighter.current_time_points = 0

                #for entity in set(self.game_map.actors) - {self.player}:
                if entity.ai:
                    try:
                        entity.ai.perform()
                    except exceptions.Impossible:
                        entity.fighter.current_time_points = 0
                        if self.debug == True:
                            print(f"{color.bcolors.OKCYAN}{entity.name}{color.bcolors.ENDC}: {entity.fighter.current_time_points} t-pts.")
                        pass  # Ignore impossible action exceptions from AI.

                entity.fighter.current_time_points = 0
                if self.debug == True:
                    print(f"{color.bcolors.OKCYAN}{entity.name}{color.bcolors.ENDC}: {entity.fighter.current_time_points} t-pts.")


    """
    # DEFAULT:
    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - {self.player}:
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass  # Ignore impossible action exceptions from AI.
    """


    def handle_enemy_turns(self) -> None:
        #for entity in set(self.game_map.actors):
        #    if entity.fighter.current_energy_points == 0:
        #        pass

        for entity in set(self.game_map.actors) - {self.player}:

            #if entity.fighter.current_time_points < 0:
            #    return exceptions.Impossible
            #else:
            
            if entity.ai:
                if entity.fighter.current_time_points >= entity.fighter.action_time_cost:
                    try:
                        entity.ai.perform()
                    except exceptions.Impossible:
                        pass  # Ignore impossible action exceptions from AI.


    def update_fov(self) -> None:
        
        if self.game_world.current_floor == 1:
            radius = 90
        else:
            #radius = random.randint(4,5) + self.player.fighter.fov
            #radius = random.randint(self.player.fighter.fov - 1, self.player.fighter.fov)
            #radius = self.player.fov
            
            #radius = random.randint(0, 1) + entity_factories.player.fighter.fov
            radius = random.randint(0, 1) + self.player.fighter.fov
            #print(f"radius: {radius}")


        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles['transparent'],
            (self.player.x, self.player.y),
            #radius = random.randint(3,5)
            radius,
            algorithm=constants.FOV_SHADOW
        )



        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible

        # Esto hace el efecto sombra. Comentar entero para usar el sistema
        # de "memoria" típico.
        """
        self.game_map.explored[:] = compute_fov(
            self.game_map.tiles['transparent'],
            (self.player.x, self.player.y),
            #radius = random.randint(5,6)
            radius + 2
        )"""


    def update_fov_alt(self) -> None:

        #radius = random.randint(4,5)
        radius = 90

        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles['transparent'],
            (self.player.x, self.player.y),
            #radius = random.randint(3,5)
            radius
        )
        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible

        # Esto hace el efecto sombra. Comentar entero para usar el sistema
        # de "memoria" típico.
        #self.game_map.explored[:] = compute_fov(
        #    self.game_map.tiles['transparent'],
        #    (self.player.x, self.player.y),
        #    #radius = random.randint(5,6)
        #    radius + 3
        #)


    def autohealmonsters(self):
        self.autoheal_counter += 1
        if self.autoheal_counter == 50:
            
            for obj in set(self.game_map.actors) - {self.player}:
            #for obj in gc.get_objects():
                if isinstance(obj, components.fighter.Fighter):
                    components.fighter.Fighter.autoheal(obj)

            self.player.fighter.autoheal()

            self.autoheal_counter = 0


    def update_hunger(self): 
        self.satiety_counter += 1
        if self.satiety_counter == 50:
            self.player.fighter.satiety -= 1
            self.satiety_counter = 0

            if self.player.fighter.satiety == 16:
                self.message_log.add_message("You are hungry", color.red)

            if self.player.fighter.satiety == 8:
                self.message_log.add_message("You are starving!", color.red)

            if self.player.fighter.satiety == 1:
                self.message_log.add_message("You are going to starve very soon!", color.red)

            if self.player.fighter.satiety == 0:
                self.message_log.add_message("You starve to death", color.red)
                self.player.fighter.die()


    def update_poison(self):
        for actor in set(self.game_map.actors):
            if actor.fighter.is_poisoned:
                actor.fighter.poisoned()


    def update_center_rooms_array(self, room_list):
        self.center_room_array = room_list
    

    def update_melee_indicator(self):
        self.player.fighter.is_in_melee = False
        self.player.fighter.aggravated = False # Para la gestión del stealth attack de los enemigos

        for obj in set(self.game_map.actors) - {self.player}:
            # Lo que tienen en común todos los objetos rompibles
            # que no son enemigos es que tienen la ia_cls "Dummy".
            #if obj.is_alive and obj.name != "Door" and obj.name != "Suspicious wall" and obj.name != "Table" and obj.name != "Fire place":
            #if obj.is_alive and self.is_dummy_object(obj):
            
            if isinstance(obj, Actor) and obj.is_alive and obj.ai_cls != components.ai.Dummy:
                
                if self.game_map.visible[obj.x, obj.y]:
                    distance = int(obj.distance(self.player.x, self.player.y))
                    self.player.fighter.aggravated = True # Para la gestión del stealth attack de los enemigos
                    #print(distance)
                    if distance > 0:
                        if distance <= 1:
                            self.player.fighter.is_in_melee = True
                            # DEBUG:
                            #print(f"Enemigo detectado: {obj.name}")
                            #print(f"Distancia: {distance}")
                            #print(f"Visible: {self.game_map.visible[obj.x, obj.y]}")
                    if distance == 2:
                        self.player.fighter.fortified = True


    def manage_temporal_effects(self, turns, amount, attribute, message_down):
        self.temporal_effects.append([turns, amount, attribute, message_down])

        print(f"Active effects: {self.temporal_effects}")
        

    def update_temporal_effects(self):
        effects_to_remove = []
        if self.temporal_effects:

            for i in range(len(self.temporal_effects)):
                turns, amount, attribute, message_down = self.temporal_effects[i]
                print("[DEBUG]: ", self.temporal_effects[i])
                print("[DEBUG]: ", turns)
                print("[DEBUG]: ", amount)
                print("[DEBUG]: ", attribute)
                print("[DEBUG]: ", message_down)
                if turns <= 0:
                    self.message_log.add_message(f"{message_down}", color.red)
                    if attribute == 'base_power':
                        self.player.fighter.base_power -= amount
                    if attribute == 'base_to_hit':
                        self.player.fighter.base_to_hit -= amount
                    if attribute == 'base_stealth':
                        self.player.fighter.base_stealth -= amount

                    #temporal_effects.pop(i)
                    effects_to_remove.append(self.temporal_effects[i])
                    #print(f"Active effects: {self.temporal_effects}")

                else: 
                    self.temporal_effects[i][0] -= 1
                    #print(f"Active effects: {self.temporal_effects}")

            # Eliminar los efectos marcados para remover
            for effect in effects_to_remove:
                self.temporal_effects.remove(effect)


    #def simple_spawn():
    #    pass
    # Las entidades ya tienen un método spawn


    def render(self, console: Console) -> None:

        self.game_map.render(console)

        # La Barra de vida
        # La posición en pantalla de la barra de vida se ajusta
        # en render_functions.py, en la función 'render_bar()'
        render_functions.render_bar(
            console=console,
            current_value=self.player.fighter.hp,
            maximum_value=self.player.fighter.max_hp,
            current_stamina=self.player.fighter.stamina,
            max_stamina=self.player.fighter.max_stamina,
            total_width=15,
        )

        # Log de mensajes que se imprimen en pantalla
        self.message_log.render(console=console, x=1, y=39, width=60, height=4)

        # Indicador del nivel de la mazmorra
        if self.game_world.current_floor == 1:
            render_functions.render_dungeon_level(
                console=console,
                dungeon_level="Town",
                location=(60, 42),
            )
        else: 
            render_functions.render_dungeon_level(
            console=console,
            dungeon_level=self.game_world.current_floor - 1,
            location=(61, 42),
            )
        
        # Inspección de objetos
        render_functions.render_names_at_mouse_location(
            #console=console, x=51, y=37, engine=self
            console=console, x=1, y=1, engine=self
        )
        

        # Combat mode indicator:
        if self.player.fighter.is_in_melee == True:
            render_functions.render_combat_mode(
                console=console, 
                hit=self.player.fighter.to_hit, 
                power=self.player.fighter.power, 
                defense=self.player.fighter.defense
            )

        # Fortity indicator
        #if self.player.fighter.can_fortify == True and self.player.fighter.fortified == True:
        if self.player.fighter.fortified == True:
            #render_functions.render_fortify_indicator(console)
            pass


    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)