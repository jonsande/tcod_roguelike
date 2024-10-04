from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING

import numpy as np  # type: ignore
from tcod.console import Console
from entity import Actor, Item, Obstacle
import tile_types
import entity_factories

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity
    
import random
from fixed_maps import template, temple, three_doors


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

    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def actors(self) -> Iterator[Actor]:
        """Iterate over this maps living actors."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Actor) and entity.is_alive
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

    def render(self, console: Console) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """
        #console.tiles_rgb[0 : self.width, 0 : self.height] = np.select(     # DEPRECATED
        console.rgb[0 : self.width, 0 : self.height] = np.select(
            condlist=[self.visible, self.explored],
            choicelist=[self.tiles["light"], self.tiles["dark"]],
            default=tile_types.SHROUD,
        )

        entities_sorted_for_rendering = sorted(
            self.entities, key=lambda x: x.render_order.value
        )

        for entity in entities_sorted_for_rendering:
            # Only print entities that are in the FOV
            if self.visible[entity.x, entity.y]:
                console.print(
                    x=entity.x, y=entity.y, string=entity.char, fg=entity.color
                )


class GameMap:

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
            if isinstance(entity, Actor) and entity.is_alive or isinstance(entity, Obstacle) and entity.is_alive
            #if isinstance(entity, Actor) and entity.is_alive
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

    def render(self, console: Console) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """
        console.tiles_rgb[0 : self.width, 0 : self.height] = np.select(
            condlist=[self.visible, self.explored],
            choicelist=[self.tiles["light"], self.tiles["dark"]],
            default=tile_types.SHROUD,
        )

        entities_sorted_for_rendering = sorted(
            self.entities, key=lambda x: x.render_order.value
        )

        for entity in entities_sorted_for_rendering:
            # Only print entities that are in the FOV
            if self.visible[entity.x, entity.y]:
                console.print(
                    x=entity.x, y=entity.y, string=entity.char, fg=entity.color
                )


class GameWorld:
    """
    Holds the settings for the GameMap, and generates new maps when moving down the stairs.
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
        #adventurer_unique_exists: bool = False,
    ):
        self.engine = engine

        self.map_width = map_width
        self.map_height = map_height

        self.max_rooms = max_rooms

        self.room_min_size = room_min_size
        self.room_max_size = room_max_size

        self.current_floor = current_floor

        #self.sauron_exists = sauron_exists
        #self.grial_exists = grial_exists
        #self.goblin_amulet_exists = goblin_amulet_exists
        #self.adventurer_unique_exists = adventurer_unique_exists

    def generate_floor(self) -> None:

        """Aquí establecemos los mapas fijos
        Dependiendo de en qué nivel nos encontramos, se disparará un generador
        del procgen u otro"""

        from procgen import generate_dungeon, generate_town, generate_fixed_dungeon

        self.current_floor += 1

        # STARTING LEVEL
        if self.current_floor == 1:

            self.engine.game_map = generate_town(
            max_rooms=self.max_rooms,
            room_min_size=self.room_min_size,
            room_max_size=self.room_max_size,
            map_width=self.map_width,
            map_height=self.map_height,
            engine=self.engine,
        )
        # FIXED LEVELS
        elif self.current_floor == 6:
            self.engine.game_map = generate_fixed_dungeon(
            map_width=self.map_width,
            map_height=self.map_height,
            engine=self.engine,
            map=temple,
            walls=tile_types.wall_v1,
            walls_special=tile_types.wall_v2,
            )
        elif self.current_floor == 11:
            self.engine.game_map = generate_fixed_dungeon(
            map_width=self.map_width,
            map_height=self.map_height,
            engine=self.engine,
            map=three_doors,
            walls=tile_types.wall_v2,
            walls_special=tile_types.wall_v1,
            )
        # RANDOMIZED LEVELS
        elif self.current_floor == random.randint(3,16):
            self.engine.game_map = generate_dungeon(
                max_rooms=90,
                room_min_size=2,
                room_max_size=12,
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
            )
        elif self.current_floor == random.randint(3,16):
            self.engine.game_map = generate_dungeon(
                max_rooms=60,
                room_min_size=3,
                room_max_size=9,
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
            )
        else: 
            self.engine.game_map = generate_dungeon(
                max_rooms=self.max_rooms,
                room_min_size=self.room_min_size,
                room_max_size=self.room_max_size,
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
            )

