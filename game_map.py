from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING, List, Tuple, Set, Callable, Union

import numpy as np  # type: ignore
from tcod.console import Console
from entity import Actor, Item, Obstacle, Chest
from render_order import RenderOrder
import tile_types
import entity_factories
import settings
from audio import ambient_sound
import exceptions
import color
import copy

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity
    
import random
import fixed_maps

CLOSED_DOOR_CHAR = tile_types.closed_door["dark"]["ch"]
OPEN_DOOR_CHAR = tile_types.open_door["dark"]["ch"]


KeyLocation = Union[Tuple[int, int], str]


class GameMapTown:

    def __init__(
        self, engine: Engine, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.width, self.height = width, height
        self.entities = set(entities)
        #self.tiles = np.full((width, height), fill_value=tile_types.town_wall, order="F")
        self.tiles = np.full((width, height), fill_value=tile_types.town_floor, order="F")
        self.visible = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player can currently see
        self.explored = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player has seen before

        self.downstairs_location = (0, 0)
        self.upstairs_location = None
        self.center_rooms: List[Tuple[int, int]] = []

    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def actors(self) -> Iterator[Actor]:
        """Iterate over this maps living actors."""
        yield from (
            entity
            for entity in self.entities
            if (
                (isinstance(entity, Actor) and entity.is_alive)
                or (
                    isinstance(entity, Obstacle)
                    and entity.is_alive
                    and entity.blocks_movement
                    and getattr(entity, "name", "").lower() != "door"
                )
            )
        )

    @property
    def items(self) -> Iterator[Item]:
        yield from (entity for entity in self.entities if isinstance(entity, Item))
    
    def get_blocking_entity_at_location(
        self, location_x: int, location_y: int,
    ) -> Optional[Entity]:
        """This new function iterates through all the entities, and if one is found that both blocks 
        movement and occupies the given location_x and location_y coordinates, it returns that Entity. 
        Otherwise, we return None instead."""
        for entity in self.entities:
            if (
                entity.blocks_movement
                and entity.x == location_x
                and entity.y == location_y
            ):
                return entity

        return None
    
    def get_actor_at_location(self, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.x == x and actor.y == y:
                return actor

        return None

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this map."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_closed_door(self, x: int, y: int) -> bool:
        return self.tiles["dark"]["ch"][x, y] == CLOSED_DOOR_CHAR

    def is_open_door(self, x: int, y: int) -> bool:
        return self.tiles["dark"]["ch"][x, y] == OPEN_DOOR_CHAR

    def open_door(self, x: int, y: int, actor: Optional[Actor] = None) -> bool:
        """Intentar abrir puerta; devuelve True si se abrió."""
        if not self.is_closed_door(x, y):
            return False
        door_entity = self._get_door_entity(x, y)
        lock_color = getattr(door_entity.fighter, "lock_color", None) if door_entity and hasattr(door_entity, "fighter") else None
        if lock_color and actor:
            key_id = f"{lock_color}_key"
            inv = getattr(actor, "inventory", None)
            key_item = None
            if inv:
                for item in list(inv.items):
                    if getattr(item, "id_name", "") == key_id:
                        key_item = item
                        break
            if not key_item:
                raise exceptions.Impossible(f"You need a {lock_color} key.")
            self.engine.message_log.add_message(f"You use a {lock_color} key.", color.white)
        if door_entity and hasattr(door_entity, "fighter"):
            door_entity.fighter.set_open(True)
            try:
                door_entity.fighter.lock_color = None
                door_entity.name = "Door"
                setattr(door_entity, "id_name", "Door")
            except Exception:
                pass
        else:
            self.tiles[x, y] = tile_types.open_door
        return True

    def try_open_door(self, x: int, y: int, actor: Optional[Actor] = None) -> bool:
        if self.is_closed_door(x, y):
            return self.open_door(x, y, actor=actor)
        return False

    def close_door(self, x: int, y: int) -> None:
        if not self.is_open_door(x, y):
            return
        door_entity = self._get_door_entity(x, y)
        if door_entity and hasattr(door_entity, "fighter"):
            door_entity.fighter.set_open(False)
        else:
            self.tiles[x, y] = tile_types.closed_door

    def try_close_door(self, x: int, y: int) -> bool:
        if self.is_open_door(x, y):
            self.close_door(x, y)
            return True
        return False

    def _get_door_entity(self, x: int, y: int):
        for entity in self.entities:
            if not entity:
                continue
            name = getattr(entity, "name", None)
            if not name:
                continue
            if name.lower() == "door" and entity.x == x and entity.y == y:
                return entity
        return None

    def _is_stairs_tile(self, x: int, y: int) -> bool:
        if self.downstairs_location and (x, y) == self.downstairs_location:
            return True
        if self.upstairs_location and (x, y) == self.upstairs_location:
            return True
        return False

    def render(self, console: Console) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """
        player_blind = getattr(self.engine.player.fighter, "is_blind", False)
        light_tiles = self.tiles["light"] if not player_blind else self.tiles["dark"]

        console.rgb[0 : self.width, 0 : self.height] = np.select(
            condlist=[self.visible, self.explored],
            choicelist=[light_tiles, self.tiles["dark"]],
            default=tile_types.SHROUD,
        )

        entities_sorted_for_rendering = sorted(
            self.entities, key=lambda x: x.render_order.value
        )

        player_entity = self.engine.player
        for entity in entities_sorted_for_rendering:
            # Only print entities that are in the FOV
            if self.visible[entity.x, entity.y]:
                if player_blind and entity is not player_entity:
                    continue
                if self._is_stairs_tile(entity.x, entity.y) and entity.render_order in (
                    RenderOrder.DECORATION,
                    RenderOrder.CORPSE,
                ):
                    # Keep stairs visible; skip low-priority sprites on top of them.
                    continue
                console.print(
                    x=entity.x, y=entity.y, string=entity.char, fg=entity.color
                )

    def get_transparency_map(self) -> np.ndarray:
        """Return transparency map adjusted for vision-blocking entities."""
        transparent = self.tiles["transparent"].copy()
        for entity in self.entities:
            if getattr(entity, "id_name", "").lower() == "bookshelf":
                transparent[entity.x, entity.y] = False
        return transparent


class GameMap:

    """GameMap representa una sola planta jugable: mantiene el array de tiles, visibilidad 
    y exploración del jugador, el conjunto de entidades presentes y la lógica básica para 
    consultarlas (colisiones, actores, objetos), abrír puertas y dibujar la planta (render) 
    en consola (myrogue/game_map.py (lines 126-230)). En resumen, encapsula todo lo que ocurre 
    dentro de un mapa concreto (paredes, puertas, FOV, entidades) y ofrece utilidades para que 
    el motor interactúe con ese espacio."""

    def __init__(
        self, engine: Engine, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.width, self.height = width, height
        self.entities = set(entities)
        #self.tiles = np.full((width, height), fill_value=tile_types.dummy_wall, order="F")
        self.tiles = np.full((width, height), fill_value=tile_types.wall, order="F")
        self.visible = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player can currently see
        self.explored = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player has seen before

        #self.detectable = np.full((width, height), fill_value=False, order="F")

        self.downstairs_location = (0, 0)
        self.upstairs_location = None
        self.center_rooms: List[Tuple[int, int]] = []
        self.room_tiles_map: dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        #self.downstairs_location = []

    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def actors(self) -> Iterator[Actor]:
        """Iterate over this maps living actors."""
        yield from (
            entity
            for entity in self.entities
            if (
                (isinstance(entity, Actor) and entity.is_alive)
                or (
                    isinstance(entity, Obstacle)
                    and entity.is_alive
                    and entity.blocks_movement
                    and getattr(entity, "name", "").lower() != "door"
                )
            )
        )

    @property
    def items(self) -> Iterator[Item]:
        yield from (entity for entity in self.entities if isinstance(entity, Item))
    
    def get_blocking_entity_at_location(
        self, location_x: int, location_y: int,
    ) -> Optional[Entity]:
        """This new function iterates through all the entities, and if one is found that both blocks 
        movement and occupies the given location_x and location_y coordinates, it returns that Entity. 
        Otherwise, we return None instead."""
        for entity in self.entities:
            if (
                entity.blocks_movement
                and entity.x == location_x
                and entity.y == location_y
            ):
                return entity

        return None
    
    def get_actor_at_location(self, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.x == x and actor.y == y:
                return actor

        return None
    
    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this map."""
        return 0 <= x < self.width and 0 <= y < self.height

    def nearest_rooms_from(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Devuelve todos los centros de habitación ordenados por distancia Manhattan a (x, y)."""
        centers = getattr(self, "center_rooms", None) or []
        if not centers:
            return []

        filtered = []
        for cx, cy in centers:
            if not self.in_bounds(cx, cy):
                continue
            filtered.append((cx, cy))

        if not filtered:
            return []

        def manhattan(point: Tuple[int, int]) -> int:
            px, py = point
            return abs(px - x) + abs(py - y)

        return sorted(filtered, key=manhattan)
    

    def get_room_tiles(self, center: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Devuelve las casillas de la habitación con centro `center` (de la planta actual), tal y como se guardaron al generar el mapa."""
        if not center:
            return []
        return list(self.room_tiles_map.get(center, []))
    
    def walkable_tiles_from_position(self, center: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Devuelve todas las casillas (walkable) desde el punto `center`."""
        if not center:
            return []
        cx, cy = center
        if not self.in_bounds(cx, cy):
            return []
        if not self.tiles["walkable"][cx, cy]:
            return []

        visited: Set[Tuple[int, int]] = set()
        stack: List[Tuple[int, int]] = [(cx, cy)]

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue
            visited.add((x, y))

            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not self.in_bounds(nx, ny):
                    continue
                if not self.tiles["walkable"][nx, ny]:
                    continue
                if (nx, ny) in visited:
                    continue
                stack.append((nx, ny))

        return list(visited)

    def is_closed_door(self, x: int, y: int) -> bool:
        return self.tiles["dark"]["ch"][x, y] == CLOSED_DOOR_CHAR

    def is_open_door(self, x: int, y: int) -> bool:
        return self.tiles["dark"]["ch"][x, y] == OPEN_DOOR_CHAR

    def open_door(self, x: int, y: int, actor: Optional[Actor] = None) -> bool:
        """Intentar abrir puerta; devuelve True si se abrió."""
        if not self.is_closed_door(x, y):
            return False
        door_entity = self._get_door_entity(x, y)
        lock_color = getattr(door_entity.fighter, "lock_color", None) if door_entity and hasattr(door_entity, "fighter") else None
        if lock_color and actor:
            key_id = f"{lock_color}_key"
            inv = getattr(actor, "inventory", None)
            key_item = None
            if inv:
                for item in list(inv.items):
                    if getattr(item, "id_name", "") == key_id:
                        key_item = item
                        break
            if not key_item:
                raise exceptions.Impossible(f"You need a {lock_color} key.", color.orange)
            self.engine.message_log.add_message(f"You use a {lock_color} key.", color.orange)
        if door_entity and hasattr(door_entity, "fighter"):
            door_entity.fighter.set_open(True)
            try:
                door_entity.fighter.lock_color = None
                door_entity.name = "Door"
                setattr(door_entity, "id_name", "Door")
            except Exception:
                pass
        else:
            self.tiles[x, y] = tile_types.open_door
        return True

    def try_open_door(self, x: int, y: int, actor: Optional[Actor] = None) -> bool:
        if self.is_closed_door(x, y):
            return self.open_door(x, y, actor=actor)
        return False

    def close_door(self, x: int, y: int) -> None:
        if not self.is_open_door(x, y):
            return
        door_entity = self._get_door_entity(x, y)
        if door_entity and hasattr(door_entity, "fighter"):
            door_entity.fighter.set_open(False)
        else:
            self.tiles[x, y] = tile_types.closed_door

    def try_close_door(self, x: int, y: int) -> bool:
        if self.is_open_door(x, y):
            self.close_door(x, y)
            return True
        return False

    def _get_door_entity(self, x: int, y: int):
        for entity in self.entities:
            if not entity:
                continue
            name = getattr(entity, "name", None)
            if not name:
                continue
            if name.lower() == "door" and entity.x == x and entity.y == y:
                return entity
        return None

    def _is_stairs_tile(self, x: int, y: int) -> bool:
        if self.downstairs_location and (x, y) == self.downstairs_location:
            return True
        if self.upstairs_location and (x, y) == self.upstairs_location:
            return True
        return False

    def render(self, console: Console) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """
        player_blind = getattr(self.engine.player.fighter, "is_blind", False)
        light_tiles = self.tiles["light"] if not player_blind else self.tiles["dark"]
        console.rgb[0 : self.width, 0 : self.height] = np.select(
            condlist=[self.visible, self.explored],
            choicelist=[light_tiles, self.tiles["dark"]],
            default=tile_types.SHROUD,
        )

        entities_sorted_for_rendering = sorted(
            self.entities, key=lambda x: x.render_order.value
        )

        player_entity = self.engine.player
        for entity in entities_sorted_for_rendering:
            # Only print entities that are in the FOV
            if self.visible[entity.x, entity.y]:
                if player_blind and entity is not player_entity:
                    continue
                if self._is_stairs_tile(entity.x, entity.y) and entity.render_order in (
                    RenderOrder.DECORATION,
                    RenderOrder.CORPSE,
                ):
                    continue
                console.print(
                    x=entity.x, y=entity.y, string=entity.char, fg=entity.color
                )

    def get_transparency_map(self) -> np.ndarray:
        """Return transparency map adjusted for vision-blocking entities."""
        transparent = self.tiles["transparent"].copy()
        for entity in self.entities:
            if getattr(entity, "id_name", "").lower() == "bookshelf":
                transparent[entity.x, entity.y] = False
        return transparent



class GameWorld:
    """
    Holds the settings for the GameMap, and generates new maps when moving down the stairs.

    GameWorld es un contenedor/orquestador de varios GameMap (instancias la clase 'GameMap'). 
    Define los parámetros de generación (anchura, altura, rangos de salas), crea por adelantado 
    los mapas de todos los pisos mediante distintos generadores según el nivel, guarda la lista 
    ordenada de pisos y se encarga de mover al jugador entre ellos (advance_floor, retreat_floor) 
    y de elegir los puntos de aparición apropiados (_find_spawn_location) (myrogue/game_map.py 
    (lines 233-380)). Básicamente gestiona el “metajuego”: qué mapas existen, cómo se generan y 
    cómo se transiciona de uno a otro.
    
    """

    def __init__(
        self,
        *,
        engine: Engine,
        map_width: int,
        map_height: int,
        max_rooms: int,
        room_min_size: int,
        room_max_size: int,
        current_floor: int = 0,
        #sauron_exists: bool = False,
        #grial_exists: bool = False,
        #goblin_amulet_exists: bool = False,
    ):
        self.engine = engine

        self.map_width = map_width
        self.map_height = map_height

        self.max_rooms = max_rooms

        self.room_min_size = room_min_size
        self.room_max_size = room_max_size

        self.current_floor = 1
        self.levels: List[GameMap] = []
        self._debug_key_positions: List[Tuple[str, int, KeyLocation]] = []
        self._generate_world()
        self._sync_ambient_sound()

    def _generate_world(self) -> None:
        from generators import (
            generate_dungeon,
            generate_town,
            generate_fixed_dungeon,
            generate_cavern,
            generate_dungeon_v2,
            generate_dungeon_v3,
            generate_the_library_map,
            generate_three_doors_map,
        )

        keys_placed: Set[str] = set()
        key_positions: List[Tuple[str, int, KeyLocation]] = []
        for floor in range(1, settings.TOTAL_FLOORS + 1):
            place_player = floor == 1
            place_downstairs = floor < settings.TOTAL_FLOORS
            generator, kwargs = self._select_generator(floor)
            game_map = generator(
                **kwargs,
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
                floor_number=floor,
                place_player=place_player,
                place_downstairs=place_downstairs,
                upstairs_location=None,
            )

            if place_player:
                self.engine.game_map = game_map
                self._update_center_rooms(game_map)

            self.levels.append(game_map)

            locked_colors = getattr(game_map, "locked_door_colors", set())
            if locked_colors:
                self._ensure_keys_for_locked_doors(floor, locked_colors, keys_placed, key_positions)

        self._debug_key_positions = key_positions
        self.current_floor = 1
        if settings.DEBUG_MODE:
            self.debug_print_key_locations()

    def debug_print_key_locations(self) -> None:
        """Imprime en consola las llaves generadas y su ubicación por piso."""
        positions = list(self._debug_key_positions)
        seen = {(color, floor, pos) for color, floor, pos in positions}

        # Añadimos cualquier llave que exista actualmente en los mapas, por si se generaron fuera del registro inicial.
        for idx, game_map in enumerate(self.levels):
            floor = idx + 1
            for entity in game_map.entities:
                if isinstance(entity, Item):
                    id_name = getattr(entity, "id_name", "")
                    if id_name.endswith("_key"):
                        color = id_name.replace("_key", "")
                        pos = (entity.x, entity.y)
                        entry = (color, floor, pos)
                        if entry not in seen:
                            positions.append(entry)
                            seen.add(entry)

        if not positions:
            print("DEBUG: No se registraron llaves generadas.")
            return

        print("DEBUG: Llaves generadas:")
        for color, floor, pos in positions:
            if isinstance(pos, tuple):
                location_desc = f"en {pos}"
            else:
                location_desc = pos
            print(f"  {color} key -> piso {floor} {location_desc}")

        # Actualizamos el registro interno para futuras llamadas.
        self._debug_key_positions = positions

    def _sync_ambient_sound(self) -> None:
        ambient_sound.play_for_floor(self.current_floor)

    def _select_generator(self, floor: int):
        from generators import (
            THE_LIBRARY_TEMPLATE,
            THREE_DOORS_TEMPLATE,
            generate_dungeon,
            generate_town,
            generate_fixed_dungeon,
            generate_cavern,
            generate_dungeon_v3,
            generate_the_library_map,
            generate_three_doors_map,
        )

        # NIVEL INICIAL
        if floor == 1:
            return generate_town, {}
        
        # FIXED DUNGEONS GENERATION
        # Comprobar si para este nivel hay un mapa fijo/personalizado
        fixed_layout = settings.FIXED_DUNGEON_LAYOUTS.get(floor)
        if fixed_layout:
            map_name = fixed_layout.get("map")
            if map_name == "three_doors":
                template = THREE_DOORS_TEMPLATE
            elif map_name in ("THE_LIBRARY_TEMPLATE", "the_library"):
                template = THE_LIBRARY_TEMPLATE
            else:
                template = getattr(fixed_maps, map_name, None) if map_name else None
            if template:
                walls_name = fixed_layout.get("walls")
                walls = getattr(tile_types, walls_name, tile_types.wall) if walls_name else tile_types.wall
                special_name = fixed_layout.get("walls_special")
                walls_special = getattr(tile_types, special_name, walls) if special_name else walls
                generator = generate_fixed_dungeon
                if map_name == "three_doors":
                    generator = generate_three_doors_map
                elif map_name in ("THE_LIBRARY_TEMPLATE", "the_library"):
                    generator = generate_the_library_map
                return generator, {
                    "map": template,
                    "walls": walls,
                    "walls_special": walls_special,
                }

        # CAVERNS GENERATION
        # Tirada a ver si sale un mapa de cavernas
        if random.random() < settings.CAVERN_SPAWN_CHANCE:
            return generate_cavern, {}

        # STANDARD PROCEDURAL DUNGEON GENERATION
        # Primero se carga la configuración de generación específica
        # de cada nivel (si la hay en el settings).
        variants = settings.DUNGEON_MAP_VARIANT_OVERRIDES.get(floor)
        if not variants:
            variants = settings.DUNGEON_MAP_VARIANTS
        if not variants:
            variants = [
                settings.DUNGEON_MAP_STANDARD
            ]
        weights = [variant.get("weight", 1.0) for variant in variants]
        variant = random.choices(variants, weights=weights, k=1)[0]

        # El generador estándar pasa a ser generate_dungeon_v2,
        # pero conservamos la lógica de variantes por si en el futuro
        # queremos que influyan en parámetros específicos.
        return generate_dungeon_v3, {}

    def _find_spawn_location(self, game_map: GameMap, *, prefer_downstairs: bool = False) -> Tuple[int, int]:
        """Return a valid spawn location for entering an existing floor."""
        def is_valid(coord: Tuple[int, int]) -> bool:
            x, y = coord
            return game_map.in_bounds(x, y) and game_map.tiles["walkable"][x, y]

        if prefer_downstairs and game_map.downstairs_location and is_valid(game_map.downstairs_location):
            return game_map.downstairs_location

        if game_map.upstairs_location and is_valid(game_map.upstairs_location):
            return game_map.upstairs_location

        for x in range(game_map.width):
            for y in range(game_map.height):
                if game_map.tiles["walkable"][x, y]:
                    return x, y

        # Fallback to the map center if no walkable tile was found.
        return game_map.width // 2, game_map.height // 2

    def advance_floor(
        self,
        spawn_selector: Optional[Callable[[GameMap], Tuple[int, int]]] = None,
    ) -> bool:
        """Move the player to the next pre-generated floor, if available.

        `spawn_selector`, when provided, chooses the coordinates where the player will
        appear on the target map. Defaults to the standard spawn logic.
        """
        if self.current_floor >= len(self.levels):
            return False

        self.current_floor += 1
        next_map = self.levels[self.current_floor - 1]
        if spawn_selector:
            spawn_x, spawn_y = spawn_selector(next_map)
        else:
            spawn_x, spawn_y = self._find_spawn_location(next_map)
        self.engine.player.place(spawn_x, spawn_y, next_map)
        self.engine.game_map = next_map
        self._update_center_rooms(next_map)
        self.engine.update_fov()
        self._sync_ambient_sound()
        return True

    def retreat_floor(self) -> bool:
        """Move the player to the previous pre-generated floor, if available."""
        if self.current_floor <= 1:
            return False

        self.current_floor -= 1
        previous_map = self.levels[self.current_floor - 1]
        spawn_x, spawn_y = self._find_spawn_location(previous_map, prefer_downstairs=True)
        self.engine.player.place(spawn_x, spawn_y, previous_map)
        self.engine.game_map = previous_map
        self._update_center_rooms(previous_map)
        self.engine.update_fov()
        self._sync_ambient_sound()
        return True

    def get_room_tiles_from_certain_floor(self, floor: int, center: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Devuelve las casillas de la habitación `center` en el piso indicado (1-index)."""
        if floor < 1 or floor > len(self.levels):
            return []
        game_map = self.levels[floor - 1]
        if not game_map or not center:
            return []
        return list(getattr(game_map, "room_tiles_map", {}).get(center, []))

    def _ensure_keys_for_locked_doors(
        self,
        current_floor: int,
        locked_colors: Set[str],
        keys_placed: Set[str],
        key_positions: List[Tuple[str, int, KeyLocation]],
    ) -> None:
        """Si hay puertas con cerradura en este nivel, asegura que exista al menos una llave previa."""
        if current_floor <= 1:
            return
        for color in locked_colors:
            if color in keys_placed:
                continue
            min_floor = settings.DUNGEON_V3_LOCKED_DOOR_MIN_FLOOR.get(color, 1)
            # # Este adjusted_min es para manejar el problema de que el número real de nivel 
            # # es siempre uno más que el que se marca en pantalla, lo cual estaba dando
            # # problemas en la generación de llaves.
            adjusted_min = max(1, min_floor - 2)
            candidate_indexes = [idx for idx in range(max(1, adjusted_min) - 1, current_floor - 1)]
            if not candidate_indexes:
                continue
            target_idx = random.choice(candidate_indexes)
            pos = self._place_key_on_floor(target_idx, color)
            if pos:
                key_positions.append((color, target_idx + 1, pos))
            keys_placed.add(color)

    def _place_key_on_floor(self, idx: int, color: str) -> Optional[KeyLocation]:
        if idx < 0 or idx >= len(self.levels):
            return None
        game_map = self.levels[idx]
        prototype = getattr(entity_factories, f"{color}_key", None)
        if not prototype:
            return None

        carrier_location = self._maybe_assign_key_to_monster(game_map, prototype)
        if carrier_location:
            return carrier_location

        chest_location = self._maybe_place_key_in_chest(game_map, prototype)
        if chest_location:
            return chest_location

        max_attempts = 200
        for _ in range(max_attempts):
            x = random.randint(1, game_map.width - 2)
            y = random.randint(1, game_map.height - 2)
            if not game_map.in_bounds(x, y):
                continue
            if not game_map.tiles["walkable"][x, y]:
                continue
            if game_map.upstairs_location and (x, y) == game_map.upstairs_location:
                continue
            if game_map.downstairs_location and (x, y) == game_map.downstairs_location:
                continue
            if game_map.get_blocking_entity_at_location(x, y):
                continue
            prototype.spawn(game_map, x, y)
            return (x, y)
        return None

    def _maybe_assign_key_to_monster(
        self,
        game_map: "GameMap",
        key_prototype: Item,
    ) -> Optional[str]:
        chance = getattr(settings, "KEY_CARRIER_SPAWN_CHANCE", 0.0)
        if chance <= 0 or random.random() > chance:
            return None

        allowed = getattr(settings, "KEY_CARRIER_ALLOWED_MONSTERS", None)
        if not allowed:
            return None
        allowed_names = {str(name).strip().lower() for name in allowed if str(name).strip()}
        if not allowed_names:
            return None

        player = getattr(self.engine, "player", None)
        candidates: List[Actor] = []
        for actor in game_map.actors:
            if player is not None and actor is player:
                continue
            actor_name = getattr(actor, "name", "")
            if actor_name and actor_name.lower() in allowed_names:
                candidates.append(actor)

        if not candidates:
            return None

        carrier = random.choice(candidates)
        inventory = getattr(carrier, "inventory", None)
        if inventory is None:
            return None

        key_item = copy.deepcopy(key_prototype)
        key_item.parent = inventory
        if len(inventory.items) >= inventory.capacity:
            inventory.capacity += 1
        inventory.items.append(key_item)

        carrier_name = getattr(carrier, "name", "criatura desconocida")
        return f"en el inventario de {carrier_name}"

    def _maybe_place_key_in_chest(
        self,
        game_map: "GameMap",
        key_prototype: Item,
    ) -> Optional[str]:
        chance = getattr(settings, "KEY_CHEST_SPAWN_CHANCE", 0.0)
        if chance <= 0 or random.random() > chance:
            return None

        chests: List[Chest] = [
            entity for entity in game_map.entities if isinstance(entity, Chest)
        ]
        if not chests:
            return None

        target_chest = random.choice(chests)
        key_item = copy.deepcopy(key_prototype)
        target_chest.add_item(key_item)
        return f"dentro de un cofre en ({target_chest.x}, {target_chest.y})"

    def register_adventurer_descent(self, loot: List[Item]) -> None:
        """Schedule an adventurer corpse with its loot deeper in the dungeon."""
        target_floor = self._select_adventurer_corpse_floor(self.current_floor)
        if target_floor is None:
            return
        self._place_adventurer_corpse(target_floor, loot)

    def _select_adventurer_corpse_floor(self, start_floor: int) -> Optional[int]:
        chance_step = getattr(settings, "ADVENTURER_CORPSE_CHANCE_PER_FLOOR", 0.0)
        if chance_step <= 0:
            return None
        total_floors = len(self.levels)
        for floor in range(start_floor + 1, total_floors + 1):
            diff = floor - start_floor
            chance = min(1.0, chance_step * diff)
            if random.random() < chance:
                return floor
        return None

    def _place_adventurer_corpse(self, floor: int, loot: List[Item]) -> None:
        if floor < 1 or floor > len(self.levels):
            return
        game_map = self.levels[floor - 1]
        x, y = self._find_random_free_tile(game_map)
        entity_factories.adventurer_corpse.spawn(game_map, x, y)
        for item in loot:
            item.spawn(game_map, x, y)

    def _find_random_free_tile(self, game_map: GameMap) -> Tuple[int, int]:
        for _ in range(200):
            x = random.randrange(game_map.width)
            y = random.randrange(game_map.height)
            if not game_map.in_bounds(x, y):
                continue
            if not game_map.tiles["walkable"][x, y]:
                continue
            if game_map.get_blocking_entity_at_location(x, y):
                continue
            return x, y
        return self._find_spawn_location(game_map)

    def _update_center_rooms(self, game_map: GameMap) -> None:
        centers = getattr(game_map, "center_rooms", None)
        if centers is None:
            centers = []
        self.engine.update_center_rooms_array(list(centers))
