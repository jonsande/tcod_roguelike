from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING, List, Tuple

import numpy as np  # type: ignore
from tcod.console import Console
from entity import Actor, Item, Obstacle
import tile_types
import entity_factories
import settings
from audio import ambient_sound
import exceptions
import color

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity
    
import random
import fixed_maps

CLOSED_DOOR_CHAR = tile_types.closed_door["dark"]["ch"]
OPEN_DOOR_CHAR = tile_types.open_door["dark"]["ch"]


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
            inv.items.remove(key_item)
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
                console.print(
                    x=entity.x, y=entity.y, string=entity.char, fg=entity.color
                )


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
            inv.items.remove(key_item)
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
                console.print(
                    x=entity.x, y=entity.y, string=entity.char, fg=entity.color
                )



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
        self._generate_world()
        self._sync_ambient_sound()

    def _generate_world(self) -> None:
        from procgen import (
            generate_dungeon,
            generate_town,
            generate_fixed_dungeon,
            generate_cavern,
            generate_dungeon_v2,
            generate_dungeon_v3,
        )

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

        self.current_floor = 1

    def _sync_ambient_sound(self) -> None:
        ambient_sound.play_for_floor(self.current_floor)

    def _select_generator(self, floor: int):
        from procgen import generate_dungeon, generate_town, generate_fixed_dungeon, generate_cavern, generate_dungeon_v2, generate_dungeon_v3

        # NIVEL INICIAL
        if floor == 1:
            return generate_town, {}
        
        # FIXED DUNGEONS GENERATION
        # Comprobar si para este nivel hay un mapa fijo/personalizado
        fixed_layout = settings.FIXED_DUNGEON_LAYOUTS.get(floor)
        if fixed_layout:
            map_name = fixed_layout.get("map")
            template = getattr(fixed_maps, map_name, None) if map_name else None
            if template:
                walls_name = fixed_layout.get("walls")
                walls = getattr(tile_types, walls_name, tile_types.wall) if walls_name else tile_types.wall
                special_name = fixed_layout.get("walls_special")
                walls_special = getattr(tile_types, special_name, walls) if special_name else walls
                return generate_fixed_dungeon, {
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

    def advance_floor(self) -> bool:
        """Move the player to the next pre-generated floor, if available."""
        if self.current_floor >= len(self.levels):
            return False

        self.current_floor += 1
        next_map = self.levels[self.current_floor - 1]
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
