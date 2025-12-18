"""Handle the loading and initialization of game sessions."""
from __future__ import annotations
from tcod import libtcodpy

import copy
import lzma
import pickle
import traceback
from typing import Callable, Dict, List, Optional, Union

import tcod
import threading
import time
from i18n import _

import color
from engine import Engine
import entity_factories
from equipment_types import EquipmentType
import input_handlers
from game_map import GameWorld
from audio import ambient_sound
import settings
from settings import (
    INTRO_MESSAGE,
    PLAYER_STARTING_EQUIP_LIMITS,
    PLAYER_STARTING_INVENTORY,
)
import procgen

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Actor, Item
    import uniques


# console.draw_semigraphics no aplica ningún escalado automático: espera un array con 
# tamaño (alto, ancho, RGB) que ya tenga el doble de resolución que el número de tiles 
# del Console. Con la terminal actual (main.py (line 15) fija 80×44 tiles), la imagen 
# que le pases desde setup_game.py (line 41) debería medir 160×88 píxeles

# Load the background image and remove the alpha channel.
#BACKGROUND_IMAGE = tcod.image.load("data/graphics/menu_background.png")[:, :, :3]
BACKGROUND_IMAGE = tcod.image.load("data/graphics/menu.png")[:, :, :3]


_EQUIPMENT_SLOT_NAMES = {
    EquipmentType.WEAPON: "weapon",
    EquipmentType.WAND: "weapon",
    EquipmentType.ARMOR: "armor",
    EquipmentType.HEADARMOR: "head_armor",
    EquipmentType.CLOAK: "cloak",
    EquipmentType.ARTIFACT: "artifact",
    EquipmentType.RING: "ring",
}


def _normalize_inventory_entry(
    entry: Union[str, Dict[str, object]]
) -> Dict[str, object]:
    if isinstance(entry, str):
        return {"item": entry}

    if isinstance(entry, dict) and "item" in entry:
        return entry

    raise ValueError(f"Invalid PLAYER_STARTING_INVENTORY entry: {entry!r}")


def _slot_name_for_item(item: "Item") -> str:
    equipment_type = item.equippable.equipment_type
    return _EQUIPMENT_SLOT_NAMES.get(equipment_type, equipment_type.name.lower())


def _resolve_factory_item(item_name: str):
    try:
        return getattr(entity_factories, item_name)
    except AttributeError as exc:  # pragma: no cover - configuration-time error
        raise ValueError(
            f"Unknown starting item '{item_name}' in PLAYER_STARTING_INVENTORY."
        ) from exc


def _add_starting_items(player: "Actor") -> None:
    """Populate the player's inventory and equip requested items."""
    items_to_equip: Dict[str, List["Item"]] = {}

    for raw_entry in PLAYER_STARTING_INVENTORY:
        entry = _normalize_inventory_entry(raw_entry)
        item_name = entry["item"]
        quantity = int(entry.get("quantity", 1))
        equip_flag = bool(entry.get("equip", False))

        if quantity <= 0:
            raise ValueError(
                f"Starting item '{item_name}' must have quantity >= 1 (got {quantity})."
            )

        prototype = _resolve_factory_item(item_name)

        for idx in range(quantity):
            item = copy.deepcopy(prototype)
            item.parent = player.inventory
            player.inventory.items.append(item)

            should_equip = equip_flag and idx == 0
            if should_equip:
                if item.equippable is None:
                    raise ValueError(
                        f"Starting item '{item_name}' is not equippable but `equip` is True."
                    )
                slot_name = _slot_name_for_item(item)
                items_to_equip.setdefault(slot_name, []).append(item)

    for slot_name, items in items_to_equip.items():
        limit = PLAYER_STARTING_EQUIP_LIMITS.get(slot_name, 2)
        if len(items) > limit:
            raise ValueError(
                f"Too many items configured to start equipped for slot '{slot_name}'. "
                f"Limit is {limit}, got {len(items)}."
            )

        for item in items[:limit]:
            player.equipment.toggle_equip(item, add_message=False)


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
    # TODO: comprobar si estos valores de room_max_size, room_min_size
    # y max_rooms se están aplicando o no a la hora de generar un mapa,
    # o si se están aplicando los establecidos en settings.py
    room_max_size = random.randint(7, 13)
    room_min_size = 4
    max_rooms = random.randint(10, 30)

    # Con 'deepcopy' se crea/recupera la entidad 'player' con 
    # sus atributos (y valores de esos atributos) originales (e.e. más primitivos)
    player = copy.deepcopy(entity_factories.player)

    engine = Engine(player=player, debug=True)

    # Al iniciar una run nueva vaciamos los contadores de generación para que los límites globales
    # de max_instances y los informes de depuración empiecen limpios.
    procgen.reset_generation_stats()

    engine.game_world = GameWorld(
        engine=engine,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
    )

    # Tras generar todos los mapas, garantizar mínimos configurados por min_instances.
    procgen.enforce_minimum_spawns(engine.game_world.levels)

    # El primer piso ya se ha generado y el jugador ha sido colocado.
    engine.update_fov()

    engine.message_log.add_message(
        INTRO_MESSAGE, color.welcome_text
    )
    engine.message_log.add_message(
        _("(Press F1 for help)"), color.orange
    )

    _add_starting_items(player)

    if getattr(settings, "INTRO_ENABLED", False):
        engine.schedule_intro(getattr(settings, "INTRO_SLIDES", []))

    return engine


def load_game(filename: str) -> Engine:
    """Load an Engine instance from a file."""
    with open(filename, "rb") as f:
        engine = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(engine, Engine)
    game_world = getattr(engine, "game_world", None)
    if game_world:
        ambient_sound.play_for_floor(game_world.current_floor)
    return engine

#def load_floor(filename: str) -> Engine:
#    """Load an Engine instance from a file."""
#    with open(filename, "rb") as f:
#        engine = pickle.loads(lzma.decompress(f.read()))
#    assert isinstance(engine, Engine)
#    return engine


class MainMenu(input_handlers.BaseEventHandler):
    """Handle the main menu rendering and input."""

    def __init__(self) -> None:
        super().__init__()
        ambient_sound.play_menu_track()

    def on_render(self, console: tcod.Console) -> None:
        """Render the main menu on a background image."""
        console.draw_semigraphics(BACKGROUND_IMAGE, 0, 0)

#         console.print(
#             6,
#             2,
#         """
# ░▒▓█████▓▒░░░▒▓█████▓▒░▒▓███████▓▒░░▒▓█████▓▒░░▒▓█████▓▒░░░▒▓██████▓▒░ ░▒▓█████▓▒░  
# ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░ 
# ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░ 
# ░▒▓█████▓▒░░░▒▓███▓▒░    ░▒▓█▓▒░  ░▒▓█▓▒░▒▓█▓▒░▒▓██████▓▒░░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░ 
# ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░ 
# ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░ 
# ░▒▓█▓▒░▒▓█▓▒░▒▓█████▓▒░  ░▒▓█▓▒░  ░░▒▓█████▓▒░░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░▒▓█▓▒░░▒▓█████▓▒░  
                                                                                            
                                                                                            
#         """
#         )

        console.print(
            console.width // 2,
            console.height // 2 - 8,
            _("a roguelike"),
            #fg=color.menu_title,
            #fg=(155, 155, 33),
            fg=color.descend,
            #bg=(9,9,11),
            #alignment=tcod.CENTER,   # DEPRECATED
            alignment=libtcodpy.CENTER,
        )
        console.print(
            console.width // 2,
            console.height - 2,
            "By Letchug",
            #fg=color.menu_title,
            fg=(25,25,25),
            #alignment=tcod.CENTER,   # DEPRECATED
            alignment=libtcodpy.CENTER,
        )

        menu_width = 24
        for i, text in enumerate(
            [_("[N] Play a new game"), _("[C] Continue last game"), _("[Q] Quit")]
        ):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                #fg=color.menu_text,
                fg=(200,200,200),
                #bg=color.black,
                #bg=(9,9,11),
                alignment=libtcodpy.CENTER,
                bg_blend=libtcodpy.BKGND_ALPHA(64),
            )

        console.print(
            console.width // 2,
            28,
            _("A experimental roguelike made with libtcod and pygame.\nThanks to CO.AG for his awesome music\n and to the whole open-source community."),
            fg=(15,15,15),
            alignment=libtcodpy.CENTER,
        )

    def ev_keydown(
        self, event: tcod.event.KeyDown
    ) -> Optional[input_handlers.BaseEventHandler]:
        if event.sym in (tcod.event.KeySym.q, tcod.event.KeySym.ESCAPE):
            ambient_sound.stop_menu_track()
            raise SystemExit()
        elif event.sym == tcod.event.KeySym.c:
            ambient_sound.stop_menu_track()
            try:
                handler = input_handlers.MainGameEventHandler(load_game("savegame.sav"))
            except FileNotFoundError:
                ambient_sound.play_menu_track()
                return input_handlers.PopupMessage(self, "No saved game to load.")
            except Exception as exc:
                traceback.print_exc()  # Print to stderr.
                ambient_sound.play_menu_track()
                return input_handlers.PopupMessage(self, f"Failed to load save:\n{exc}")
            return handler
        elif event.sym == tcod.event.KeySym.n:
            ambient_sound.stop_menu_track()
            return LoadingScreenHandler(self, new_game)

        return None


class LoadingScreenHandler(input_handlers.BaseEventHandler):
    """Simple ASCII loading animation shown while the dungeon is generated."""

    _SPINNER = ["|", "/", "-", "\\"]

    def __init__(self, parent_handler: input_handlers.BaseEventHandler, loader: Callable[[], Engine]):
        if not isinstance(parent_handler, input_handlers.BaseEventHandler):
            raise TypeError("parent_handler must inherit from BaseEventHandler")
        self.parent = parent_handler
        self._loader = loader
        self._engine_result: Optional[Engine] = None
        self._error: Optional[str] = None
        self._done = False
        self._start_time = time.perf_counter()
        self._thread = threading.Thread(target=self._run_loader, daemon=True)
        self._thread.start()

    def _run_loader(self) -> None:
        try:
            engine = self._loader()
            self._engine_result = engine
        except Exception:
            traceback.print_exc()
            self._error = traceback.format_exc()
        finally:
            self._done = True

    def on_render(self, console: tcod.Console) -> None:
        console.clear()
        center_x = console.width // 2
        center_y = console.height // 2 - 2

        # console.print(
        #     center_x,
        #     center_y - 4,
        #     "Generando...",
        #     fg=color.menu_text,
        #     alignment=libtcodpy.CENTER,
        # )

        elapsed = time.perf_counter() - self._start_time
        bar_width = 28
        bar_chars = ["-"] * bar_width

        if self._done and self._engine_result and not self._error:
            bar_chars = ["="] * bar_width
        else:
            head = int((elapsed * 8) % bar_width)
            trail = 5
            for offset in range(trail):
                idx = (head - offset) % bar_width
                bar_chars[idx] = "="
        bar = "[" + "".join(bar_chars) + "]"

        spinner = self._SPINNER[int(elapsed * 6) % len(self._SPINNER)]
        # ascii_pick = [
        #     r"   /\\",
        #     r"  /__\\   {}".format(spinner),
        #     r"     /",
        # ]
        # for idx, line in enumerate(ascii_pick):
        #     console.print(
        #         center_x,
        #         center_y - 1 + idx,
        #         line,
        #         fg=color.menu_text,
        #         alignment=libtcodpy.CENTER,
        #     )

        console.print(
            center_x,
            center_y + 3,
            bar,
            fg=color.white,
            alignment=libtcodpy.CENTER,
        )

        if self._done:
            if self._engine_result and not self._error:
                # status = "¡Listo!"
                # console.print(
                #     center_x,
                #     center_y + 5,
                #     status,
                #     fg=color.orange,
                #     alignment=libtcodpy.CENTER,
                # )
                console.print(
                    center_x - 1,
                    center_y + 5,
                    # "Pulsa cualquier tecla para continuar",
                    _("(Press any key)"),
                    fg=color.menu_text,
                    alignment=libtcodpy.CENTER,
                )
            else:
                console.print(
                    center_x,
                    center_y + 5,
                    # "Hubo un problema al generar el juego.",
                    "There was a problem",
                    fg=color.red,
                    alignment=libtcodpy.CENTER,
                )
                console.print(
                    center_x,
                    center_y + 7,
                    # "Pulsa cualquier tecla para volver al menú.",
                    "= Press any key to return =",
                    fg=color.menu_text,
                    alignment=libtcodpy.CENTER,
                )
        else:
            console.print(
                center_x - 1,
                center_y + 5,
                _("LOADING"),
                fg=color.menu_text,
                alignment=libtcodpy.CENTER,
            )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[input_handlers.BaseEventHandler]:
        if not self._done:
            return None

        if self._engine_result and not self._error:
            return input_handlers.MainGameEventHandler(self._engine_result)

        # Algo salió mal; vuelve al menú principal.
        ambient_sound.play_menu_track()
        return self.parent
