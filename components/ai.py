from __future__ import annotations

import random
from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np  # type: ignore
import tcod
from tcod import constants
from tcod.map import compute_fov
from i18n import _

from actions import Action, BumpAction, MeleeAction, MovementAction, WaitAction, PassAction
import color
import tile_types
import exceptions
import settings
import dialog_settings
from audio import update_campfire_audio

if TYPE_CHECKING:
    from entity import Actor


class BaseAI(Action):

    def perform(self) -> None:
        raise NotImplementedError()

    def on_attacked(self, attacker: "Actor") -> None:
        """Called when another actor performs a melee attack against this entity."""
        fighter = getattr(self.entity, "fighter", None)
        if fighter:
            fighter.aggravated = True

    def _is_adventurer(self, actor: "Actor") -> bool:
        name = getattr(actor, "name", "")
        return bool(name and name.lower() == "adventurer")

    def _potential_targets(self) -> List["Actor"]:
        engine = getattr(self, "engine", None)
        if not engine:
            return []

        targets: List["Actor"] = []
        player = getattr(engine, "player", None)
        if player and player is not self.entity:
            fighter = getattr(player, "fighter", None)
            if fighter and getattr(fighter, "hp", 0) > 0:
                targets.append(player)

        if self._is_adventurer(self.entity):
            return targets

        gamemap = getattr(engine, "game_map", None)
        if not gamemap:
            return targets

        for actor in gamemap.actors:
            if (
                not actor
                or actor is self.entity
                or actor is player
                or not self._is_adventurer(actor)
            ):
                continue
            fighter = getattr(actor, "fighter", None)
            if fighter and getattr(fighter, "hp", 0) > 0:
                targets.append(actor)
        return targets

    def _select_target(self) -> Optional["Actor"]:
        targets = self._potential_targets()
        if not targets:
            return None

        player = getattr(self.engine, "player", None)

        def sort_key(actor: "Actor") -> Tuple[int, int]:
            distance = max(
                abs(actor.x - self.entity.x), abs(actor.y - self.entity.y)
            )
            is_player = 0 if player and actor is player else 1
            return distance, is_player

        return min(targets, key=sort_key)

    def _describe_target(self, target: "Actor") -> str:
        player = getattr(self.engine, "player", None)
        if player and target is player:
            return "you"
        name = getattr(target, "name", "")
        return name or "someone"

    def get_path_to(self, dest_x: int, dest_y: int) -> List[Tuple[int, int]]:
        """Compute and return a path to the target position.

        If there is no valid path then returns an empty list.
        """
        # Copy the walkable array.
        cost = np.array(self.entity.gamemap.tiles["walkable"], dtype=np.int8)

        for entity in self.entity.gamemap.entities:
            # Check that an enitiy blocks movement and the cost isn't zero (blocking.)
            if entity.blocks_movement and cost[entity.x, entity.y]:
                # Add to the cost of a blocked position.
                # A lower number means more enemies will crowd behind each other in
                # hallways.  A higher number means enemies will take longer paths in
                # order to surround the player.
                cost[entity.x, entity.y] += 20

        # Create a graph from the cost array and pass that graph to a new pathfinder.
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.entity.x, self.entity.y))  # Start position.

        # Compute the path to the destination and remove the starting point.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()

        # Convert from List[List[int]] to List[Tuple[int, int]].
        return [(index[0], index[1]) for index in path]
    
class ConfusedEnemy(BaseAI):
    """
    A confused enemy will stumble around aimlessly for a given number of turns, then revert back to its previous AI.
    If an actor occupies a tile it is randomly moving into, it will attack.
    """

    def __init__(
        self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int
    ):
        super().__init__(entity)

        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining

    def perform(self) -> None:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"The {self.entity.name} is no longer confused."
            )
            self.entity.ai = self.previous_ai
        else:
            # Pick a random direction
            direction_x, direction_y = random.choice(
                [
                    (-1, -1),  # Northwest
                    (0, -1),  # North
                    (1, -1),  # Northeast
                    (-1, 0),  # West
                    (1, 0),  # East
                    (-1, 1),  # Southwest
                    (0, 1),  # South
                    (1, 1),  # Southeast
                ]
            )

            self.turns_remaining -= 1

            # The actor will either try to move or attack in the chosen random direction.
            # Its possible the actor will just bump into the wall, wasting a turn.
            return BumpAction(self.entity, direction_x, direction_y,).perform()
        
class SelfConfused(BaseAI):

    def __init__(
        self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int
    ):
        super().__init__(entity)

        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining

    def perform(self) -> None:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"You are no longer confused."
            )
            self.entity.ai = self.previous_ai
        else:
            # Pick a random direction
            direction_x, direction_y = random.choice(
                [
                    (-1, -1),  # Northwest
                    (0, -1),  # North
                    (1, -1),  # Northeast
                    (-1, 0),  # West
                    (1, 0),  # East
                    (-1, 1),  # Southwest
                    (0, 1),  # South
                    (1, 1),  # Southeast
                ]
            )

            self.turns_remaining -= 1

            # The actor will either try to move or attack in the chosen random direction.
            # Its possible the actor will just bump into the wall, wasting a turn.
            return BumpAction(self.entity, direction_x, direction_y,).perform()

class ParalizeEnemy(BaseAI):
    """
    Se paraliza a la criatura.
    """

    def __init__(
        self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int
    ):
        super().__init__(entity)

        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining

    def perform(self) -> None:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"The {self.entity.name} is no longer paralized."
            )
            self.entity.ai = self.previous_ai
        else:
            #self.entity.fighter.effects += 'paralized'
            self.engine.message_log.add_message(
                f"The {self.entity.name} is paralized!"
            )

            self.turns_remaining -= 1

            # The actor will either try to move or attack in the chosen random direction.
            # Its possible the actor will just bump into the wall, wasting a turn.

            # return BumpAction(self.entity, direction_x, direction_y,).perform()
            return WaitAction(self.entity).perform()

wait_counter = 0
class HostileEnemyPlus(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.path2: List[Tuple[int, int]] = []
        #self.spawn_point = (self.entity.x, self.entity.y)

    def perform(self) -> None:

        target = self._select_target()
        if not target:
            return WaitAction(self.entity).perform()
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        if self.engine.game_map.visible[self.entity.x, self.entity.y] == False:
            self_invisible = True
            self_visible = False
        else:
            self_invisible = False
            self_visible = True

        """
        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()

            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()
        
        """
        # Camino hacia el jugador       
        self.path = self.get_path_to(target.x, target.y)
        # Camino hacia la posición de origen
        self.path_to_origin = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])
        # Camino hacia las escaleras
        stairs_location = getattr(self.engine.game_map, "downstairs_location", None)
        if stairs_location:
            self.path_to_stairs = self.get_path_to(stairs_location[0], stairs_location[1])
        else:
            self.path_to_stairs = []


        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        if self.entity.fighter.aggravated == False:

            target_stealth = getattr(target.fighter, "stealth", 0)
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov - target_stealth - random.randint(0, self.entity.fighter.luck)
        else:
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov - random.randint(0, self.entity.fighter.luck)


        if distance > 1 and distance <= engage_rng:

            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)
                else:
                    if settings.DEBUG_MODE:
                        self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)

            # Esta condición es para evitar el error IndexError: pop from empty list
            # que me ha empezado a dar a raíz de implementar las puertas como tiles y
            # como entidades
            if not self.path:
                return WaitAction(self.entity).perform()
            else:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

        # Comportamiento al acercarse al jugador:         
        elif distance == 1:

            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)
                else:
                    if settings.DEBUG_MODE:
                        self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)
 
            # Si se queda sin estamina:
            if self.entity.fighter.stamina == 0:

                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
               
                self.path_to_origin = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])
                dest_x, dest_y = self.path_to_origin.pop(0)

                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
                #return WaitAction(self.entity).perform()

            if self.entity.fighter.stamina >= 1:

                if random.randint(1,6) <= 3:

                    self.path_to_origin = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])

                    try:
                        dest_x, dest_y = self.path_to_origin.pop(0) # BUG: Esto estaba dando error IndexError: pop from empty list
                        return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
                    except IndexError:
                        return MeleeAction(self.entity, dx, dy).perform()

                else:
                    return MeleeAction(self.entity, dx, dy).perform()

            else:
                return MeleeAction(self.entity, dx, dy).perform()
            """    
            elif distance == 2:

                if self.entity.fighter.stamina == 2:

                    if random.randint(1,6) <= 3:

                        self.path_to_origin = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])
                        dest_x, dest_y = self.path_to_origin.pop(0)
                        return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
            """
        
        elif distance > engage_rng:

            #self.engine.message_log.add_message(f"{self.entity.name} te ignora.")

            self.path2 = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])

            """self.path.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar al jugador)"""
            """self.path2.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar la posición
            original en la que fué spawmeada)"""

            if not self.path2:
                return WaitAction(self.entity).perform()
            else:
                # Esto hace que el monstruo, al de x turnos, vuelva a la casilla en la que fue spawmeada

                if self.entity.fighter.wait_counter <= random.randint(1, 4) + self.entity.fighter.aggressivity:
                    self.entity.fighter.wait_counter += 1
                    return WaitAction(self.entity).perform()
                else:
                    self.entity.fighter.wait_counter -= 1
                    dest_x, dest_y = self.path2.pop(0)
                    return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        
            #return WaitAction(self.entity).perform()
        """
        SISTEMA DE DEAMBULAR:
        Se hace con BumpAction, clase de actions.py. BumpAction(self.entity, direction_x, direction_y,).perform()
        Mirar en esta misma página el final de la classe ConfusedEnemy
        """

class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.path2: List[Tuple[int, int]] = []
        #self.spawn_point = (self.entity.x, self.entity.y)

    def perform(self) -> None:

        target = self._select_target()
        if not target:
            return WaitAction(self.entity).perform()
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        if self.engine.game_map.visible[self.entity.x, self.entity.y] == False:
            self_invisible = True
            self_visible = False
        else:
            self_invisible = False
            self_visible = True
        
        # TODO: Patrol system. Un sistema de patrulla sencillo basado en waypoints.

        # ENGAGE SYSTEM (ORIGINAL)
        # Los enemigos persiguen al PJ en busca de melee en
        # cuanto entran en el campo de visión del PJ (del
        # propio PJ, no del suyo)
        """
        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()

            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()
        
        """
                

        # ENGAGE SYSTEM (REVISED)
        # Este sistema es mucho más potente de lo que parece a primera vista.
        # Entre otras cosas permite implementar un sistema de sigilo (y de puntos
        # de experiencia por salvar tiradas al sigilo)
        # El siguiente trozo de código lo que hace, fundamentalmente, es que 
        # los distintos tipos de enemigos puedan tener distinto rango y valor de "detección/provocación",
        # y que ese rango y valores sean independiente del FOV del PJ

        self.path = self.get_path_to(target.x, target.y)
        # Una rata (con un fov=0) y aquí con un randint(1,) a veces abandonará
        # la persecución (con un dandint(0,) es todavaía más probable que abandone
        # la persecución). La regla general: si el engage_rng resultante no es mayor a 1,
        # un enemigo puede abandonar la persecución aun estando en casilla
        # contigua.

        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        if self.entity.fighter.aggravated == False:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")

            # target_stealth = getattr(target.fighter, "stealth", 0)
            # if target_stealth < 0:
            #     stealth_penalty = target_stealth
            # else:
            #     stealth_penalty = random.randint(0, target_stealth)
            # engage_rng = random.randint(1, 3) + self.entity.fighter.fov - stealth_penalty
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov - random.randint(0, self.entity.fighter.luck)

        else:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}") # Debug
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov - random.randint(0, self.entity.fighter.luck)
        
        # Debug
        #self.engine.message_log.add_message(f"{self.spawn_point} ---> (0, 0)")
        #self.engine.message_log.add_message(f"{self.entity.x} , {self.entity.y} ---> posición actual")

        if distance > 1 and distance <= engage_rng:
            #self.engine.player.fighter.is_in_melee = False
            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)
                else:
                    if settings.DEBUG_MODE:
                        self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)

            # Esta condición es para evitar el error IndexError: pop from empty list
            # que me ha empezado a dar a raíz de implementar las puertas como tiles y
            # como entidades
            if not self.path:
                return WaitAction(self.entity).perform()
            else:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()


        elif distance <= 1:

            #self.engine.player.fighter.is_in_melee = True

            if self.entity.fighter.stamina == 0:
                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
                return WaitAction(self.entity).perform()
            else:
                return MeleeAction(self.entity, dx, dy).perform()
        
        elif distance > engage_rng:

            #self.engine.message_log.add_message(f"{self.entity.name} te ignora.")

            self.path2 = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])

            """self.path.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar al jugador)"""
            """self.path2.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar la posición
            original en la que fué spawmeada)"""

            if not self.path2:
                return WaitAction(self.entity).perform()
            else:
                # Esto hace que el monstruo, al de x turnos, vuelva a la casilla en la que fue spawmeada

                if self.entity.fighter.wait_counter <= random.randint(1, 4) + self.entity.fighter.aggressivity:
                    self.entity.fighter.wait_counter += 1
                    return WaitAction(self.entity).perform()
                else:
                    self.entity.fighter.wait_counter -= 1
                    dest_x, dest_y = self.path2.pop(0)
                    return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        
            #return WaitAction(self.entity).perform()

        """
        SISTEMA DE DEAMBULAR:
        Se hace con BumpAction, clase de actions.py. BumpAction(self.entity, direction_x, direction_y,).perform()
        Mirar en esta misma página el final de la classe ConfusedEnemy
        """

class HostileEnemyV2(BaseAI):

    _NEIGHBOR_DELTAS = [
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    ]

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.path2: List[Tuple[int, int]] = []
        #self.spawn_point = (self.entity.x, self.entity.y)
        self._wander_cooldown = self._roll_wander_delay()
        self._aggressor: Optional[Actor] = None
        self._lost_sight_counter: Optional[int] = None

    def _wander_idle(self) -> None:
        if self._wander_cooldown > 0:
            self._wander_cooldown -= 1
            return WaitAction(self.entity).perform()

        gamemap = self.engine.game_map
        directions = list(self._NEIGHBOR_DELTAS)
        random.shuffle(directions)
        for dx, dy in directions:
            nx = self.entity.x + dx
            ny = self.entity.y + dy
            if not gamemap.in_bounds(nx, ny):
                continue
            if not gamemap.tiles["walkable"][nx, ny]:
                continue
            if gamemap.get_blocking_entity_at_location(nx, ny):
                continue
            try:
                MovementAction(self.entity, dx, dy).perform()
                self._wander_cooldown = self._roll_wander_delay()
                return
            except exceptions.Impossible:
                continue

        self._wander_cooldown = self._roll_wander_delay()
        WaitAction(self.entity).perform()

    def _roll_wander_delay(self) -> int:
        return random.randint(1, 6)

    def _is_valid_aggressor(self, actor: Optional[Actor]) -> bool:
        if not actor:
            return False
        fighter = getattr(actor, "fighter", None)
        if not fighter or getattr(fighter, "hp", 0) <= 0:
            return False
        return getattr(actor, "gamemap", None) is self.engine.game_map

    def _can_see_actor(self, actor: Actor) -> bool:
        fighter = getattr(self.entity, "fighter", None)
        if not fighter:
            return False
        radius = max(0, fighter.fov)
        if radius <= 0:
            return actor.x == self.entity.x and actor.y == self.entity.y
        gamemap = self.engine.game_map
        try:
            transparent = gamemap.get_transparency_map()
        except AttributeError:
            transparent = gamemap.tiles["transparent"]
        visible = compute_fov(
            transparent,
            (self.entity.x, self.entity.y),
            radius,
            algorithm=constants.FOV_SHADOW,
        )
        if not gamemap.in_bounds(actor.x, actor.y):
            return False
        return bool(visible[actor.x, actor.y])

    def perform(self) -> None:

        target = self._select_target()
        if not target:
            #return WaitAction(self.entity).perform()
            return self._wander_idle()
        
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        if self.engine.game_map.visible[self.entity.x, self.entity.y] == False:
            self_invisible = True
            self_visible = False
        else:
            self_invisible = False
            self_visible = True
        
        # TODO: Patrol system. Un sistema de patrulla sencillo basado en waypoints.

        # ENGAGE SYSTEM (ORIGINAL)
        # Los enemigos persiguen al PJ en busca de melee en
        # cuanto entran en el campo de visión del PJ (del
        # propio PJ, no del suyo)
        """
        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()

            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()
        
        """

        # ENGAGE SYSTEM (REVISED)
        # Este sistema es mucho más potente de lo que parece a primera vista.
        # Entre otras cosas permite implementar un sistema de sigilo (y de puntos
        # de experiencia por salvar tiradas al sigilo)
        # El siguiente trozo de código lo que hace, fundamentalmente, es que 
        # los distintos tipos de enemigos puedan tener distinto rango y valor de "detección/provocación",
        # y que ese rango y valores sean independiente del FOV del PJ

        self.path = self.get_path_to(target.x, target.y)
        # Una rata (con un fov=0) y aquí con un randint(1,) a veces abandonará
        # la persecución (con un dandint(0,) es todavaía más probable que abandone
        # la persecución). La regla general: si el engage_rng resultante no es mayor a 1,
        # un enemigo puede abandonar la persecución aun estando en casilla
        # contigua.

        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        target_stealth = getattr(target.fighter, "stealth", 0)
        target_luck = getattr(target.fighter, "luck", 0)
        if self.entity.fighter.aggravated == False:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")
            # if target_stealth < 0:
            #     stealth_penalty = target_stealth
            # else:
            #     stealth_penalty = random.randint(0, target_stealth)
            # engage_rng = random.randint(1, 3) + self.entity.fighter.fov - stealth_penalty
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov - target_stealth - random.randint(0, target_luck)

        else:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}") # Debug
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov - random.randint(0, target_luck)
        
        # Debug
        #self.engine.message_log.add_message(f"{self.spawn_point} ---> (0, 0)")
        #self.engine.message_log.add_message(f"{self.entity.x} , {self.entity.y} ---> posición actual")

        if distance > 1 and distance <= engage_rng:
            #self.engine.player.fighter.is_in_melee = False
            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)
                else:
                    if settings.DEBUG_MODE:
                        self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)

            # Esta condición es para evitar el error IndexError: pop from empty list
            # que me ha empezado a dar a raíz de implementar las puertas como tiles y
            # como entidades
            if not self.path:
                return self._wander_idle()
                #return WaitAction(self.entity).perform()
            else:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()


        elif distance <= 1:

            if self.entity.fighter.aggravated == False:
                # TODO: Comprobar si este cambio del aggravated es correcto. ¿Está siendo agraviado antes
                # de recibir el ataque por sorpresa?
                self.entity.fighter.aggravated = True
                return WaitAction(self.entity).perform()
            else:
                if self.entity.fighter.stamina == 0:
                    if self_visible:
                        self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
                    return WaitAction(self.entity).perform()
                else:
                    return MeleeAction(self.entity, dx, dy).perform()
        
        elif distance > engage_rng:

            # TODO: Creo que aquí es donde podemos mejorar el rendimiento del juego.

            #self.engine.message_log.add_message(f"{self.entity.name} te ignora.")

            self.path2 = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])

            """self.path.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar al jugador)"""
            """self.path2.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar la posición
            original en la que fué spawmeada)"""

            if not self.path2:

                #return WaitAction(self.entity).perform()
                return self._wander_idle()
            
            else:
                # Esto hace que el monstruo, al de x turnos, vuelva a la casilla en la que fue spawmeada

                if self.entity.fighter.wait_counter <= random.randint(1, 4) + self.entity.fighter.aggressivity:
                    self.entity.fighter.wait_counter += 1
                    return WaitAction(self.entity).perform()
                else:
                    self.entity.fighter.wait_counter -= 1
                    dest_x, dest_y = self.path2.pop(0)
                    return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        
            #return WaitAction(self.entity).perform()


        """
        SISTEMA DE DEAMBULAR:
        Se hace con BumpAction, clase de actions.py. BumpAction(self.entity, direction_x, direction_y,).perform()
        Mirar en esta misma página el final de la classe ConfusedEnemy
        """

class SleepingEnemy(BaseAI):

    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> None:

        target = self._select_target()
        if not target:
            return PassAction(self.entity).perform()
        target_fighter = getattr(target, "fighter", None)
        if not target_fighter:
            return PassAction(self.entity).perform()

        target_luck = getattr(target_fighter, "luck", 0)
        sleeping_dice = random.randint(2,12) - target_luck

        if sleeping_dice > 10:
            woke_ai = self.entity.fighter.woke_ai_cls(self.entity)
            self.entity.ai = woke_ai
            # Si self.entity se encuentra entre las casillas visibles por el PJ... 
            if self.engine.game_map.visible[self.entity.x, self.entity.y]:
                self.engine.message_log.add_message(
                    f"The {self.entity.name} wakes up.",
                    color.orange
                    )
                
        else:
            # Si self.entity se encuentra entre las casillas visibles por el PJ... 
            if self.engine.game_map.visible[self.entity.x, self.entity.y]:
                
                sneak_dice = random.randint(1, 6)
                sneak_final = sneak_dice - getattr(target_fighter, "stealth", 0)
                target_luck_bonus = (
                    random.randint(0, target_luck) if target_luck > 0 else 0
                )
                break_point = 3 + target_luck_bonus
                
                if sneak_final > break_point:
                #if sneak_final == 666:   # DEBUG
                    target_desc = self._describe_target(target)
                    self.engine.message_log.add_message(
                        f"The {self.entity.name} notices {target_desc}! ({sneak_final}VS{break_point})",
                        color.orange
                        )
                    #woke_ai = HostileEnemy(self.entity)
                    woke_ai = self.entity.fighter.woke_ai_cls(self.entity)
                    self.entity.ai = woke_ai
                    #self.entity.name = self.entity.name + " (!)"
                    
                else:
                    target_desc = self._describe_target(target)
                    self.engine.message_log.add_message(
                        f"The {self.entity.name} doesn't notice {target_desc} (sleeping). ({sneak_final}VS{break_point})"
                        )
                    return PassAction(self.entity).perform()
            else:
                return PassAction(self.entity).perform()
     
class Neutral(BaseAI):

    # Actualmente un personaje con IA "Neutral" camina derecho
    # hacia las escaleras y baja por ellas.

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self._last_hp: Optional[int] = None

    def perform(self) -> None:

        current_hp = self.entity.fighter.hp

        if self._last_hp is None:
            self._last_hp = current_hp

        if current_hp < self._last_hp or self.entity.fighter.aggravated:
            self.entity.fighter.aggravated = True
            woke_ai = self.entity.fighter.woke_ai_cls(self.entity)
            self.entity.ai = woke_ai
            return woke_ai.perform()

        target_x = self.engine.game_map.downstairs_location[0]
        target_y = self.engine.game_map.downstairs_location[1]

        if self.entity.x == target_x and self.entity.y == target_y:
            self._last_hp = current_hp
            return self.entity.fighter.desintegrate()

        #dx = target_x - self.entity.x
        #dy = target_y - self.entity.y
        #distance = max(abs(dx), abs(dy))  # Chebyshev distance.
        #if self.engine.game_map.visible[self.entity.x, self.entity.y]:
        #    if distance <= 1:
        #        pass

        self.path = self.get_path_to(target_x, target_y)

        #else:
        #    while self.engine.game_map.visible[self.entity.x, self.entity.y] == False:
        #        self.search_and_destroy()

        if self.path:
            # Aquí se elimina del path la casilla que se acaba de ocupar...
            dest_x, dest_y = self.path.pop(0)
            # ...y se avanza a la siguiente casilla del path.
            self._last_hp = current_hp
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()

        self._last_hp = current_hp
        return WaitAction(self.entity).perform()

class AdventurerAI(BaseAI):
    """Adventurers wander between rooms, rest when exhausted, stay neutral unless provoked,
    take stairs, enjoy campfires and sometimes talk."""

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.target: Optional[Tuple[int, int]] = None
        self.current_room: Optional[Tuple[int, int]] = None
        self.room_centers: List[Tuple[int, int]] = []
        self.stalled_turns: int = 0
        self.waiting_campfire = None
        self._player_contact = False
        self._combat_path: List[Tuple[int, int]] = []
        self._combat_target: Optional[Tuple[int, int]] = None
        self._aggressor: Optional[Actor] = None
        self._relevant_greetings_remaining: int = getattr(
            dialog_settings, "ADVENTURER_MAX_RELEVANT_GREETING_MESSAGES", 2
        )

    def perform(self) -> None:
        if getattr(self.entity.fighter, "stamina", 1) <= 0:
            return WaitAction(self.entity).perform()

        if getattr(self.entity.fighter, "aggravated", False):
            return self._pursue_enemy()

        centers = getattr(self.engine, "center_room_array", None) or []
        if centers and not self.room_centers:
            self.room_centers = [tuple(c) for c in centers if c]
            self.current_room = self._nearest_room_center()

        if self._check_campfire_pause():
            self._handle_player_contact()
            return WaitAction(self.entity).perform()

        if self._stairs_visible():
            stairs = self.engine.game_map.downstairs_location
            if stairs:
                self.target = stairs
                self.path = self._build_path(stairs)
        elif not self.room_centers:
            self._handle_player_contact()
            return self._wander()
        elif self.target is None or self.target == self.current_room:
            self._select_new_room()

        stairs = self.engine.game_map.downstairs_location
        if stairs and (self.entity.x, self.entity.y) == stairs:
            return self.entity.fighter.desintegrate()

        if not self.path and self.target:
            self.path = self._build_path(self.target)
            if not self.path:
                self.target = None
                self._handle_player_contact()
                return self._wander()

        if not self.path:
            self._handle_player_contact()
            return self._wander()

        dest_x, dest_y = self.path[0]
        if (dest_x, dest_y) == (self.entity.x, self.entity.y):
            self.path.pop(0)
            self.stalled_turns = 0
            if not self.path:
                self.current_room = self.target
                self.target = None
            self._handle_player_contact()
            return

        dx = dest_x - self.entity.x
        dy = dest_y - self.entity.y
        blocking_actor = self.engine.game_map.get_actor_at_location(dest_x, dest_y)
        if blocking_actor:
            if blocking_actor is self.engine.player and not getattr(
                self.entity.fighter, "aggravated", False
            ):
                self.path = []
                self.target = None
                self._handle_player_contact()
                return WaitAction(self.entity).perform()

        prev_pos = (self.entity.x, self.entity.y)
        try:
            BumpAction(self.entity, dx, dy).perform()
        except exceptions.Impossible:
            self._handle_stall()
            self._handle_player_contact()
            return

        if (self.entity.x, self.entity.y) == (dest_x, dest_y):
            self.path.pop(0)
            self.stalled_turns = 0
            if not self.path:
                self.current_room = self.target
                self.target = None
        elif (self.entity.x, self.entity.y) == prev_pos:
            self._handle_stall()
        else:
            self.stalled_turns = 0
        self._handle_player_contact()

    def _handle_stall(self) -> None:
        if getattr(self.entity.fighter, "aggravated", False):
            self.path = []
            self.stalled_turns = 0
            self._combat_path = []
            self._combat_target = None
            return
        self.stalled_turns += 1
        if self.stalled_turns >= 2:
            self.target = None
            self.path = []
            self.stalled_turns = 0

    def _select_new_room(self) -> None:
        options = [room for room in self.room_centers if room != self.current_room]
        if not options:
            self.target = None
            return
        self.target = random.choice(options)
        self.path = []
        self.stalled_turns = 0

    def _nearest_room_center(self) -> Optional[Tuple[int, int]]:
        if not self.room_centers:
            return None
        best = min(
            self.room_centers,
            key=lambda c: abs(c[0] - self.entity.x) + abs(c[1] - self.entity.y),
        )
        return best

    def _build_path(self, destination: Tuple[int, int]) -> List[Tuple[int, int]]:
        gm = self.engine.game_map
        dest_x, dest_y = destination
        if not gm.in_bounds(dest_x, dest_y):
            return []

        cost = np.array(gm.tiles["walkable"], dtype=np.int8)
        cost = np.where(cost, 1, 0).astype(np.int16)
        door_mask = gm.tiles["dark"]["ch"] == tile_types.closed_door["dark"]["ch"]
        cost[door_mask] = 1

        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)
        pathfinder.add_root((self.entity.x, self.entity.y))
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()
        return [(step[0], step[1]) for step in path]

    def _wander(self) -> None:
        directions = [
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        ]
        random.shuffle(directions)
        for dx, dy in directions:
            nx = self.entity.x + dx
            ny = self.entity.y + dy
            if not self.engine.game_map.in_bounds(nx, ny):
                continue
            try:
                BumpAction(self.entity, dx, dy).perform()
                return
            except exceptions.Impossible:
                continue
        WaitAction(self.entity).perform()

    def _pursue_enemy(self) -> None:
        target_actor = self._resolve_aggressor()
        if not target_actor:
            self.entity.fighter.aggravated = False
            self._aggressor = None
            self._combat_path = []
            self._combat_target = None
            self._handle_player_contact()
            return WaitAction(self.entity).perform()

        destination = (target_actor.x, target_actor.y)
        if self._combat_target != destination or not self._combat_path:
            self._combat_target = destination
            self._combat_path = self._build_path(destination)
        if not self._combat_path:
            self._handle_player_contact()
            return self._wander()
        dest_x, dest_y = self._combat_path[0]
        if (dest_x, dest_y) == (self.entity.x, self.entity.y):
            self._combat_path.pop(0)
            return
        dx = dest_x - self.entity.x
        dy = dest_y - self.entity.y
        prev_pos = (self.entity.x, self.entity.y)
        try:
            BumpAction(self.entity, dx, dy).perform()
        except exceptions.Impossible:
            self._combat_path = []
            return
        if (self.entity.x, self.entity.y) == (dest_x, dest_y):
            self._combat_path.pop(0)
        elif (self.entity.x, self.entity.y) == prev_pos:
            self._combat_path = []

    def _stairs_visible(self) -> bool:
        gamemap = self.engine.game_map
        stairs = gamemap.downstairs_location
        if not stairs:
            return False
        radius = getattr(self.entity.fighter, "fov", 0)
        if radius <= 0:
            return False
        visible = compute_fov(
            gamemap.tiles["transparent"],
            (self.entity.x, self.entity.y),
            radius,
            algorithm=constants.FOV_SHADOW,
        )
        x, y = stairs
        return bool(visible[x, y])

    def _check_campfire_pause(self) -> bool:
        if self.waiting_campfire:
            fighter = getattr(self.waiting_campfire, "fighter", None)
            if (
                fighter
                and getattr(fighter, "hp", 0) > 0
                and self._is_adjacent_to(self.waiting_campfire)
            ):
                return True
            self.waiting_campfire = None

        campfire = self._adjacent_campfire()
        if campfire:
            fighter = getattr(campfire, "fighter", None)
            if fighter and getattr(fighter, "hp", 0) > 0:
                self.waiting_campfire = campfire
                return True
        return False

    def _adjacent_campfire(self):
        gamemap = self.engine.game_map
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                actor = gamemap.get_actor_at_location(self.entity.x + dx, self.entity.y + dy)
                if actor and getattr(actor, "name", "").lower() == "campfire":
                    return actor
        return None

    def _is_adjacent_to(self, entity: Actor) -> bool:
        return max(abs(entity.x - self.entity.x), abs(entity.y - self.entity.y)) <= 1

    def _next_greeting_message(self) -> Optional[str]:
        relevant = getattr(dialog_settings, "ADVENTURER_GREETING_MESSAGES", [])
        irrelevant = getattr(
            dialog_settings, "ADVENTURER_IRRELEVANT_GREETING_MESSAGES", []
        )

        if self._relevant_greetings_remaining > 0 and relevant:
            self._relevant_greetings_remaining -= 1
            return random.choice(relevant)

        if irrelevant:
            return random.choice(irrelevant)

        if relevant:
            return random.choice(relevant)

        return None

    def _handle_player_contact(self) -> None:
        if getattr(self.entity.fighter, "aggravated", False):
            self._player_contact = False
            return
        player = self.engine.player
        adjacent = max(abs(player.x - self.entity.x), abs(player.y - self.entity.y)) == 1
        if adjacent and not self._player_contact:
            gm = self.engine.game_map
            if gm.visible[self.entity.x, self.entity.y]:
                message = self._next_greeting_message()
                if message:
                    self.engine.message_log.add_message(message)
            self._player_contact = True
        elif not adjacent:
            self._player_contact = False

    def _check_campfire_pause(self) -> bool:
        if self.waiting_campfire:
            fighter = getattr(self.waiting_campfire, "fighter", None)
            if (
                fighter
                and getattr(fighter, "hp", 0) > 0
                and self._is_adjacent_to(self.waiting_campfire)
            ):
                return True
            self.waiting_campfire = None

        campfire = self._adjacent_campfire()
        if campfire:
            fighter = getattr(campfire, "fighter", None)
            if fighter and getattr(fighter, "hp", 0) > 0:
                self.waiting_campfire = campfire
                return True
        return False

    def _adjacent_campfire(self):
        gamemap = self.engine.game_map
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                x = self.entity.x + dx
                y = self.entity.y + dy
                actor = gamemap.get_actor_at_location(x, y)
                if actor and getattr(actor, "name", "").lower() == "campfire":
                    return actor
        return None

    def _is_adjacent_to(self, entity: Actor) -> bool:
        return (
            abs(entity.x - self.entity.x) <= 1 and abs(entity.y - self.entity.y) <= 1
        )

    def _resolve_aggressor(self) -> Optional[Actor]:
        if self._is_valid_enemy(self._aggressor):
            return self._aggressor
        return None

    def _is_valid_enemy(self, actor: Optional[Actor]) -> bool:
        if not actor:
            return False
        fighter = getattr(actor, "fighter", None)
        if not fighter or getattr(fighter, "hp", 0) <= 0:
            return False
        if getattr(actor, "gamemap", None) is not self.engine.game_map:
            return False
        return True

    def on_attacked(self, attacker: Actor) -> None:
        super().on_attacked(attacker)
        if not attacker:
            return
        if getattr(attacker, "gamemap", None) is not self.engine.game_map:
            return
        self._aggressor = attacker
        self._combat_path = []
        self._combat_target = None
        self.waiting_campfire = None
        self._player_contact = False

class SneakeEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.path2: List[Tuple[int, int]] = []
        #self.spawn_point = (self.entity.x, self.entity.y)

    def perform(self) -> None:

        target = self._select_target()
        if not target:
            return WaitAction(self.entity).perform()
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        self.path = self.get_path_to(target.x, target.y)

        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        if self.entity.fighter.aggravated == False:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")

            # Esto para evitar errores en caso de que el STEALTH tenga valor negativo
            target_stealth = getattr(target.fighter, "stealth", 0)
            if target_stealth < 0:
                stealth_penalty = target_stealth
            else:
                stealth_penalty = random.randint(0, target_stealth)
            engage_rng = random.randint(0, 1) + self.entity.fighter.fov - stealth_penalty
        else:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")
            engage_rng = 1 + self.entity.fighter.fov
        
        #self.engine.message_log.add_message(f"{self.spawn_point} ---> (0, 0)")
        #self.engine.message_log.add_message(f"{self.entity.x} , {self.entity.y} ---> posición actual")

        if distance > 1 and distance <= engage_rng:

            self.entity.fighter.aggravated = True
            #self.engine.message_log.add_message(f"¡Has provocado a {self.entity.name}!")

            if not self.path:
                return WaitAction(self.entity).perform()
            else:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()


        elif distance <= 1:

            if self.entity.fighter.stamina == 0:
                self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
                return WaitAction(self.entity).perform()
            else:
                return MeleeAction(self.entity, dx, dy).perform()
        
        elif distance > engage_rng:

            self.path2 = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])

            if not self.path2:
                return WaitAction(self.entity).perform()
            else:
                # Esto hace que el monstruo, al de x turnos, vuelva a la casilla en la que fue spawmeada

                if self.entity.fighter.wait_counter <= random.randint(1, 4) + self.entity.fighter.aggressivity:
                    self.entity.fighter.wait_counter += 1
                    return WaitAction(self.entity).perform()
                else:
                    self.entity.fighter.wait_counter -= 1
                    dest_x, dest_y = self.path2.pop(0)
                    return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

class Scout(BaseAI): # WORK IN PROGRESS
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.path2: List[Tuple[int, int]] = []
        #self.spawn_point = (self.entity.x, self.entity.y)
        self.checkpoint = []

    def perform(self) -> None:

        target = self._select_target()
        if not target:
            return WaitAction(self.entity).perform()
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        self.path = self.get_path_to(target.x, target.y)

        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        if self.entity.fighter.aggravated == False:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")

            # Esto para evitar errores en caso de que el STEALTH tenga valor negativo
            target_stealth = getattr(target.fighter, "stealth", 0)
            if target_stealth < 0:
                stealth_penalty = target_stealth
            else:
                stealth_penalty = random.randint(0, target_stealth)
            engage_rng = random.randint(1, 3) + self.entity.fighter.fov - stealth_penalty
        else:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")
            engage_rng = random.randint(1, 3) + self.entity.fighter.fov
        
        #self.engine.message_log.add_message(f"{self.spawn_point} ---> (0, 0)")
        #self.engine.message_log.add_message(f"{self.entity.x} , {self.entity.y} ---> posición actual")

        if distance > 1 and distance <= engage_rng:

            self.entity.fighter.aggravated = True

            if not self.path:
                return WaitAction(self.entity).perform()
            else:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

        elif distance <= 1:

            if self.entity.fighter.stamina == 0:
                self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
                return WaitAction(self.entity).perform()
            else:
                return MeleeAction(self.entity, dx, dy).perform()
        
        # SCOUTING MECHANICS
        elif distance > engage_rng:
            
            if self.checkpoint:
                dest_x, dest_y = self.checkpoint
                #print(f"DESTINO ACTUAL DEL SCOUT: {dest_x},{dest_y}") # DEBUGG
                self.path2 = self.get_path_to(dest_x, dest_y) # Returns array of cells to checkpoint
                
                if self.entity.x == dest_x and self.entity.y == dest_y:
                    #self.checkpoint = []
                    try:
                        self.checkpoint = self.engine.center_room_array.pop(0) # Esto estaba dando un error IndexError
                        return WaitAction(self.entity).perform()
                    except IndexError:
                        #print(f"[DEBUG] Error excepton -- IndexError: pop from empty list\nGoblin location: {self.checkpoint}")
                        WaitAction(self.entity).perform()
                else:
                    if self.path2:
                        to_x, to_y = self.path2.pop(0)
                        
                        #if distance > self.engine.player.fighter.fov + 2 and distance < self.engine.player.fighter.fov +15:
                        if distance > 6 + 2 and distance < 6 + 9:
                            #self.engine.game_map.visible
                            self.engine.message_log.add_message(
                                f"You hear footsteps!",
                                color.orange
                                )
                            
                        return MovementAction(self.entity, to_x - self.entity.x, to_y - self.entity.y).perform()
                    else:
                        return WaitAction(self.entity).perform()                   
            else:
                try:
                    self.checkpoint = self.engine.center_room_array.pop(0)
                    return WaitAction(self.entity).perform()
                except IndexError:
                    #print("IndexError: pop from empty list")
                    WaitAction(self.entity).perform()
                    
class SentinelEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)

        #self.spawn_point = (self.entity.x, self.entity.y)

    def perform(self) -> None:

        target = self._select_target()
        if not target:
            return WaitAction(self.entity).perform()
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        if distance <= 1:

            if self.entity.fighter.stamina == 0:
                self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
                return WaitAction(self.entity).perform()
            else:
                return MeleeAction(self.entity, dx, dy).perform()
        else:
            return WaitAction(self.entity).perform()

# Objetos rompibles, como mesas:
from entity import Obstacle
class Dummy(BaseAI):

    def __init__(self, entity: Obstacle):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> None:
        
        if self.entity.name == "Campfire":

            player = self.engine.player
            campfire = self.entity
            dx = player.x - campfire.x
            dy = player.y - campfire.y
            distance = max(abs(dx), abs(dy))  # Chebyshev distance.

            is_adjacent = distance <= 1
            update_campfire_audio(self.entity, is_adjacent)

            if is_adjacent:
                player.fighter.heal(1)
                if player.fighter.hp < player.fighter.max_hp:
                    self.engine.message_log.add_message(
                        f"You restore 1 HP.",
                        color.health_recovered
                    )

            #if self.engine.game_map.visible[campfire.x, campfire.y]:


class OldManAI(BaseAI):

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self._player_contact = False
        self._messages_delivered = 0
        max_messages = getattr(dialog_settings, "OLD_MAN_MAX_DIALOG_MESSAGES", 2)
        try:
            self._max_messages = max(0, int(max_messages))
        except (TypeError, ValueError):
            self._max_messages = 2
        self._repeat_message = getattr(
            dialog_settings,
            "OLD_MAN_REPEAT_MESSAGE",
            "Está escrito en el templo: «...e incontables niños retornarán a la noche primigenia.»",
        )

    def perform(self) -> None:
        self._handle_player_contact()
        return WaitAction(self.entity).perform()

    def _handle_player_contact(self) -> None:
        engine = getattr(self, "engine", None)
        if not engine:
            return
        player = getattr(engine, "player", None)
        gamemap = getattr(engine, "game_map", None)
        if not player or not gamemap:
            self._player_contact = False
            return

        adjacent = max(abs(player.x - self.entity.x), abs(player.y - self.entity.y)) <= 1
        if not adjacent:
            self._player_contact = False
            return

        if self._player_contact:
            return

        if not gamemap.visible[self.entity.x, self.entity.y]:
            return

        self._speak()
        self._player_contact = True

    def _speak(self) -> None:
        engine = getattr(self, "engine", None)
        if not engine:
            return
        message = self._next_message()
        if not message:
            return
        engine.message_log.add_message(message)

    def _next_message(self) -> Optional[str]:
        if self._messages_delivered >= self._max_messages:
            return self._repeat_message

        messages = getattr(dialog_settings, "OLD_MAN_DIALOG_MESSAGES", [])
        if not messages:
            return self._repeat_message

        self._messages_delivered += 1
        return random.choice(messages)

    def on_player_bump(self) -> None:
        self._speak()
        self._player_contact = True
