"""Handle the loading and initialization of game sessions."""
from __future__ import annotations
from tcod import libtcodpy

import copy
import lzma
import pickle
import traceback
from typing import Optional

import tcod

import color
from engine import Engine
import entity_factories
import input_handlers
from game_map import GameWorld

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uniques



# Load the background image and remove the alpha channel.
background_image = tcod.image.load("data/menu_background.png")[:, :, :3]


def new_game() -> Engine:
    """Return a brand new game session as an Engine instance."""
    #map_width = 70
    #map_height = 44
    map_width = 80
    map_height = 36

    # Valores originales
    #room_max_size = 10
    #room_min_size = 6
    #max_rooms = 30

    #room_max_size = 9
    #room_min_size = 4
    #max_rooms = 30

    #if Engine.game_world.current_floor == 0:
    #    room_max_size = 20
    #    room_min_size = 9
    #    max_rooms = 2
    #else:
    #    room_max_size = 9
    #    room_min_size = 4
    #    max_rooms = 30

    import random
    room_max_size = random.randint(7, 13)
    room_min_size = 4
    max_rooms = random.randint(10, 30)

    # Con 'deepcopy' se crea/recupera la entidad 'player' con 
    # sus atributos (y valores de esos atributos) originales (e.e. más primitivos)
    player = copy.deepcopy(entity_factories.player)

    engine = Engine(player=player)

    engine.game_world = GameWorld(
        engine=engine,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
    )

    # Esta es la primera vez que se genera el mapa y el fov:
    engine.game_world.generate_floor()
    engine.update_fov()

    engine.message_log.add_message(
        "You arrive to Monkey Island!", color.welcome_text
    )

    dagger = copy.deepcopy(entity_factories.dagger)
    leather_armor = copy.deepcopy(entity_factories.leather_armor)
    sand_bag = copy.deepcopy(entity_factories.sand_bag)

    # Aquí se asigna el inventario del jugador como el "padre" del objeto dagger. 
    # Esto significa que la daga ahora "pertenece" al inventario del jugador o está 
    # almacenada en él.
    dagger.parent = player.inventory
    leather_armor.parent = player.inventory
    sand_bag.parent = player.inventory

    player.inventory.items.append(dagger)
    player.equipment.toggle_equip(dagger, add_message=False)

    player.inventory.items.append(leather_armor)
    player.equipment.toggle_equip(leather_armor, add_message=False)

    player.inventory.items.append(sand_bag)

    return engine


def load_game(filename: str) -> Engine:
    """Load an Engine instance from a file."""
    with open(filename, "rb") as f:
        engine = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(engine, Engine)
    return engine

#def load_floor(filename: str) -> Engine:
#    """Load an Engine instance from a file."""
#    with open(filename, "rb") as f:
#        engine = pickle.loads(lzma.decompress(f.read()))
#    assert isinstance(engine, Engine)
#    return engine


class MainMenu(input_handlers.BaseEventHandler):
    """Handle the main menu rendering and input."""

    def on_render(self, console: tcod.Console) -> None:
        """Render the main menu on a background image."""
        console.draw_semigraphics(background_image, 0, 0)

        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "YET ANOTHER ROGUELIKE",
            fg=color.menu_title,
            #alignment=tcod.CENTER,   # DEPRECATED
            alignment=libtcodpy.CENTER,
        )
        console.print(
            console.width // 2,
            console.height - 2,
            "By Letchug",
            fg=color.menu_title,
            #alignment=tcod.CENTER,   # DEPRECATED
            alignment=libtcodpy.CENTER,
        )

        menu_width = 24
        for i, text in enumerate(
            ["[N] Play a new game", "[C] Continue last game", "[Q] Quit"]
        ):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg=color.menu_text,
                bg=color.black,
                alignment=libtcodpy.CENTER,
                bg_blend=libtcodpy.BKGND_ALPHA(64),
            )

    def ev_keydown(
        self, event: tcod.event.KeyDown
    ) -> Optional[input_handlers.BaseEventHandler]:
        if event.sym in (tcod.event.KeySym.q, tcod.event.KeySym.ESCAPE):
            raise SystemExit()
        elif event.sym == tcod.event.KeySym.c:
            try:
                return input_handlers.MainGameEventHandler(load_game("savegame.sav"))
            except FileNotFoundError:
                return input_handlers.PopupMessage(self, "No saved game to load.")
            except Exception as exc:
                traceback.print_exc()  # Print to stderr.
                return input_handlers.PopupMessage(self, f"Failed to load save:\n{exc}")
        elif event.sym == tcod.event.KeySym.n:
            return input_handlers.MainGameEventHandler(new_game())

        return None