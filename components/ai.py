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

    def __init__(self, entity: Actor) -> None:
        super().__init__(entity)
        # Cache de rutas por destino: (dest_x, dest_y) -> (turno_calculado, path).
        # Se usa para no recalcular A* cada turno si el objetivo no cambia y
        # el siguiente paso sigue libre.
        self._path_cache: dict[Tuple[int, int], Tuple[int, List[Tuple[int, int]]]] = {}
        # Contadores de persecución: pérdida de contacto y fallos de ruta.
        self._agro_lost_turns: int = 0
        self._path_failure_streak: int = 0

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
            hidden = getattr(fighter, "is_hidden", False)
            # Si el sigilo está desactivado, ignoramos el flag is_hidden para la selección de objetivos.
            if getattr(settings, "STEALTH_DISABLED", False):
                hidden = False
            if fighter and getattr(fighter, "hp", 0) > 0 and not hidden:
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
            hidden = getattr(fighter, "is_hidden", False)
            if getattr(settings, "STEALTH_DISABLED", False):
                hidden = False
            if fighter and getattr(fighter, "hp", 0) > 0 and not hidden:
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

    def _sound_transparency_map(self, gamemap) -> np.ndarray:
        """Mapa de transparencia para sonido: muros/puertas atenúan pero no bloquean del todo."""
        try:
            base = gamemap.get_transparency_map()
        except AttributeError:
            base = gamemap.tiles["transparent"]
        sound_map = base.astype(float)
        wall_opacity = 0.8  # Muros dejan pasar algo de sonido.
        sound_map = np.where(sound_map, sound_map, wall_opacity)
        try:
            closed_ch = tile_types.closed_door["dark"]["ch"]
            door_mask = gamemap.tiles["dark"]["ch"] == closed_ch
            sound_map[door_mask] = 0.5  # Las puertas cierran menos el sonido que un muro.
        except Exception:
            pass
        return sound_map

    def _can_hear_position(self, x: int, y: int, radius: int) -> bool:
        """Devuelve True si (x, y) es audible para la criatura con el FOH dado."""
        gamemap = self.entity.gamemap
        if not gamemap.in_bounds(x, y):
            return False
        sound_map = self._sound_transparency_map(gamemap)
        audible = compute_fov(
            sound_map,
            (self.entity.x, self.entity.y),
            radius,
            algorithm=constants.FOV_SHADOW,
        )
        return bool(audible[x, y])

    def _neighbor_positions(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Vecinos en 8 direcciones para caminatas cortas."""
        return [
            (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
            (x - 1, y),                 (x + 1, y),
            (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
        ]

    def _is_walkable_for_ai(
        self,
        x: int,
        y: int,
        *,
        can_pass_closed_doors: bool,
        can_open_doors: bool,
    ) -> bool:
        """Comprueba si la casilla es transitable para la IA (muros, puertas, bloqueos)."""
        gamemap = self.entity.gamemap
        if not gamemap.in_bounds(x, y):
            return False
        if can_pass_closed_doors or can_open_doors:
            closed_ch = tile_types.closed_door["dark"]["ch"]
            if gamemap.tiles["dark"]["ch"][x, y] == closed_ch:
                # Trata puertas cerradas como transitables para criaturas que pueden abrirlas/atravesarlas.
                return True
        if not gamemap.tiles["walkable"][x, y]:
            return False
        blocker = gamemap.get_blocking_entity_at_location(x, y)
        if blocker and blocker is not self.entity:
            # Puertas cuentan como bloqueadores si no pueden abrirlas; el resto siempre bloquea.
            if can_pass_closed_doors or can_open_doors:
                if getattr(getattr(blocker, "name", ""), "lower", lambda: "")() == "door":
                    return True
            return False
        return True

    def _bfs_path_limited(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        *,
        max_radius: int,
        can_pass_closed_doors: bool,
        can_open_doors: bool,
    ) -> List[Tuple[int, int]]:
        """BFS barato en radio acotado; devuelve ruta desde start a goal o []."""
        from collections import deque

        sx, sy = start
        gx, gy = goal
        # Chebyshev distance como heurística rápida para abortar fuera de radio.
        if max(abs(gx - sx), abs(gy - sy)) > max_radius:
            return []

        queue: deque[Tuple[int, int]] = deque()
        queue.append((sx, sy))
        came_from: dict[Tuple[int, int], Optional[Tuple[int, int]]] = {(sx, sy): None}

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == (gx, gy):
                break
            for nx, ny in self._neighbor_positions(cx, cy):
                if (nx, ny) in came_from:
                    continue
                if not self._is_walkable_for_ai(
                    nx,
                    ny,
                    can_pass_closed_doors=can_pass_closed_doors,
                    can_open_doors=can_open_doors,
                ):
                    continue
                # Limitar expansión al radio indicado.
                if max(abs(nx - sx), abs(ny - sy)) > max_radius:
                    continue
                came_from[(nx, ny)] = (cx, cy)
                queue.append((nx, ny))

        if (gx, gy) not in came_from:
            return []

        # Reconstruir ruta desde goal hacia start (excluyendo origen).
        path_rev: List[Tuple[int, int]] = []
        current = (gx, gy)
        while current and current in came_from:
            prev = came_from[current]
            if prev is None:
                break
            path_rev.append(current)
            current = prev
        path_rev.reverse()
        return path_rev

    def get_path_to(self, dest_x: int, dest_y: int, *, ignore_senses: bool = False) -> List[Tuple[int, int]]:
        """Compute and return a path to the target position.

        If there is no valid path then returns an empty list.
        """
        engine_turn = getattr(self.engine, "turn", 0)
        # Incluir la posición actual en la clave: la ruta depende del origen tanto como del destino.
        cache_key = (self.entity.x, self.entity.y, dest_x, dest_y, ignore_senses)
        recalc_interval = max(1, getattr(settings, "AI_PATH_RECALC_INTERVAL", 4))
        cached_entry = self._path_cache.get(cache_key)
        if cached_entry:
            last_turn, cached_path = cached_entry
            if engine_turn - last_turn < recalc_interval:
                # Si no ha pasado el intervalo, intentamos reutilizar la ruta.
                # Sólo la damos por válida si el siguiente paso sigue siendo walkable
                # y no está bloqueado por otra entidad (evita chocar contra puertas/aliados).
                if cached_path:
                    next_x, next_y = cached_path[0]
                    try:
                        if self.entity.gamemap.tiles["walkable"][next_x, next_y]:
                            blocker = self.entity.gamemap.get_blocking_entity_at_location(next_x, next_y)
                            if not blocker or blocker is self.entity:
                                # Devolvemos copia para no mutar la cache al hacer pop() fuera.
                                return list(cached_path)
                    except Exception:
                        pass
        # Copy the walkable array.
        gamemap = self.entity.gamemap
        fighter = getattr(self.entity, "fighter", None)
        can_pass_closed_doors = getattr(fighter, "can_pass_closed_doors", False)
        can_open_doors = getattr(fighter, "can_open_doors", False)
        # No planificamos si el objetivo está fuera del sentido dominante (vista u oído)
        # y aún no está agravado: evita que enemigos “dormidos” gasten CPU calculando rutas a ciegas.
        if not ignore_senses and fighter and getattr(fighter, "aggravated", False) is False:
            fov = max(0, getattr(fighter, "fov", 0))
            foh = max(0, getattr(fighter, "foh", 0))
            use_hearing = foh > fov
            if use_hearing:
                hearing_radius = foh
                if hearing_radius <= 0:
                    return []
                # Atajo rápido por distancia antes de hacer FOV sonoro.
                if max(abs(dest_x - self.entity.x), abs(dest_y - self.entity.y)) > hearing_radius:
                    return []
                try:
                    if not self._can_hear_position(dest_x, dest_y, hearing_radius):
                        return []
                except Exception:
                    pass
            else:
                try:
                    if not gamemap.visible[dest_x, dest_y]:
                        return []
                except Exception:
                    pass

        # Si está cerca, usa un algoritmo BFS barato en radio limitado; así evitamos A* para caminos cortos.
        bfs_radius = max(1, getattr(settings, "AI_PATH_BFS_RADIUS", 8))
        bfs_path = self._bfs_path_limited(
            (self.entity.x, self.entity.y),
            (dest_x, dest_y),
            max_radius=bfs_radius,
            can_pass_closed_doors=can_pass_closed_doors,
            can_open_doors=can_open_doors,
        )
        if bfs_path:
            self._path_cache[cache_key] = (engine_turn, bfs_path)
            return list(bfs_path)

        cost = np.array(gamemap.tiles["walkable"], dtype=np.int8)
        if can_pass_closed_doors or can_open_doors:
            closed_ch = tile_types.closed_door["dark"]["ch"]
            door_mask = gamemap.tiles["dark"]["ch"] == closed_ch
            cost[door_mask] = 1

        for entity in self.entity.gamemap.entities:
            if not entity.blocks_movement or not cost[entity.x, entity.y]:
                continue
            if (
                (can_pass_closed_doors or can_open_doors)
                and getattr(getattr(entity, "name", ""), "lower", lambda: "")() == "door"
            ):
                continue
            # Add to the cost of a blocked position.
            # A lower number means more enemies will crowd behind each other in
            # hallways.  A higher number means enemies will take longer paths in
            # order to surround the player.
            cost[entity.x, entity.y] += 15

        # Create a graph from the cost array and pass that graph to a new pathfinder.
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.entity.x, self.entity.y))  # Start position.

        # Compute the path to the destination and remove the starting point.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()

        # Convert from List[List[int]] to List[Tuple[int, int]].
        computed_path = [(index[0], index[1]) for index in path]
        self._path_cache[cache_key] = (engine_turn, computed_path)
        return list(computed_path)
    
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
    """Actualmente esta AI sólo la usan los Bandidos. Básicamente tienen el mismo
    comportamiento que HostileEnemy AI sólo que en combate en ocasiones retroceden
    unos pasos antes de volver a atacar"""

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
                        print(f"DEBUG: {self.entity.name} is aggravated!")
                        #self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)

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
                        print(f"DEBUG: {self.entity.name} is aggravated!")
                        #self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)
 
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

# OBSOLETO
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

        target_stealth = getattr(target.fighter, "stealth", 0)
        target_luck = getattr(target.fighter, "luck", 0)
        if self.entity.fighter.aggravated == False:
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov - target_stealth - random.randint(0, target_luck)

        else:
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov
        
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
                        print(f"DEBUG: {self.entity.name} is aggravated!")
                        #self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)

            # Esta condición es para evitar el error IndexError: pop from empty list
            # que me ha empezado a dar a raíz de implementar las puertas como tiles y
            # como entidades
            if not self.path:
                return WaitAction(self.entity).perform()
            else:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()


        elif distance <= 1:

            # if self.entity.fighter.stamina == 0:
            #     if self_visible:
            #         self.engine.message_log.add_message(f"{self.entity.name} exhausted!", color.green)
            #     return WaitAction(self.entity).perform()
            # else:
            #     return MeleeAction(self.entity, dx, dy).perform()
        
            if self.entity.fighter.aggravated == False:
                # TODO: Comprobar si este cambio del aggravated es correcto aquí. ¿Es posible un
                # ataque sigiloso contra esta criatura?
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

class HostileEnemyV3(BaseAI):
    """Hostile enemy that can engage via sight or hearing."""

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.path2: List[Tuple[int, int]] = []

    def _can_see_actor(self, actor: Actor) -> bool:
        fighter = getattr(self.entity, "fighter", None)
        if not fighter:
            return False
        radius = max(0, getattr(fighter, "fov", 0))
        if radius <= 0:
            return False

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
        can_see = bool(visible[actor.x, actor.y])
        if settings.DEBUG_MODE:
            print(
                f"[DEBUG][SIGHT] {self.entity.name} at ({self.entity.x},{self.entity.y}) "
                f"{'can' if can_see else 'cannot'} see {getattr(actor, 'name', '?')} "
                f"at ({actor.x},{actor.y}) with fov={radius}"
            )
        return can_see

    def _sound_transparency_map(self, gamemap) -> np.ndarray:
        try:
            base = gamemap.get_transparency_map()
        except AttributeError:
            base = gamemap.tiles["transparent"]
        sound_map = base.astype(float)
        # Opacidad sonora de muros y puertas
        wall_opacity = 0.8  # Walls are semi-transparent for sound; tweak here if needed.
        sound_map = np.where(sound_map, sound_map, wall_opacity)
        try:
            closed_ch = tile_types.closed_door["dark"]["ch"]
            door_mask = gamemap.tiles["dark"]["ch"] == closed_ch
            sound_map[door_mask] = 0.5  # Closed doors are semi-transparent for sound; tweak here.
        except Exception:
            pass
        return sound_map

    def _can_hear_actor(self, actor: Actor, noise_bonus: int = 0) -> bool:
        fighter = getattr(self.entity, "fighter", None)
        if not fighter:
            return False
        if noise_bonus <= 0:
            return False
        hearing_radius = getattr(fighter, "foh", 0)
        if hearing_radius <= 0:
            return False
        gamemap = self.engine.game_map
        if not gamemap.in_bounds(actor.x, actor.y):
            return False
        sound_map = self._sound_transparency_map(gamemap)
        audible = compute_fov(
            sound_map,
            (self.entity.x, self.entity.y),
            hearing_radius,
            algorithm=constants.FOV_SHADOW,
        )
        can_hear = bool(audible[actor.x, actor.y])
        if settings.DEBUG_MODE:
            print(
                f"[DEBUG][HEARING] {self.entity.name} at ({self.entity.x},{self.entity.y}) "
                f"{'can' if can_hear else 'cannot'} hear {getattr(actor, 'name', '?')} "
                f"at ({actor.x},{actor.y}) with foh={hearing_radius}"
            )
        return can_hear

    def _noise_bonus(self, actor: Actor) -> int:
        """Noise made by the target (e.g. attacking or opening doors) reduces stealth for hearing checks."""
        engine = getattr(self, "engine", None)
        if not engine or not hasattr(engine, "noise_level"):
            return 0
        try:
            return max(0, engine.noise_level(actor))
        except Exception:
            return 0


    def _engage_range(self, base_range: Optional[int], target_stealth: int, target_luck: int) -> Tuple[Optional[int], int, int]:
        """Cálculo del rango que dispara el agravio, devolviendo también los dados usados."""
        if base_range is None:
            return None, 0, 0
        if self.entity.fighter.aggravated is False:
            luck_roll = random.randint(0, target_luck)
            engage_roll = random.randint(0, self.entity.fighter.perception)
            engage_rng = engage_roll + base_range - target_stealth - luck_roll
            return engage_rng, engage_roll, luck_roll
        else:
            luck_roll = 0
            engage_roll = random.randint(0, 3)
            engage_rng = engage_roll + base_range
            return engage_rng, engage_roll, luck_roll

    def perform(self) -> None:
        target = self._select_target()
        if not target:
            # Si no hay objetivo (p.ej. jugador oculto), sigue patrullando.
            return self._patrol_rooms()
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance.

        if self.engine.game_map.visible[self.entity.x, self.entity.y] == False:
            self_invisible = True
            self_visible = False
        else:
            self_invisible = False
            self_visible = True

        self.path = self.get_path_to(target.x, target.y)

        orig_target_stealth = getattr(target.fighter, "stealth", 0)
        target_stealth = orig_target_stealth
        target_luck = getattr(target.fighter, "luck", 0)
        noise_bonus = self._noise_bonus(target)
        # Noise makes the target easier to detect by hearing: it reduces effective stealth for engage checks.
        if noise_bonus:
            target_stealth = max(0, target_stealth - noise_bonus)

        can_see = self._can_see_actor(target)
        can_hear = False
        detection_base: Optional[int] = None
        if can_see:
            detection_base = getattr(self.entity.fighter, "fov", 0)
        else:
            can_hear = self._can_hear_actor(target, noise_bonus=noise_bonus)
            if can_hear:
                detection_base = getattr(self.entity.fighter, "foh", 0)
            elif noise_bonus > 0:
                # If the target is noisy but not yet in audible map, we still rely on hearing range.
                detection_base = getattr(self.entity.fighter, "foh", 0)

        if detection_base is None and self.entity.fighter.aggravated:
            detection_base = max(
                getattr(self.entity.fighter, "fov", 0),
                getattr(self.entity.fighter, "foh", 0),
                1,
            )

        # Si está agravado pero sin ver/oir y sin base de detección, acumula turnos perdidos.
        if self.entity.fighter.aggravated and detection_base is None:
            self._agro_lost_turns += 1
        else:
            self._agro_lost_turns = 0

        # Pérdida de agro por distancia excesiva.
        max_pursuit = getattr(settings, "AI_MAX_PURSUIT_RANGE", 25)
        if self.entity.fighter.aggravated and distance > max_pursuit:
            self.entity.fighter.aggravated = False
            self.path = []
            self._agro_lost_turns = 0

        # Pérdida de agro por demasiados turnos sin ver/oir.
        if self.entity.fighter.aggravated and self._agro_lost_turns > 0:
            threshold = getattr(settings, "AI_AGGRO_LOSS_BASE", 3) + getattr(self.entity.fighter, "aggressivity", 0)
            if self._agro_lost_turns >= threshold:
                self.entity.fighter.aggravated = False
                self.path = []
                self._agro_lost_turns = 0

        # Estar dentro del FOV o el FOH de una criatura no agravia inmediatamente.
        # Para el agravio entran en juego el stealth y el luck del target.
        # Si no hay base de detección y no está agravado, no tiene sentido seguir este turno.
        if detection_base is None and self.entity.fighter.aggravated is False:
            return WaitAction(self.entity).perform()

        engage_rng, engage_roll, luck_roll = self._engage_range(detection_base, target_stealth, target_luck)
        if engage_rng is None:
            engage_rng = -1
        if settings.DEBUG_MODE:
            noise_src = f"noise_bonus={noise_bonus}" if noise_bonus else "noise_bonus=0"
            print(
                f"[DEBUG][ENGAGE] {self.entity.name} at ({self.entity.x},{self.entity.y}) "
                f"target={getattr(target,'name','?')} dist={distance} "
                f"see={can_see} hear={can_hear} base_range={detection_base} "
                f"target_stealth={getattr(target.fighter,'stealth',0)} "
                f"target_luck={target_luck} {noise_src} "
                f"adjusted_stealth={target_stealth} "
                f"roll_base={engage_roll} luck_roll={luck_roll} engage_rng={engage_rng}"
            )

        # if settings.DEBUG_MODE:
        #     debug_msg = (
        #         f"[DEBUG] {self.entity.name}: vision={can_see}, hearing={can_hear}, "
        #         f"noise_bonus={noise_bonus}, engage_rng={engage_rng}, dist={distance}"
        #     )
        #     try:
        #         self.engine.message_log.add_message(debug_msg, color.white)
        #     except Exception:
        #         if getattr(self.engine, "debug", False):
        #             print(debug_msg)

        if engage_rng >= 0 and distance > 1 and distance <= engage_rng:
            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)
                else:
                    if settings.DEBUG_MODE:
                        print(f"DEBUG: {self.entity.name} is aggravated!")

            if not self.path:
                self._path_failure_streak += 1
                if self._path_failure_streak >= getattr(settings, "AI_PATH_FAILURE_LIMIT", 3):
                    self.entity.fighter.aggravated = False
                    self._path_failure_streak = 0
                return WaitAction(self.entity).perform()
            else:
                self._path_failure_streak = 0
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

        elif engage_rng >= 0 and distance <= 1:
            if self.entity.fighter.aggravated == False:
                # Stealth check en contacto melee: el atacante intenta no agravar todavía.
                stealth_roll = random.randint(1, 4) + target_stealth + random.randint(0, target_luck)
                awareness = random.randint(0, 3) + max(getattr(self.entity.fighter, "fov", 0), getattr(self.entity.fighter, "foh", 0))
                if settings.DEBUG_MODE:
                    dbg = f"[DEBUG] {self.entity.name} melee stealth check: roll={stealth_roll} vs dc={awareness}"
                    try:
                        self.engine.message_log.add_message(dbg, color.white)
                    except Exception:
                        if getattr(self.engine, "debug", False):
                            print(dbg)
                if stealth_roll > awareness:
                    # Supera el chequeo: no se agrava aún, permitiendo un posible stealth attack.
                    return WaitAction(self.entity).perform()
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
            self.path2 = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])

            if not self.path2:
                return WaitAction(self.entity).perform()
            else:
                if self.entity.fighter.wait_counter <= random.randint(1, 4) + self.entity.fighter.aggressivity:
                    self.entity.fighter.wait_counter += 1
                    return WaitAction(self.entity).perform()
                else:
                    self.entity.fighter.wait_counter -= 1
                    dest_x, dest_y = self.path2.pop(0)
                    return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

        # Default fallback
        return WaitAction(self.entity).perform()




class ScoutV3(BaseAI):
    """Scout enemy that can engage via sight or hearing."""

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []  # Patrol path
        self._combat_path: List[Tuple[int, int]] = []
        self.room_centers: List[Tuple[int, int]] = []
        self._patrol_index: int = -1
        self._patrol_target: Optional[Tuple[int, int]] = None

    def _load_room_centers(self) -> None:
        if self.room_centers:
            return
        centers = getattr(self.engine, "center_room_array", None) or getattr(self.engine.game_map, "center_rooms", None) or []
        centers_list = [tuple(c) for c in centers if c]

        spawn = getattr(self.entity, "spawn_coord", None)
        if spawn:
            sx, sy = spawn
            centers_list.sort(key=lambda c: abs(c[0] - sx) + abs(c[1] - sy))
        else:
            random.shuffle(centers_list)

        self.room_centers = centers_list

    def _select_next_patrol_target(self) -> bool:
        self._load_room_centers()
        if not self.room_centers:
            self._patrol_target = None
            return False

        attempts = 0
        while self.room_centers and attempts < len(self.room_centers):
            self._patrol_index = (self._patrol_index + 1) % len(self.room_centers)
            center = self.room_centers[self._patrol_index]
            candidate_path = self.get_path_to(center[0], center[1], ignore_senses=True)
            if candidate_path:
                self._patrol_target = center
                self.path = candidate_path
                return True

            # No path: descartar esta habitación y probar con la siguiente.
            self.room_centers.pop(self._patrol_index)
            if not self.room_centers:
                self._patrol_index = -1
                self._patrol_target = None
                self.path = []
                return False
            # Retroceder el índice porque el array se ha acortado.
            self._patrol_index = (self._patrol_index - 1) % len(self.room_centers)
            attempts += 1

        self._patrol_target = None
        return False

    def _patrol_rooms(self) -> None:
        if self._patrol_target is None or not self.path:
            if not self._select_next_patrol_target():
                return WaitAction(self.entity).perform()

        if not self.path:
            self._patrol_target = None
            return WaitAction(self.entity).perform()

        dest_x, dest_y = self.path.pop(0)
        try:
            return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        except exceptions.Impossible:
            # Reintentar recalculando el camino hacia el mismo objetivo; si sigue sin poder, pasa al siguiente.
            if self._patrol_target:
                #self.path = self.get_path_to(self._patrol_target[0], self._patrol_target[1])
                # Para patrullar, ignoramos los sentidos: queremos un camino aunque el jugador esté oculto.
                self.path = self.get_path_to(self._patrol_target[0], self._patrol_target[1], ignore_senses=True)
            if not self.path:
                self._patrol_target = None
                return WaitAction(self.entity).perform()
            dest_x, dest_y = self.path.pop(0)
            try:
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()
            except exceptions.Impossible:
                self._patrol_target = None
                self.path = []
                return WaitAction(self.entity).perform()

    def _can_see_actor(self, actor: Actor) -> bool:
        fighter = getattr(self.entity, "fighter", None)
        if not fighter:
            return False
        radius = max(0, getattr(fighter, "fov", 0))
        if radius <= 0:
            return False

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

    def _sound_transparency_map(self, gamemap) -> np.ndarray:
        try:
            base = gamemap.get_transparency_map()
        except AttributeError:
            base = gamemap.tiles["transparent"]
        sound_map = base.astype(float)
        wall_opacity = 0.8  # Walls are semi-transparent for sound; tweak here if needed.
        sound_map = np.where(sound_map, sound_map, wall_opacity)
        try:
            closed_ch = tile_types.closed_door["dark"]["ch"]
            door_mask = gamemap.tiles["dark"]["ch"] == closed_ch
            sound_map[door_mask] = 0.3  # Closed doors are semi-transparent for sound; tweak here.
        except Exception:
            pass
        return sound_map

    def _can_hear_actor(self, actor: Actor, noise_bonus: int = 0) -> bool:
        fighter = getattr(self.entity, "fighter", None)
        if not fighter:
            return False
        if noise_bonus <= 0:
            return False
        hearing_radius = getattr(fighter, "foh", 0)
        if hearing_radius <= 0:
            return False
        gamemap = self.engine.game_map
        if not gamemap.in_bounds(actor.x, actor.y):
            return False
        sound_map = self._sound_transparency_map(gamemap)
        audible = compute_fov(
            sound_map,
            (self.entity.x, self.entity.y),
            hearing_radius,
            algorithm=constants.FOV_SHADOW,
        )
        can_hear = bool(audible[actor.x, actor.y])
        if settings.DEBUG_MODE:
            print(
                f"[DEBUG][HEARING] {self.entity.name} at ({self.entity.x},{self.entity.y}) "
                f"{'can' if can_hear else 'cannot'} hear {getattr(actor, 'name', '?')} "
                f"at ({actor.x},{actor.y}) with foh={hearing_radius}"
            )
        return can_hear

    def _noise_bonus(self, actor: Actor) -> int:
        """Noise made by the target (e.g. attacking or opening doors) reduces stealth for hearing checks."""
        engine = getattr(self, "engine", None)
        if not engine or not hasattr(engine, "noise_level"):
            return 0
        try:
            return max(0, engine.noise_level(actor))
        except Exception:
            return 0


    def _engage_range(self, base_range: Optional[int], target_stealth: int, target_luck: int) -> Tuple[Optional[int], int, int]:
        """Cálculo del rango que dispara el agravio, devolviendo también los dados usados."""
        if base_range is None:
            return None, 0, 0
        if self.entity.fighter.aggravated is False:
            luck_roll = random.randint(0, target_luck)
            engage_roll = random.randint(0, self.entity.fighter.perception)
            engage_rng = engage_roll + base_range - target_stealth - luck_roll
            return engage_rng, engage_roll, luck_roll
        else:
            luck_roll = 0
            engage_roll = random.randint(0, 3)
            engage_rng = engage_roll + base_range
            return engage_rng, engage_roll, luck_roll

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

        self._combat_path = self.get_path_to(target.x, target.y)

        orig_target_stealth = getattr(target.fighter, "stealth", 0)
        target_stealth = orig_target_stealth
        target_luck = getattr(target.fighter, "luck", 0)
        noise_bonus = self._noise_bonus(target)
        # Noise makes the target easier to detect by hearing: it reduces effective stealth for engage checks.
        if noise_bonus:
            target_stealth = max(0, target_stealth - noise_bonus)

        can_see = self._can_see_actor(target)
        can_hear = False
        detection_base: Optional[int] = None
        if can_see:
            detection_base = getattr(self.entity.fighter, "fov", 0)
        else:
            can_hear = self._can_hear_actor(target, noise_bonus=noise_bonus)
            if can_hear:
                detection_base = getattr(self.entity.fighter, "foh", 0)
            elif noise_bonus > 0:
                detection_base = getattr(self.entity.fighter, "foh", 0)

        if detection_base is None and self.entity.fighter.aggravated:
            detection_base = max(
                getattr(self.entity.fighter, "fov", 0),
                getattr(self.entity.fighter, "foh", 0),
                1,
            )

        # Si no percibe al objetivo y no está agravado, ignoramos al jugador y seguimos patrullando.
        if detection_base is None and self.entity.fighter.aggravated is False:
            self._combat_path = []
            return self._patrol_rooms()

        # Estar dentro del FOV o el FOH de una criatura no agravia inmediatamente.
        # Para el agravio entran en juego el stealth y el luck del target.
        engage_rng, engage_roll, luck_roll = self._engage_range(detection_base, target_stealth, target_luck)
        if engage_rng is None:
            engage_rng = -1
        if settings.DEBUG_MODE:
            noise_src = f"noise_bonus={noise_bonus}" if noise_bonus else "noise_bonus=0"
            print(
                f"[DEBUG][ENGAGE] {self.entity.name} at ({self.entity.x},{self.entity.y}) "
                f"target={getattr(target,'name','?')} dist={distance} "
                f"see={can_see} hear={can_hear} base_range={detection_base} "
                f"target_stealth={getattr(target.fighter,'stealth',0)} "
                f"target_luck={target_luck} {noise_src} "
                f"adjusted_stealth={target_stealth} "
                f"roll_base={engage_roll} luck_roll={luck_roll} engage_rng={engage_rng}"
            )

        if engage_rng >= 0 and distance > 1 and distance <= engage_rng:
            if self.entity.fighter.aggravated == False:
                self.entity.fighter.aggravated = True
                if self_visible:
                    self.engine.message_log.add_message(f"{self.entity.name} is aggravated!", color.red)
                else:
                    if settings.DEBUG_MODE:
                        print(f"DEBUG: {self.entity.name} is aggravated!")

            if not self._combat_path:
                return WaitAction(self.entity).perform()
            else:
                dest_x, dest_y = self._combat_path.pop(0)
                return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()

        elif engage_rng >= 0 and distance <= 1:
            if self.entity.fighter.aggravated == False:
                # Stealth check en contacto melee: el atacante intenta no agravar todavía.
                stealth_roll = random.randint(1, 4) + target_stealth + random.randint(0, target_luck)
                awareness = random.randint(0, 3) + max(getattr(self.entity.fighter, "fov", 0), getattr(self.entity.fighter, "foh", 0))
                if settings.DEBUG_MODE:
                    dbg = f"[DEBUG] {self.entity.name} melee stealth check: roll={stealth_roll} vs dc={awareness}"
                    try:
                        self.engine.message_log.add_message(dbg, color.white)
                    except Exception:
                        if getattr(self.engine, "debug", False):
                            print(dbg)
                if stealth_roll > awareness:
                    # Supera el chequeo: no se agrava aún, permitiendo un posible stealth attack.
                    return WaitAction(self.entity).perform()
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
            self._combat_path = []
            return self._patrol_rooms()

        # Default fallback
        return WaitAction(self.entity).perform()

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

    # Movimiento oscilante/errático
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
        
        # HUIDA EN CASO DE PUNTOS DE VIDA BAJOS
        escape_threshold = round((self.entity.fighter.max_hp * self.entity.fighter.escape_threshold) / 100)
        # EN CONSTRUCCIÓN
        # if self.entity.fighter.hp < escape_threshold:
            
        #     if distance < 8:
        #         near_rooms = self.engine.game_map.nearest_rooms_from(self.entity.x, self.entity.y)
        #         for room in near_rooms:
        #             self.path = self.get_path_to(room[0], room[1])
        #             if len(self.path) >= 1:
        #                 break
        #     if self.path:
        #         dest_x, dest_y = self.path.pop(0)
        #         return MovementAction(self.entity, dest_x - self.entity.x, dest_y - self.entity.y).perform()


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

        # Camino / Serie de casillas hasta el objetivo,si hay camino transitable (si 
        # hay puertas o muros se considera intransitable)
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
            engage_rng = random.randint(0, 3) + self.entity.fighter.fov
        
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
                        print(f"DEBUG: {self.entity.name} is aggravated!")
                        #self.engine.message_log.add_message(f"DEBUG: {self.entity.name} is aggravated!", color.red)

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
                # TODO: Comprobar si este cambio del aggravated es correcto. ¿Es posible un
                # ataque sigiloso contra esta criatura?
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

            #self.engine.message_log.add_message(f"{self.entity.name} te ignora.")

            # Go home. La criatura regresa al punto de generación
            self.path2 = self.get_path_to(self.entity.spawn_coord[0], self.entity.spawn_coord[1])

            """self.path.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar al jugador)"""
            """self.path2.pop(0) devuelve las coordenadas de la casilla
            a la que tiene que moverse en el siguiente turno la criatura (para alcanzar la posición
            original en la que fué spawmeada)"""

            if not self.path2:

                return WaitAction(self.entity).perform()
                #return self._wander_idle()
            
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

class SlimeAI(BaseAI):
    """Slime that wanders within its current room, visiting tiles until it resets."""

    def __init__(self, entity: Actor):
        super().__init__(entity)
        self._visited: set[tuple[int, int]] = set()
        self._room_center: Optional[Tuple[int, int]] = None

    def on_attacked(self, attacker: "Actor") -> None:
        """Use default aggravation behavior so stealth works normally."""
        return super().on_attacked(attacker)

    def perform(self) -> None:
        gamemap = getattr(self, "engine", None)
        gamemap = getattr(gamemap, "game_map", None)
        if not gamemap:
            return WaitAction(self.entity).perform()

        room_center, room_tiles = self._current_room(gamemap)
        if room_center != self._room_center:
            self._visited.clear()
            self._room_center = room_center

        self._visited.add((self.entity.x, self.entity.y))

        dest = self._choose_next_step(gamemap, room_tiles)
        if dest:
            dx = dest[0] - self.entity.x
            dy = dest[1] - self.entity.y
            return MovementAction(self.entity, dx, dy).perform()

        # Reset and try again if stuck or room fully visited.
        self._visited.clear()
        self._visited.add((self.entity.x, self.entity.y))
        dest = self._choose_next_step(gamemap, room_tiles)
        if dest:
            dx = dest[0] - self.entity.x
            dy = dest[1] - self.entity.y
            return MovementAction(self.entity, dx, dy).perform()

        return WaitAction(self.entity).perform()

    def _current_room(self, gamemap) -> Tuple[Optional[Tuple[int, int]], List[Tuple[int, int]]]:
        """Return the center and tile list for the room containing the slime, if any."""
        tile = (self.entity.x, self.entity.y)
        room_map = getattr(gamemap, "room_tiles_map", {}) or {}
        for center, tiles in room_map.items():
            if tile in tiles:
                return center, tiles
        return None, []

    def _choose_next_step(self, gamemap, room_tiles: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """Pick a random adjacent unvisited tile within the current room (if known)."""
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
        room_tiles_set = set(room_tiles) if room_tiles else None

        candidates: List[Tuple[int, int]] = []
        for dx, dy in directions:
            nx, ny = self.entity.x + dx, self.entity.y + dy
            if not gamemap.in_bounds(nx, ny):
                continue
            if not gamemap.tiles["walkable"][nx, ny]:
                continue
            if gamemap.get_blocking_entity_at_location(nx, ny):
                continue
            if room_tiles_set is not None and (nx, ny) not in room_tiles_set:
                continue
            if (nx, ny) in self._visited:
                continue
            candidates.append((nx, ny))

        if candidates:
            return random.choice(candidates)

        # If no candidates but room_tiles known and there are still tiles left, allow revisiting to keep moving.
        if room_tiles_set and not room_tiles_set.issubset(self._visited):
            # Pick any adjacent tile within room to keep shuffling.
            for dx, dy in directions:
                nx, ny = self.entity.x + dx, self.entity.y + dy
                if (nx, ny) in room_tiles_set and gamemap.in_bounds(nx, ny) and gamemap.tiles["walkable"][nx, ny]:
                    if not gamemap.get_blocking_entity_at_location(nx, ny):
                        return (nx, ny)

        return None

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

        fighter = getattr(self.entity, "fighter", None)
        can_pass_closed_doors = getattr(fighter, "can_pass_closed_doors", False)
        can_open_doors = getattr(fighter, "can_open_doors", False)

        cost = np.array(gm.tiles["walkable"], dtype=np.int8)
        cost = np.where(cost, 1, 0).astype(np.int16)
        if can_pass_closed_doors or can_open_doors:
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
