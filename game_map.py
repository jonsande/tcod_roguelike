from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING, List, Tuple, Set, Callable, Union, Dict

import numpy as np  # type: ignore
from tcod.console import Console
from entity import Actor, Item, Obstacle, Chest
from render_order import RenderOrder
import tile_types
import entity_factories
import settings
from audio import ambient_sound, play_door_open_sound
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


def _maybe_play_door_open_sound(
    game_map: Union["GameMapTown", "GameMap"],
    actor: Optional[Actor],
    x: int,
    y: int,
) -> None:
    """Play the door open sound when the event is audible for the player."""
    engine = getattr(game_map, "engine", None)
    if engine is None:
        return
    player = getattr(engine, "player", None)
    force = actor is not None and actor is player
    engine.play_sound_effect(
        play_door_open_sound,
        source=actor,
        position=(x, y),
        level=2,
        force=force,
    )


class GameMapTown:

    def __init__(
        self, engine: Engine, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.width, self.height = width, height
        self.entities = set(entities)
        self.ambient_effects: List[object] = []
        #self.tiles = np.full((width, height), fill_value=tile_types.town_wall, order="F")
        self.tiles = np.full((width, height), fill_value=tile_types.town_floor, order="F")
        self.is_town = True
        self.visible = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player can currently see
        self.explored = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player has seen before

        self.downstairs_location = None
        self.upstairs_location = None
        self.downstairs_locations: List[Tuple[int, int]] = []
        self.downstairs_exits: Dict[Tuple[int, int], "GameMap"] = {}
        self.upstairs_target: Optional["GameMap"] = None
        self.branch_id = 0
        self.branch_depth = 0
        self.branch_entry_floor = 0
        self.branch_label = ""
        self.effective_floor = 1
        self.center_rooms: List[Tuple[int, int]] = []
        self.room_tiles_map: dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        self.room_names_by_center: Dict[Tuple[int, int], str] = {}
        self.room_ids_by_center: Dict[Tuple[int, int], str] = {}
        self.room_desc_by_center: Dict[Tuple[int, int], Optional[str]] = {}
        self.room_center_by_tile: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.room_seen: Set[Tuple[int, int]] = set()
        self.current_room_center: Optional[Tuple[int, int]] = None
        self.room_names_by_center: Dict[Tuple[int, int], str] = {}
        self.room_ids_by_center: Dict[Tuple[int, int], str] = {}
        self.room_desc_by_center: Dict[Tuple[int, int], Optional[str]] = {}
        self.room_center_by_tile: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.room_seen: Set[Tuple[int, int]] = set()
        self.current_room_center: Optional[Tuple[int, int]] = None

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

    def get_room_center_for_tile(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        return self.room_center_by_tile.get((x, y))

    def register_player_room_entry(self, actor: Actor) -> None:
        if getattr(self, "is_town", False):
            self.current_room_center = None
            return
        center = self.get_room_center_for_tile(actor.x, actor.y)
        if not center:
            self.current_room_center = None
            return
        self.current_room_center = center
        if center in self.room_seen:
            return
        self.room_seen.add(center)
        description = self.room_desc_by_center.get(center)
        if description:
            self.engine.message_log.add_message(description, color.white)

    def get_room_center_for_tile(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        return self.room_center_by_tile.get((x, y))

    def register_player_room_entry(self, actor: Actor) -> None:
        center = self.get_room_center_for_tile(actor.x, actor.y)
        if not center:
            self.current_room_center = None
            return
        self.current_room_center = center
        if center in self.room_seen:
            return
        self.room_seen.add(center)
        description = self.room_desc_by_center.get(center)
        if description:
            self.engine.message_log.add_message(description, color.white)

    def get_downstairs_locations(self) -> List[Tuple[int, int]]:
        if self.downstairs_locations:
            return list(self.downstairs_locations)
        if self.downstairs_location:
            return [self.downstairs_location]
        return []

    def get_primary_downstairs(self) -> Optional[Tuple[int, int]]:
        locations = self.get_downstairs_locations()
        return locations[0] if locations else None

    def is_downstairs_location(self, x: int, y: int) -> bool:
        return (x, y) in self.get_downstairs_locations()

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
        _maybe_play_door_open_sound(self, actor, x, y)
        return True

    def try_open_door(self, x: int, y: int, actor: Optional[Actor] = None) -> bool:
        if self.is_closed_door(x, y):
            return self.open_door(x, y, actor=actor)
        return False

    def close_door(self, x: int, y: int) -> None:
        if not self.is_open_door(x, y):
            return
        floor_entities = self._door_floor_obstructions(x, y)
        if floor_entities:
            entity_names = [getattr(entity, "name", None) for entity in floor_entities if getattr(entity, "name", None)]
            if entity_names:
                names = ", ".join(entity_names)
            else:
                names = "something"
            verb = "is" if len(floor_entities) == 1 else "are"
            raise exceptions.Impossible(f"You can't close the door; {names} {verb} lying on the floor.")
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

    def _door_floor_obstructions(self, x: int, y: int):
        door_entity = self._get_door_entity(x, y)
        obstructions = []
        for entity in self.entities:
            if entity is door_entity:
                continue
            if entity.x != x or entity.y != y:
                continue
            order = getattr(entity, "render_order", None)
            if order in (RenderOrder.ITEM, RenderOrder.CORPSE):
                obstructions.append(entity)
        return obstructions

    def _is_stairs_tile(self, x: int, y: int) -> bool:
        if self.is_downstairs_location(x, y):
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

    def add_ambient_effect(self, effect: object) -> None:
        """Register a passive visual effect to render on top of the map."""
        self.ambient_effects.append(effect)


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
        self.ambient_effects: List[object] = []
        #self.tiles = np.full((width, height), fill_value=tile_types.dummy_wall, order="F")
        self.tiles = np.full((width, height), fill_value=tile_types.wall, order="F")
        self.visible = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player can currently see
        self.explored = np.full(
            (width, height), fill_value=False, order="F"
        )  # Tiles the player has seen before

        #self.detectable = np.full((width, height), fill_value=False, order="F")

        self.downstairs_location = None
        self.upstairs_location = None
        self.downstairs_locations: List[Tuple[int, int]] = []
        self.downstairs_exits: Dict[Tuple[int, int], "GameMap"] = {}
        self.upstairs_target: Optional["GameMap"] = None
        self.branch_id = 0
        self.branch_depth = 0
        self.branch_entry_floor = 0
        self.branch_label = ""
        self.effective_floor = 1
        self.center_rooms: List[Tuple[int, int]] = []
        self.room_tiles_map: dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        self.room_names_by_center: Dict[Tuple[int, int], str] = {}
        self.room_ids_by_center: Dict[Tuple[int, int], str] = {}
        self.room_desc_by_center: Dict[Tuple[int, int], Optional[str]] = {}
        self.room_center_by_tile: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.room_seen: Set[Tuple[int, int]] = set()
        self.current_room_center: Optional[Tuple[int, int]] = None
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

    def get_room_center_for_tile(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        return self.room_center_by_tile.get((x, y))

    def register_player_room_entry(self, actor: Actor) -> None:
        center = self.get_room_center_for_tile(actor.x, actor.y)
        if not center:
            self.current_room_center = None
            return
        self.current_room_center = center
        if center in self.room_seen:
            return
        self.room_seen.add(center)
        description = self.room_desc_by_center.get(center)
        if description:
            self.engine.message_log.add_message(description, color.white)

    def get_downstairs_locations(self) -> List[Tuple[int, int]]:
        if self.downstairs_locations:
            return list(self.downstairs_locations)
        if self.downstairs_location:
            return [self.downstairs_location]
        return []

    def get_primary_downstairs(self) -> Optional[Tuple[int, int]]:
        locations = self.get_downstairs_locations()
        return locations[0] if locations else None

    def is_downstairs_location(self, x: int, y: int) -> bool:
        return (x, y) in self.get_downstairs_locations()
    
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
        _maybe_play_door_open_sound(self, actor, x, y)
        return True

    def try_open_door(self, x: int, y: int, actor: Optional[Actor] = None) -> bool:
        if self.is_closed_door(x, y):
            return self.open_door(x, y, actor=actor)
        return False

    def close_door(self, x: int, y: int) -> None:
        if not self.is_open_door(x, y):
            return
        floor_entities = self._door_floor_obstructions(x, y)
        if floor_entities:
            entity_names = [getattr(entity, "name", None) for entity in floor_entities if getattr(entity, "name", None)]
            names = ", ".join(entity_names) if entity_names else "something"
            verb = "is" if len(floor_entities) == 1 else "are"
            raise exceptions.Impossible(f"You can't close the door; {names} {verb} lying on the floor.")
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

    def _door_floor_obstructions(self, x: int, y: int):
        door_entity = self._get_door_entity(x, y)
        obstructions = []
        for entity in self.entities:
            if entity is door_entity:
                continue
            if entity.x != x or entity.y != y:
                continue
            order = getattr(entity, "render_order", None)
            if order in (RenderOrder.ITEM, RenderOrder.CORPSE):
                obstructions.append(entity)
        return obstructions

    def _is_stairs_tile(self, x: int, y: int) -> bool:
        if self.is_downstairs_location(x, y):
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

    def add_ambient_effect(self, effect: object) -> None:
        """Register a passive visual effect to render on top of the map."""
        self.ambient_effects.append(effect)


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
        self.branches: Dict[int, List[GameMap]] = {}
        self.branch_entries: Dict[int, int] = {}
        self.branch_lengths: Dict[int, int] = {}
        self._debug_key_positions: List[Tuple[str, Union[int, str], KeyLocation]] = []
        self._room_flavour_entries = self._load_room_flavour_entries()
        self._generate_world()
        self._sync_ambient_sound()

    def _load_room_flavour_entries(self) -> List[Dict[str, Optional[str]]]:
        try:
            import roomsflavour_settings as roomsflavour
        except Exception:
            return []

        raw = getattr(roomsflavour, "ROOM_FLAVOUR", None)
        if raw is None:
            raw = getattr(roomsflavour, "ROOM_FLAVOUR_ENTRIES", None)
        raw = raw or []

        entries: List[Dict[str, Optional[str]]] = []
        for entry in raw:
            if isinstance(entry, str):
                name = entry.strip()
                if name:
                    entries.append({"name": name, "description": None, "weight": 1.0})
                continue
            if isinstance(entry, dict):
                name = str(entry.get("name", "")).strip()
                if not name:
                    continue
                description = entry.get("description")
                description = str(description).strip() if description is not None else None
                weight = entry.get("weight", 1.0)
                try:
                    weight_value = float(weight)
                except (TypeError, ValueError):
                    weight_value = 1.0
                if weight_value <= 0:
                    weight_value = 1.0
                entries.append(
                    {"name": name, "description": description or None, "weight": weight_value}
                )
        return entries

    def _assign_room_flavours(self, game_map: GameMap) -> None:
        if getattr(game_map, "is_town", False):
            return
        room_tiles_map = getattr(game_map, "room_tiles_map", {}) or {}
        if not room_tiles_map:
            return

        entries = self._room_flavour_entries
        if not entries:
            entries = [{"name": "Unknown chamber", "description": None, "weight": 1.0}]

        weights = [entry.get("weight", 1.0) for entry in entries]
        name_counts: Dict[str, int] = {}
        room_center_by_tile: Dict[Tuple[int, int], Tuple[int, int]] = {}

        for center, tiles in room_tiles_map.items():
            if center in game_map.room_names_by_center:
                name = game_map.room_names_by_center[center]
                description = game_map.room_desc_by_center.get(center)
            else:
                choice = random.choices(entries, weights=weights, k=1)[0]
                name = choice["name"]
                description = choice.get("description")
            count = name_counts.get(name, 0) + 1
            name_counts[name] = count
            label = getattr(game_map, "branch_label", "").strip()
            suffix = f"{label}-{count}" if label else str(count)
            room_id = f"{name} {suffix}"
            game_map.room_names_by_center[center] = name
            game_map.room_ids_by_center[center] = room_id
            if description is not None:
                game_map.room_desc_by_center[center] = description
            for tile in tiles:
                room_center_by_tile[tile] = center

        game_map.room_center_by_tile = room_center_by_tile

    def debug_print_room_names(self) -> None:
        """Imprime en consola la lista de habitaciones generadas."""
        entries: List[Tuple[str, Tuple[int, int], str]] = []
        for game_map in self._iter_all_maps():
            label = getattr(game_map, "branch_label", "?")
            for center, room_id in getattr(game_map, "room_ids_by_center", {}).items():
                entries.append((label, center, room_id))

        if not entries:
            print("DEBUG: No hay habitaciones registradas.")
            return

        def sort_key(entry: Tuple[str, Tuple[int, int], str]) -> Tuple[int, int, int, str]:
            label = entry[0]
            if label.startswith("M-"):
                try:
                    return (0, int(label.split("-", 1)[1]), 0, label)
                except ValueError:
                    return (0, 0, 0, label)
            if label.startswith("B"):
                try:
                    branch_part, depth_part = label[1:].split("-", 1)
                    return (1, int(branch_part), int(depth_part), label)
                except ValueError:
                    return (1, 0, 0, label)
            return (2, 0, 0, label)

        print("DEBUG: Habitaciones generadas:")
        for label, center, room_id in sorted(entries, key=sort_key):
            print(f"  {room_id} -> piso {label}, centro {center}")

    def _assign_branch_metadata(
        self,
        game_map: GameMap,
        *,
        branch_id: int,
        branch_depth: int,
        entry_floor: int,
        label: str,
        effective_floor: int,
    ) -> None:
        game_map.branch_id = branch_id
        game_map.branch_depth = branch_depth
        game_map.branch_entry_floor = entry_floor
        game_map.branch_label = label
        game_map.effective_floor = effective_floor

    def _init_downstairs_data(self, game_map: GameMap) -> None:
        game_map.downstairs_locations = []
        game_map.downstairs_exits = {}
        if game_map.downstairs_location:
            game_map.downstairs_locations.append(game_map.downstairs_location)

    def _select_branch_plan(self) -> List[Dict[str, int]]:
        if settings.TOTAL_FLOORS <= 3:
            return []
        max_branches = max(0, int(getattr(settings, "MAX_SECONDARY_BRANCHES", 0)))
        if max_branches <= 0:
            return []
        candidates = list(getattr(settings, "BRANCH_FLOORS", []) or [])
        candidates = [floor for floor in candidates if 1 < floor < settings.TOTAL_FLOORS]
        fixed_floors = set(getattr(settings, "FIXED_DUNGEON_LAYOUTS", {}).keys())
        candidates = [floor for floor in candidates if floor not in fixed_floors]
        if not candidates:
            return []
        candidates = candidates[:max_branches]

        min_len = max(1, int(getattr(settings, "BRANCH_MIN_LENGTH", 1)))
        max_len = max(min_len, int(getattr(settings, "BRANCH_MAX_LENGTH", min_len)))
        plan: List[Dict[str, int]] = []
        for idx, floor in enumerate(candidates, start=1):
            length = random.randint(min_len, max_len)
            plan.append({"id": idx, "entry_floor": floor, "length": length})
        return plan

    def _resolve_branch_generator(self, name: str):
        from generators import generate_cavern, generate_dungeon_v3
        name = str(name).strip().lower()
        if name == "cavern":
            return generate_cavern
        if name == "dungeon_v3":
            return generate_dungeon_v3
        return None

    def _select_branch_generator(self) -> Callable:
        choices = getattr(settings, "BRANCH_GENERATORS", None) or []
        resolved = [self._resolve_branch_generator(name) for name in choices]
        resolved = [gen for gen in resolved if gen is not None]
        if resolved:
            return random.choice(resolved)
        from generators import generate_dungeon_v3
        return generate_dungeon_v3

    def _place_branch_downstairs(self, game_map: GameMap) -> Optional[Tuple[int, int]]:
        if getattr(game_map, "is_cavern", False) and getattr(settings, "BRANCH_CAVERN_STAIRS_ANYWHERE", True):
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
                if game_map.is_downstairs_location(x, y):
                    continue
                if any(entity.x == x and entity.y == y for entity in game_map.entities):
                    continue
                if game_map.get_blocking_entity_at_location(x, y):
                    continue
                game_map.tiles[(x, y)] = tile_types.down_stairs
                return (x, y)
            return None

        room_tiles_map = getattr(game_map, "room_tiles_map", {}) or {}
        room_tiles = [coord for tiles in room_tiles_map.values() for coord in tiles]
        if not room_tiles:
            return None
        random.shuffle(room_tiles)

        for x, y in room_tiles:
            if not game_map.in_bounds(x, y):
                continue
            if not game_map.tiles["walkable"][x, y]:
                continue
            if game_map.upstairs_location and (x, y) == game_map.upstairs_location:
                continue
            if game_map.is_downstairs_location(x, y):
                continue
            if any(entity.x == x and entity.y == y for entity in game_map.entities):
                continue
            if game_map.get_blocking_entity_at_location(x, y):
                continue
            game_map.tiles[(x, y)] = tile_types.down_stairs
            return (x, y)
        return None

    def _ensure_branch_stairs_access(self, game_map: GameMap, stairs: Tuple[int, int]) -> None:
        entry_point = game_map.upstairs_location
        if not entry_point:
            return
        from procgen import ensure_path_between, guarantee_downstairs_access
        if not ensure_path_between(game_map, entry_point, stairs):
            guarantee_downstairs_access(game_map, entry_point, stairs)

    def _generate_world(self) -> None:
        from generators import (
            generate_town,
            generate_fixed_dungeon,
            generate_cavern,
            generate_dungeon_v3,
            generate_the_library_map,
            generate_three_doors_map,
        )
        from procgen import set_generation_floor_context, reset_unique_room_registry

        self.levels = []
        self.branches = {}
        self.branch_entries = {}
        self.branch_lengths = {}
        branch_plan = self._select_branch_plan()
        reset_unique_room_registry()

        keys_placed: Set[str] = set()
        key_positions: List[Tuple[str, Union[int, str], KeyLocation]] = []
        locked_colors_by_floor: List[Tuple[int, Set[str]]] = []

        for floor in range(1, settings.TOTAL_FLOORS + 1):
            place_player = floor == 1
            place_downstairs = floor < settings.TOTAL_FLOORS
            generator, kwargs = self._select_generator(floor)
            label = f"M-{floor}"
            set_generation_floor_context(label)
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
            set_generation_floor_context(None)

            self._assign_branch_metadata(
                game_map,
                branch_id=0,
                branch_depth=0,
                entry_floor=floor,
                label=label,
                effective_floor=floor,
            )
            self._init_downstairs_data(game_map)
            self._assign_room_flavours(game_map)

            if place_player:
                self.engine.game_map = game_map
                self._update_center_rooms(game_map)
                if getattr(game_map, "register_player_room_entry", None):
                    game_map.register_player_room_entry(self.engine.player)

            self.levels.append(game_map)

            locked_colors = set(getattr(game_map, "locked_door_colors", set()) or set())
            if locked_colors:
                locked_colors_by_floor.append((floor, locked_colors))

        # Enlazar salidas del tronco principal.
        for idx in range(len(self.levels) - 1):
            current_map = self.levels[idx]
            next_map = self.levels[idx + 1]
            main_stairs = current_map.downstairs_location
            if main_stairs:
                current_map.downstairs_exits[main_stairs] = next_map
                next_map.upstairs_target = current_map

        # Generar ramas secundarias.
        for entry in branch_plan:
            branch_id = entry["id"]
            entry_floor = entry["entry_floor"]
            length = entry["length"]
            entry_map = self.levels[entry_floor - 1]

            branch_maps: List[GameMap] = []
            previous_map: GameMap = entry_map
            for depth in range(1, length + 1):
                generator = self._select_branch_generator()
                effective_floor = entry_floor + depth
                label = f"B{branch_id}-{depth}"
                place_downstairs = depth < length

                set_generation_floor_context(label)
                if generator is generate_dungeon_v3:
                    prev_lock_chance = settings.DUNGEON_V3_LOCKED_DOOR_CHANCE
                    settings.DUNGEON_V3_LOCKED_DOOR_CHANCE = 0.0
                else:
                    prev_lock_chance = None

                game_map = generator(
                    map_width=self.map_width,
                    map_height=self.map_height,
                    engine=self.engine,
                    floor_number=effective_floor,
                    place_player=False,
                    place_downstairs=place_downstairs,
                    upstairs_location=None,
                )

                if prev_lock_chance is not None:
                    settings.DUNGEON_V3_LOCKED_DOOR_CHANCE = prev_lock_chance
                set_generation_floor_context(None)

                self._assign_branch_metadata(
                    game_map,
                    branch_id=branch_id,
                    branch_depth=depth,
                    entry_floor=entry_floor,
                    label=label,
                    effective_floor=effective_floor,
                )
                self._init_downstairs_data(game_map)
                self._assign_room_flavours(game_map)

                game_map.upstairs_target = previous_map
                if previous_map is not entry_map:
                    if previous_map.downstairs_location:
                        previous_map.downstairs_exits[previous_map.downstairs_location] = game_map

                branch_maps.append(game_map)
                previous_map = game_map

            if branch_maps:
                branch_stairs = self._place_branch_downstairs(entry_map)
                if branch_stairs:
                    self.branches[branch_id] = branch_maps
                    self.branch_entries[branch_id] = entry_floor
                    self.branch_lengths[branch_id] = len(branch_maps)
                    entry_map.downstairs_locations.append(branch_stairs)
                    entry_map.downstairs_exits[branch_stairs] = branch_maps[0]
                    self._ensure_branch_stairs_access(entry_map, branch_stairs)
                    branch_maps[0].upstairs_target = entry_map
                elif settings.DEBUG_MODE:
                    print(f"DEBUG: No se pudo colocar escalera de rama en M-{entry_floor}.")

        # Colocar llaves ahora que se conocen las ramas.
        for floor, locked_colors in locked_colors_by_floor:
            self._ensure_keys_for_locked_doors(
                floor, locked_colors, keys_placed, key_positions
            )

        self._debug_key_positions = key_positions
        self.current_floor = 1
        if settings.DEBUG_MODE:
            self.debug_print_key_locations()
            self.debug_print_branch_structure()

    def _get_floor_label(self, floor: Union[int, str]) -> str:
        if isinstance(floor, str):
            return floor
        if isinstance(floor, int) and 1 <= floor <= len(self.levels):
            label = getattr(self.levels[floor - 1], "branch_label", None)
            return label or str(floor)
        return str(floor)

    def _iter_all_maps(self) -> Iterator[GameMap]:
        yield from self.levels
        for branch_maps in self.branches.values():
            yield from branch_maps

    def debug_print_key_locations(self) -> None:
        """Imprime en consola las llaves generadas y su ubicación por piso."""
        positions = list(self._debug_key_positions)
        seen = {(color, floor, pos) for color, floor, pos in positions}

        # Añadimos cualquier llave que exista actualmente en los mapas, por si se generaron fuera del registro inicial.
        for game_map in self._iter_all_maps():
            floor_label = getattr(game_map, "branch_label", None) or "?"
            for entity in game_map.entities:
                if isinstance(entity, Item):
                    id_name = getattr(entity, "id_name", "")
                    if id_name.endswith("_key"):
                        color = id_name.replace("_key", "")
                        pos = (entity.x, entity.y)
                        entry = (color, floor_label, pos)
                        if entry not in seen:
                            positions.append(entry)
                            seen.add(entry)

        if not positions:
            print("DEBUG: No se registraron llaves generadas.")
            return

        print("DEBUG: Llaves generadas:")
        for color, floor, pos in positions:
            floor_label = self._get_floor_label(floor)
            if isinstance(pos, tuple):
                location_desc = f"en {pos}"
            else:
                location_desc = pos
            print(f"  {color} key -> piso {floor_label} {location_desc}")

        # Actualizamos el registro interno para futuras llamadas.
        self._debug_key_positions = positions

    def debug_print_branch_structure(self) -> None:
        """Imprime en consola la estructura de ramas generadas."""
        if not self.branches:
            print("DEBUG: No hay ramas secundarias en este mundo.")
            return

        print("DEBUG: Ramas secundarias:")
        for branch_id, maps in sorted(self.branches.items()):
            entry_floor = self.branch_entries.get(branch_id, "?")
            length = self.branch_lengths.get(branch_id, len(maps))
            labels = [getattr(game_map, "branch_label", "?") for game_map in maps]
            labels_str = ", ".join(labels) if labels else "sin niveles"
            print(
                f"  B{branch_id}: entrada en piso M-{entry_floor}, longitud {length}, niveles: {labels_str}"
            )

    def debug_print_player_branch_location(self) -> None:
        """Imprime en consola la rama y el nivel actual del jugador."""
        current_map = self.engine.game_map
        label = getattr(current_map, "branch_label", "?")
        effective = getattr(current_map, "effective_floor", "?")
        if getattr(current_map, "branch_id", 0) == 0:
            print(f"DEBUG: Jugador en rama principal ({label}), nivel efectivo {effective}.")
        else:
            entry_floor = getattr(current_map, "branch_entry_floor", "?")
            print(
                f"DEBUG: Jugador en rama secundaria {label} (entrada M-{entry_floor}), nivel efectivo {effective}."
            )

    def _sync_ambient_sound(self) -> None:
        ambient_sound.play_for_floor(self.current_floor)

    def _select_generator(self, floor: int):
        from generators import (
            THE_LIBRARY_TEMPLATE,
            THREE_DOORS_TEMPLATE,
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
        # El generador estándar es generate_dungeon_v3.
        return generate_dungeon_v3, {}

    def _find_spawn_location(
        self,
        game_map: GameMap,
        *,
        prefer_downstairs: bool = False,
        prefer_location: Optional[Tuple[int, int]] = None,
    ) -> Tuple[int, int]:
        """Return a valid spawn location for entering an existing floor."""
        def is_valid(coord: Tuple[int, int]) -> bool:
            x, y = coord
            return game_map.in_bounds(x, y) and game_map.tiles["walkable"][x, y]

        if prefer_location and is_valid(prefer_location):
            return prefer_location

        primary_downstairs = game_map.get_primary_downstairs()
        if prefer_downstairs and primary_downstairs and is_valid(primary_downstairs):
            return primary_downstairs

        if game_map.upstairs_location and is_valid(game_map.upstairs_location):
            return game_map.upstairs_location

        for x in range(game_map.width):
            for y in range(game_map.height):
                if game_map.tiles["walkable"][x, y]:
                    return x, y

        # Fallback to the map center if no walkable tile was found.
        return game_map.width // 2, game_map.height // 2

    def get_downstairs_destination(
        self, stairs_location: Optional[Tuple[int, int]]
    ) -> Optional[GameMap]:
        current_map = self.engine.game_map
        if stairs_location is None:
            stairs_location = current_map.get_primary_downstairs()
        if not stairs_location:
            return None
        return getattr(current_map, "downstairs_exits", {}).get(stairs_location)

    def advance_floor(
        self,
        *,
        stairs_location: Optional[Tuple[int, int]] = None,
        spawn_selector: Optional[Callable[[GameMap], Tuple[int, int]]] = None,
    ) -> bool:
        """Move the player to the next pre-generated floor, if available.

        `stairs_location` selects which downstairs to use when multiple exist.
        `spawn_selector`, when provided, chooses the coordinates where the player will
        appear on the target map. Defaults to the standard spawn logic.
        """
        next_map = self.get_downstairs_destination(stairs_location)
        if not next_map:
            return False

        if spawn_selector:
            spawn_x, spawn_y = spawn_selector(next_map)
        else:
            spawn_x, spawn_y = self._find_spawn_location(next_map)
        self.engine.player.place(spawn_x, spawn_y, next_map)
        self.engine.game_map = next_map
        self.current_floor = getattr(next_map, "effective_floor", self.current_floor)
        self._update_center_rooms(next_map)
        self.engine.update_fov()
        self._sync_ambient_sound()
        return True

    def retreat_floor(self) -> bool:
        """Move the player to the previous pre-generated floor, if available."""
        current_map = self.engine.game_map
        previous_map = getattr(current_map, "upstairs_target", None)
        if previous_map is None:
            return False

        return_location = None
        for coord, target in getattr(previous_map, "downstairs_exits", {}).items():
            if target is current_map:
                return_location = coord
                break
        spawn_x, spawn_y = self._find_spawn_location(
            previous_map, prefer_downstairs=True, prefer_location=return_location
        )
        self.engine.player.place(spawn_x, spawn_y, previous_map)
        self.engine.game_map = previous_map
        self.current_floor = getattr(previous_map, "effective_floor", self.current_floor)
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
        key_positions: List[Tuple[str, Union[int, str], KeyLocation]],
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
            candidate_indexes = [
                idx for idx in range(max(1, adjusted_min) - 1, current_floor - 1)
            ]
            if not candidate_indexes:
                continue

            candidate_floors = [idx + 1 for idx in candidate_indexes]
            branch_candidates = [
                branch_id
                for branch_id, entry_floor in self.branch_entries.items()
                if entry_floor in candidate_floors
            ]
            branch_chance = max(0.0, min(1.0, getattr(settings, "KEY_BRANCH_SPAWN_CHANCE", 0.0)))
            if branch_candidates and random.random() < branch_chance:
                branch_id = random.choice(branch_candidates)
                branch_maps = self.branches.get(branch_id, [])
                if branch_maps:
                    target_map = random.choice(branch_maps)
                    pos = self._place_key_on_map(target_map, color)
                    if pos:
                        if settings.DEBUG_MODE:
                            print(
                                f"DEBUG: Llave {color} colocada en rama {target_map.branch_label}."
                            )
                        key_positions.append((color, target_map.branch_label, pos))
                        keys_placed.add(color)
                        continue

            target_idx = random.choice(candidate_indexes)
            target_map = self.levels[target_idx]
            pos = self._place_key_on_map(target_map, color)
            if pos:
                key_positions.append((color, target_map.branch_label, pos))
            keys_placed.add(color)

    def _place_key_on_floor(self, idx: int, color: str) -> Optional[KeyLocation]:
        if idx < 0 or idx >= len(self.levels):
            return None
        game_map = self.levels[idx]
        return self._place_key_on_map(game_map, color)

    def _place_key_on_map(self, game_map: GameMap, color: str) -> Optional[KeyLocation]:
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
            if game_map.is_downstairs_location(x, y):
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
            if game_map.is_downstairs_location(x, y):
                continue
            if game_map.upstairs_location and (x, y) == game_map.upstairs_location:
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
