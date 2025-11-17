"""Handle the loading and initialization of game sessions."""
from __future__ import annotations
from tcod import libtcodpy

import copy
import lzma
import pickle
import traceback
from typing import Dict, List, Optional, Union

import tcod

import color
from engine import Engine
import entity_factories
from equipment_types import EquipmentType
import input_handlers
from game_map import GameWorld
from audio import ambient_sound
from settings import (
    INTRO_MESSAGE,
    PLAYER_STARTING_EQUIP_LIMITS,
    PLAYER_STARTING_INVENTORY,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Actor, Item
    import uniques



# Load the background image and remove the alpha channel.
background_image = tcod.image.load("data/menu_background.png")[:, :, :3]


_EQUIPMENT_SLOT_NAMES = {
    EquipmentType.WEAPON: "weapon",
    EquipmentType.ARMOR: "armor",
    EquipmentType.ARTEFACT: "artefact",
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

    engine.game_world = GameWorld(
        engine=engine,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
    )

    # El primer piso ya se ha generado y el jugador ha sido colocado.
    engine.update_fov()

    engine.message_log.add_message(
        INTRO_MESSAGE, color.welcome_text
    )

    _add_starting_items(player)

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

    def on_render(self, console: tcod.Console) -> None:
        """Render the main menu on a background image."""
        console.draw_semigraphics(background_image, 0, 0)

        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "ADVENTURERS!",
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
