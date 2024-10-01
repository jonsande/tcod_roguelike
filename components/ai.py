from __future__ import annotations

import random
from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np  # type: ignore
import tcod

from actions import Action, BumpAction, MeleeAction, MovementAction, WaitAction, PassAction
import color

if TYPE_CHECKING:
    from entity import Actor


class BaseAI(Action):


    def perform(self) -> None:
        raise NotImplementedError()

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

        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

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
        self.path_to_stairs = self.get_path_to(self.engine.game_map.downstairs_location[0], self.engine.game_map.downstairs_location[1])


        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        if self.entity.fighter.aggravated == False:

            # Esto para evitar errores en caso de que el STEALTH tenga valor negativo
            if self.engine.player.fighter.stealth < 0:
                engage_rng = random.randint(0, 3) + self.entity.fighter.fov - self.engine.player.fighter.stealth
            else:
                engage_rng = random.randint(0, 3) + self.entity.fighter.fov - self.engine.player.fighter.stealth  # - random.randint(0, self.engine.player.fighter.stealth)
        else:
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov


        if distance > 1 and distance <= engage_rng:

            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
                self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)

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
                self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)
 
            # Si se queda sin estamina:
            if self.entity.fighter.stamina == 0:

                self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
               
                self.path_to_origin = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])
                dest_x, dest_y = self.path_to_origin.pop(0)

                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
                #return WaitAction(self.entity).perform()

            if self.entity.fighter.stamina >= 1:

                if random.randint(1,6) <= 3:

                    self.path_to_origin = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])
                    dest_x, dest_y = self.path_to_origin.pop(0)
                    return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

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
        
        # TO DO: mecánica de ataque siguiloso, con un superbonificador a to hit y a daño, 
        # que haga que la habilidad STEALTH sea más útil
        
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

        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        
        # TO DO: PATROL SYSTEM


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

            # Esto para evitar errores en caso de que el STEALTH tenga valor negativo
            if self.engine.player.fighter.stealth < 0:
                engage_rng = random.randint(1, 3) + self.entity.fighter.fov - self.engine.player.fighter.stealth
            else:
                # engage_rng = 1d3 + fov enemigo - 1d(player stealth)
                engage_rng = random.randint(1, 3) + self.entity.fighter.fov - random.randint(0, self.engine.player.fighter.stealth)
        else:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")
            engage_rng = random.randint(1, 3) + self.entity.fighter.fov
        
        #self.engine.message_log.add_message(f"{self.spawn_point} ---> (0, 0)")
        #self.engine.message_log.add_message(f"{self.entity.x} , {self.entity.y} ---> posición actual")

        if distance > 1 and distance <= engage_rng:
            #self.engine.player.fighter.is_in_melee = False
            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
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
                self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
                return WaitAction(self.entity).perform()
            else:
                return MeleeAction(self.entity, dx, dy).perform()
        
        # TO DO: mecánica de ataque siguiloso, con un superbonificador a to hit y a daño, 
        # que haga que la habilidad STEALTH sea más útil
        
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


class SleepingEnemy(BaseAI):

    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> None:
        
        # Si self.entity se encuentra entre las casillas visibles por el PJ... 
        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            
            sneak_dice = random.randint(1, 6)
            sneak_final = sneak_dice - self.engine.player.fighter.stealth
            #print(f"SNEAK ROLL: {sneak_dice}")
            break_point = 3 + random.randint(0, self.engine.player.fighter.luck)
            
            if sneak_final > break_point:
            #if sneak_final == 666:   # DEBUG
                self.engine.message_log.add_message(
                    f"The {self.entity.name} notices you! ({sneak_final}VS{break_point})",
                    color.orange
                    )
                #woke_ai = HostileEnemy(self.entity)
                woke_ai = self.entity.fighter.woke_ai_cls(self.entity)
                self.entity.ai = woke_ai
                #self.entity.name = self.entity.name + " (!)"
                
            else:
                self.engine.message_log.add_message(
                    f"The {self.entity.name} doesn't notice you (sleeping). ({sneak_final}VS{break_point})"
                    )
                return PassAction(self.entity).perform()
        else:
            return PassAction(self.entity).perform()
     
 
class Neutral(BaseAI): #ToDO: QUE SE VUELVA HOSTIL SI SE LE ATACA

    # Actualmente un personaje con IA "Neutral" camina derecho
    # hacia las escaleras y baja por ellas.

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> None:

        target_x = self.engine.game_map.downstairs_location[0]
        target_y = self.engine.game_map.downstairs_location[1]

        if self.entity.x == target_x and self.entity.y == target_y:
            
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
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()


class SneakeEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.path2: List[Tuple[int, int]] = []
        #self.spawn_point = (self.entity.x, self.entity.y)

    def perform(self) -> None:

        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        self.path = self.get_path_to(target.x, target.y)

        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        if self.entity.fighter.aggravated == False:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")

            # Esto para evitar errores en caso de que el STEALTH tenga valor negativo
            if self.engine.player.fighter.stealth < 0:
                engage_rng = random.randint(0, 1) + self.entity.fighter.fov - self.engine.player.fighter.stealth
            else:
                engage_rng = random.randint(0, 1) + self.entity.fighter.fov - random.randint(0, self.engine.player.fighter.stealth)
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

        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        self.path = self.get_path_to(target.x, target.y)

        # El bonificador de STEALTH sólo se aplica si el monstruo no ha sido provocado nunca:
        if self.entity.fighter.aggravated == False:
            #print(f"{self.entity.name} aggravated: {self.entity.fighter.aggravated}")

            # Esto para evitar errores en caso de que el STEALTH tenga valor negativo
            if self.engine.player.fighter.stealth < 0:
                engage_rng = random.randint(1, 3) + self.entity.fighter.fov - self.engine.player.fighter.stealth
            else:
                engage_rng = random.randint(1, 3) + self.entity.fighter.fov - random.randint(0, self.engine.player.fighter.stealth)
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
                                color.red
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

        target = self.engine.player
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
        pass
        #return WaitAction(self.entity).perform()
