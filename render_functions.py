from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

import color

if TYPE_CHECKING:
    from tcod import Console
    from engine import Engine
    from game_map import GameMap


def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
    if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
        return ""

    names = ", ".join(
        entity.name for entity in game_map.entities if entity.x == x and entity.y == y
    )

    #return names.capitalize()
    return names


def render_bar(
    console: Console, current_value: int, maximum_value: int, current_stamina: int, max_stamina: int, total_width: int
) -> None:
    #bar_width = int(float(current_value) / maximum_value * total_width)

    #console.draw_rect(x=6, y=37, width=total_width, height=1, ch=1, bg=color.bar_empty)

    #if bar_width > 0:
    #    console.draw_rect(
    #        x=6, y=37, width=bar_width, height=1, ch=1, bg=color.bar_filled
    #    )

    if current_value > maximum_value//2:
        hp_color = color.green
    if current_value <= maximum_value//2:
        hp_color = color.orange
        if current_value <= maximum_value//4:
            hp_color = color.red

    if current_stamina > max_stamina//2:
        stamina_color = color.blue
    if current_stamina <= max_stamina//2:
        stamina_color = color.orange
        if current_stamina <= max_stamina//4:
            stamina_color = color.red


    #console.print(
    #    x=2, y=37, string=f"HP: {current_value}/{maximum_value}", fg=hp_color
    #)
    console.print(
        x=1, y=37, string="HP: ", fg=color.bar_text
    )

    console.print(
        x=5, y=37, string=f"{current_value}/{maximum_value}", fg=hp_color
    )

    #console.print(
    #    x=13, y=37, string=f"ST: {current_stamina}/{max_stamina}", fg=stamina_color
    #)

    console.print(
        x=12, y=37, string="SP: ", fg=color.bar_text
    )

    console.print(
        x=16, y=37, string=f"{current_stamina}/{max_stamina}", fg=stamina_color
    )


def render_combat_mode(console: Console, hit, power, defense):
    console.print(
        x=20, y=37, string="IN MELEE", fg=color.red
    )
    console.print(
        x=30, y=37, string=f"Hit: {hit}", fg=color.white
    )
    console.print(
        x=37, y=37, string=f"Pow: {power}", fg=color.white
    )
    console.print(
        x=44, y=37, string=f"Def: {defense}", fg=color.white
    )


def render_fortify_indicator(console: Console):
    console.print(
        x=20, y=37, string=f"Press WAIT: +1 Def ", fg=color.orange
    )


def render_dungeon_level(
    console: Console, dungeon_level: int, location: Tuple[int, int]
) -> None:
    """
    Render the level the player is currently on, at the given location.
    """
    x, y = location

    console.print(x=x, y=y, string=f"Dungeon level: {dungeon_level}")

"""
def render_names_at_mouse_location(
    console: Console, x: int, y: int, engine: Engine
) -> None:
    mouse_x, mouse_y = engine.mouse_location

    names_at_mouse_location = get_names_at_location(
        x=mouse_x, y=mouse_y, game_map=engine.game_map
    )
    
    console.print(x=x, y=y, string=names_at_mouse_location, bg=color.black, fg=color.white)
"""    

"""
def render_names_at_mouse_location_alt(
    console: Console, x: int, y: int, engine: Engine
) -> None:
    mouse_x, mouse_y = engine.mouse_location

    names_at_mouse_location = get_names_at_location(
        x=mouse_x, y=mouse_y, game_map=engine.game_map
    )
    #console.print(x=x, y=y, string=names_at_mouse_location)
    
    TITLE = "Examine information"
    if engine.player.x <= 30:
        x = 40
    else:
        x = 0

    y = 0

    width = len(TITLE) + 8

    console.draw_frame(
        x=x,
        y=y,
        width=width,
        height=8,
        title=TITLE,
        # Para que el fondo sea transparente o no:
        clear=True,
        fg=(255, 255, 255),
        bg=(0, 0, 0),
    )

    console.print(
        x=x + 1, y=y + 1, string="Descripción 1"
    )
    console.print(
        x=x + 1, y=y + 2, string=names_at_mouse_location
    )"""
