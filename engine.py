"""'Engine' class will take the responsibilities of drawing 
the map and entities, as well as handling the player’s input."""

from __future__ import annotations

import random

import lzma
import pickle
from typing import TYPE_CHECKING, List, Sequence, Tuple

import tcod
from tcod.context import Context
from tcod.console import Console
from tcod.map import compute_fov
from tcod import constants
import settings

import components.ai
import components.base_component
import exceptions
from message_log import MessageLog
import color
import render_functions
from entity import Actor
from render_order import RenderOrder

if TYPE_CHECKING:
    from entity import Actor
    from game_map import GameMap, GameWorld
    
#import gc
import components.fighter
import entity_factories
from components.ai import Dummy

AnimationGlyph = Tuple[int, int, str, Tuple[int, int, int]]
AnimationFrame = Tuple[List[AnimationGlyph], float]


# Calendario:
#calendar = {}


class Engine:

    game_map: GameMap
    game_world: GameWorld

    _CAMPFIRE_FLICKER_COLORS: Tuple[Tuple[int, int, int], ...] = (
        (255, 200, 80),
        (255, 170, 0),
        (255, 145, 40),
        (255, 110, 10),
        (255, 220, 120),
    )
    _CAMPFIRE_CHAR: str = "*"
    _CAMPFIRE_SCROLL_CHANCE: float = settings.CAMPFIRE_SCROLL_DROP_CHANCE
    _ADVENTURER_FLICKER_COLORS: Tuple[Tuple[int, int, int], ...] = (
        (255, 255, 200),
        (240, 220, 160),
        (255, 245, 180),
        (230, 200, 150),
        (255, 255, 230),
    )

    def __init__(self, player: Actor, debug: bool = False):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.player = player
        if settings.GOD_MODE:
            self.player.fighter.fov = 90
        self.turn = 0
        self.autoheal_counter = 0
        self.satiety_counter = 0
        self.spawn_monsters_counter = 0
        self.temporal_effects = []
        self.center_room_array = []
        self.identified_items = []
        self.debug = debug
        self._animation_queue: List[List[AnimationFrame]] = []

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

            if isinstance(entity.ai, Dummy) == False:
            
                if entity.fighter.current_time_points > 20:

                    if self.debug == True:
                        print(f"DEBUG: {color.bcolors.OKCYAN}{entity.name} {color.bcolors.OKCYAN}EXTRA TURN{color.bcolors.ENDC}!")
                    
                    #entity.fighter.current_time_points = 0

                    #for entity in set(self.game_map.actors) - {self.player}:
                    if entity.ai:
                        try:
                            entity.ai.perform()
                        except exceptions.Impossible:
                            entity.fighter.current_time_points = 0
                            if self.debug == True:
                                print(f"DEBUG: {color.bcolors.OKCYAN}{entity.name}{color.bcolors.ENDC}: {entity.fighter.current_time_points} t-pts.")
                            pass  # Ignore impossible action exceptions from AI.

                    entity.fighter.current_time_points = 0
                    if self.debug == True:
                        print(f"DEBUG: {color.bcolors.OKCYAN}{entity.name}{color.bcolors.ENDC}: {entity.fighter.current_time_points} t-pts.")


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
        
        if settings.GOD_MODE:
            self.game_map.visible[:] = True
            self.game_map.explored[:] = True
            return

        if self.player.fighter.is_blind:
            radius = 1
        elif self.game_world.current_floor == 1:
            radius = 90
        else:
            # Efecto "titilar" de la lámpara, farol, linterna.
            radius = max(0, random.randint(0, 1) + self.player.fighter.fov)

            # Aquí intentamos quitar el efecto titilar si
            # la lámpara está apagada.
            # No funciona el if porque no coge o no actualiza
            # el valor de la instancia sino que sólo usa el 
            # por defecto de su clase
            # if self.player.fighter.lamp_on == True:
                #radius = random.randint(0, 1) + self.player.fighter.fov

        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles['transparent'],
            (self.player.x, self.player.y),
            #radius = random.randint(3,5)
            radius,
            algorithm=constants.FOV_SHADOW
        )



        self._apply_campfire_effects()

        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible

        # Esto hace el efecto sombra.
        # Si la super_memory es True, el personaje recuerda lo visto
        # y el mapa se dibuja usando el sistema de "memoria" típico.
        if self.player.fighter.super_memory == False:
            memory_radius = radius + 2
            if self.player.fighter.is_blind:
                memory_radius = radius
            self.game_map.explored[:] = compute_fov(
                self.game_map.tiles['transparent'],
                (self.player.x, self.player.y),
                #radius = random.randint(5,6)
                memory_radius
            )


    def update_fov_alt(self) -> None:

        if settings.GOD_MODE:
            self.game_map.visible[:] = True
            self.game_map.explored[:] = True
            return

        #radius = random.randint(4,5)
        radius = 90

        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles['transparent'],
            (self.player.x, self.player.y),
            #radius = random.randint(3,5)
            radius
        )
        self._apply_campfire_effects()
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

    def _apply_campfire_effects(self) -> None:
        """Make campfires flicker and illuminate nearby tiles if the player has line of sight."""
        gamemap = getattr(self, "game_map", None)
        if not gamemap or not getattr(gamemap, "entities", None):
            return

        campfires = []
        adventurers = []
        for entity in gamemap.entities:
            if not entity:
                continue
            name = getattr(entity, "name", None)
            if not name:
                continue
            if name.lower() == "campfire":
                campfires.append(entity)
            elif name.lower() == "adventurer":
                adventurers.append(entity)
        if not campfires and not adventurers:
            return

        transparent = gamemap.tiles["transparent"]
        los_radius = max(gamemap.width, gamemap.height)
        player_los = compute_fov(
            transparent,
            (self.player.x, self.player.y),
            los_radius,
            algorithm=constants.FOV_SHADOW,
        )

        for campfire in campfires:
            if not player_los[campfire.x, campfire.y]:
                continue

            fighter = getattr(campfire, "fighter", None)
            base_radius = getattr(fighter, "fov", 3) if fighter else 3
            base_radius = max(1, base_radius - 1)
            flicker_offset = random.randint(-1, 1)
            radius = max(1, base_radius + flicker_offset)

            campfire.color = random.choice(self._CAMPFIRE_FLICKER_COLORS)
            campfire.char = self._CAMPFIRE_CHAR

            light_mask = compute_fov(
                transparent,
                (campfire.x, campfire.y),
                radius,
                algorithm=constants.FOV_SHADOW,
            )
            gamemap.visible |= light_mask

        for adventurer in adventurers:
            if not player_los[adventurer.x, adventurer.y]:
                continue
            fighter = getattr(adventurer, "fighter", None)
            if not fighter:
                continue
            base_radius = max(1, getattr(fighter, "fov", 4))
            flicker_offset = random.randint(-1, 1)
            radius = max(1, base_radius + flicker_offset)
            adventurer.color = random.choice(self._ADVENTURER_FLICKER_COLORS)
            light_mask = compute_fov(
                transparent,
                (adventurer.x, adventurer.y),
                radius,
                algorithm=constants.FOV_SHADOW,
            )
            gamemap.visible |= light_mask

    def _tick_campfire(self, campfire: Actor, fighter: components.fighter.Fighter) -> None:
        if fighter.hp <= 0:
            return
        fighter.hp -= 1
        if fighter.hp > 0:
            return
        if self.game_map.visible[campfire.x, campfire.y]:
            self.message_log.add_message("A campfire dies out.", color.status_effect_applied)
        if random.random() < self._CAMPFIRE_SCROLL_CHANCE:
            entity_factories.fireball_scroll.spawn(self.game_map, campfire.x, campfire.y)
        campfire.char = "%"
        campfire.color = (90, 90, 90)
        campfire.name = "Remains of campfire"
        campfire.blocks_movement = False
        campfire.ai = None
        campfire.render_order = RenderOrder.CORPSE


    def autohealmonsters(self):
        self.autoheal_counter += 1
        if self.autoheal_counter == 50:
            
            for obj in set(self.game_map.actors) - {self.player}:
            #for obj in gc.get_objects():
                if isinstance(obj, components.fighter.Fighter):
                    components.fighter.Fighter.autoheal(obj)

            self.player.fighter.autoheal()

            self.autoheal_counter = 0


    #def where_the_hell_the_stairs_are(self):
        #return self.game_map.downstairs_location
    def bugfix_downstairs(self):

        from entity import Decoration
        if not self.game_map.downstairs_location:
            return

        x, y = self.game_map.downstairs_location
        down_exists = False
        for entity in list(self.game_map.entities):
            if entity.x != x or entity.y != y:
                continue

            name = getattr(entity, "name", None)
            if not name:
                continue
            name_lower = name.lower()
            if isinstance(entity, Decoration) and name_lower == "downstairs":
                if down_exists:
                    self.game_map.entities.discard(entity)
                else:
                    down_exists = True
                continue

            if isinstance(entity, Decoration):
                self.game_map.entities.discard(entity)

        if not down_exists:
            stairs = Decoration(
                x=x,
                y=y,
                char='>',
                color=(50,50,40),
                name="Downstairs")
            stairs.spawn(self.game_map, stairs.x, stairs.y)


    def spawn_monsters_upstairs(self):
        
        #print(f"DEBUG: >>>>>>>>>>>>>>>> DOWNSTAIRS_LOCATION: {self.game_map.downstairs_location}")

        self.spawn_monsters_counter = self.spawn_monsters_counter + 1

        dice = random.randint(1, 20)

        total = self.spawn_monsters_counter + dice

        if self.debug == True:
            print("DEGUB: self.spawn_monsters_counter = ", self.spawn_monsters_counter)
            print("DEGUB: Spawn monsters dice (1d20) = ", dice)
            print("DEGUB: Total = ", total)

        if total >= 130:

            spawn_chance = random.randint(1,6)

            if self.debug == True:
                    print(f"DEGUB: spawn chance dice: {spawn_chance}")

            if spawn_chance >= 5:

                amount = random.randint(1, 3)

                if self.debug == True:
                    print(f"DEGUB: New monsters upstairs! ({amount})")

                from entity_factories import monster_roulette, orc, goblin, snake, true_orc
                for i in range(amount):

                    # Generate random monsters upstairs
                    if self.game_world.current_floor <= 4:
                        selected_monster = monster_roulette(choices=[goblin,])
                        selected_monster.spawn(self.game_map, self.game_map.downstairs_location[0], self.game_map.downstairs_location[1])
                    if self.game_world.current_floor > 4:
                        selected_monster = monster_roulette(choices=[orc, goblin, true_orc,])
                        selected_monster.spawn(self.game_map, self.game_map.downstairs_location[0], self.game_map.downstairs_location[1])
                    
                    # Generate single type monster upstairs
                    #entity_factories.goblin.spawn(self.game_map, self.game_map.downstairs_location[0], self.game_map.downstairs_location[1])
            
            self.spawn_monsters_counter = 0


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

    def update_fire(self):
        for entity in set(self.game_map.entities):
            fighter = getattr(entity, "fighter", None)
            if fighter and getattr(fighter, "is_burning", False):
                fighter.update_fire()
            name = getattr(entity, "name", "")
            if name and name.lower() == "campfire" and fighter:
                self._tick_campfire(entity, fighter)


    def update_center_rooms_array(self, room_list):
        self.center_room_array = room_list
    

    def update_melee_indicator(self):
        self.player.fighter.is_in_melee = False
        self.player.fighter.aggravated = False # Para la gestión del stealth attack de los enemigos

        for obj in set(self.game_map.actors) - {self.player}:
            # Lo que tienen en común todos los objetos rompibles
            # que no son enemigos es que tienen la ia_cls "Dummy".
            #if obj.is_alive and obj.name != "Door" and obj.name != "Suspicious wall" and obj.name != "Table" and obj.name != "Campfire":
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
                    end_color = color.red if amount >= 0 else color.status_effect_applied
                    self.message_log.add_message(f"{message_down}", end_color)
                    if attribute == 'base_power':
                        self.player.fighter.base_power -= amount
                    if attribute == 'base_to_hit':
                        self.player.fighter.base_to_hit -= amount
                    if attribute == 'base_stealth':
                        self.player.fighter.base_stealth -= amount
                    if attribute == 'fov':
                        self.player.fighter.fov -= amount
                        if amount < 0:
                            self.player.fighter.is_blind = False

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

        # Fortify indicator
        #if self.player.fighter.can_fortify == True and self.player.fighter.fortified == True:
        if self.player.fighter.fortified == True:
            #render_functions.render_fortify_indicator(console)
            pass


    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)

    def queue_animation(self, frames: List[AnimationFrame]) -> None:
        if frames:
            self._animation_queue.append(frames)

    def play_queued_animations(self, context: Context, console: Console) -> None:
        if not self._animation_queue:
            return
        while self._animation_queue:
            animation = self._animation_queue.pop(0)
            for glyphs, duration in animation:
                console.clear()
                self.render(console)
                self._draw_animation_glyphs(console, glyphs)
                context.present(console)
                delay_ms = max(1, int(max(duration, 0.01) * 1000))
                tcod.sys_sleep_milli(delay_ms)

    def _draw_animation_glyphs(self, console: Console, glyphs: Sequence[AnimationGlyph]) -> None:
        game_map = self.game_map
        for x, y, char, fg in glyphs:
            if not game_map.in_bounds(x, y):
                continue
            if not game_map.visible[x, y]:
                continue
            console.print(x=x, y=y, string=char, fg=fg)
