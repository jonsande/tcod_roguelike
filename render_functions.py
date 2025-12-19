from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

import textwrap

import color
from render_order import RenderOrder
from entity import Actor
from i18n import _
from components.ai import SleepingEnemy

if TYPE_CHECKING:
    from tcod import Console
    from engine import Engine
    from game_map import GameMap


def _unique_names(names: List[str]) -> List[str]:
    """Return the unique names while preserving order, adding stack counts."""
    counts: dict[str, int] = {}
    ordered: List[tuple[str, str]] = []
    for name in names:
        lowered = name.lower()
        if lowered not in counts:
            ordered.append((lowered, name))
            counts[lowered] = 0
        counts[lowered] += 1

    unique_names: List[str] = []
    for lowered, original in ordered:
        count = counts[lowered]
        if count > 1:
            unique_names.append(f"{original} (x{count})")
        else:
            unique_names.append(original)
    return unique_names


def _format_list_with_and(words: List[str]) -> str:
    if not words:
        return ""
    if len(words) == 1:
        return words[0]
    return f"{', '.join(words[:-1])} and {words[-1]}"


def _slime_inside_description(entity: Actor) -> Optional[str]:
    """Return a '(with ... inside)' suffix describing slime inventory, or None."""
    fighter = getattr(entity, "fighter", None)
    if not fighter or not getattr(fighter, "is_slime", False):
        return None
    inventory = getattr(entity, "inventory", None)
    if not inventory:
        return None
    counts: dict[str, int] = {}
    order: List[str] = []
    for item in getattr(inventory, "items", []):
        name = getattr(item, "name", None)
        if not name:
            continue
        key = name.lower()
        if key not in counts:
            order.append(name)
            counts[key] = 0
        counts[key] += 1
    if not counts:
        return None

    parts: List[str] = []
    for original in order:
        key = original.lower()
        count = counts.get(key, 1)
        if count <= 1:
            parts.append(original)
        else:
            plural = original if original.endswith("s") else f"{original}s"
            parts.append(plural)

    joined = _format_list_with_and(parts)
    if not joined:
        return None
    return f" (with {joined} inside)"

# Version without equipment info
# def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
#     if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
#         return ""

#     names = [
#         entity.name for entity in game_map.entities if entity.x == x and entity.y == y
#     ]

#     tile_descriptions: List[str] = []
#     if game_map.upstairs_location and (x, y) == game_map.upstairs_location:
#         tile_descriptions.append("There are upstairs")
#     if game_map.downstairs_location and (x, y) == game_map.downstairs_location:
#         tile_descriptions.append("There are downstairs")

#     return ", ".join(_unique_names(names) + tile_descriptions)

def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
    if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
        return ""

    names = []
    for entity in game_map.entities:
        if entity.x == x and entity.y == y:
            name = getattr(entity, "name", None)
            if not isinstance(name, str):
                # Entities like vanished foes clear their name; skip them on hover.
                continue
            if isinstance(entity, Actor):
                equipped = []
                if getattr(entity, "equipment", None):
                    for item in entity.equipment.equipped_items():
                        item_name = getattr(item, "name", None)
                        if item_name:
                            equipped.append(item_name)
                if equipped:
                    name += f" (with {_format_list_with_and(equipped)})"
                slime_suffix = _slime_inside_description(entity)
                if slime_suffix:
                    name += slime_suffix
                ai = getattr(entity, "ai", None)
                if isinstance(ai, SleepingEnemy):
                    name += " (sleeping)"
            names.append(name)

    tile_descriptions: List[str] = []
    if game_map.upstairs_location and (x, y) == game_map.upstairs_location:
        tile_descriptions.append("There are upstairs")
    if game_map.downstairs_location and (x, y) == game_map.downstairs_location:
        tile_descriptions.append("There are downstairs")

    return ", ".join(_unique_names(names) + tile_descriptions)


def get_items_and_features_at_location(x: int, y: int, game_map: GameMap) -> str:
    if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
        return ""

    item_names = [
        entity.name
        for entity in game_map.entities
        if entity.x == x
        and entity.y == y
        and entity.render_order == RenderOrder.ITEM
    ]

    tile_descriptions: List[str] = []
    if game_map.upstairs_location and (x, y) == game_map.upstairs_location:
        tile_descriptions.append("There are upstairs")
    if game_map.downstairs_location and (x, y) == game_map.downstairs_location:
        tile_descriptions.append("There are downstairs")

    return ", ".join(_unique_names(item_names) + tile_descriptions)


def _wrap_tile_info_text(text: str, width: int) -> List[str]:
    return textwrap.wrap(text, width=width, break_on_hyphens=False, break_long_words=False)


def _append_prompt_to_lines(lines: List[str], prompt: str, width: int) -> List[str]:
    wrapped_lines = list(lines)
    if not wrapped_lines:
        return [prompt]

    final_line = f"{wrapped_lines[-1]} {prompt}"
    if len(final_line) <= width:
        wrapped_lines[-1] = final_line
    else:
        wrapped_lines.append(prompt)
    return wrapped_lines


def _render_tile_info_block(
    console: Console,
    engine: Engine,
    text: str,
    x: int,
    y: int,
    *,
    source: str,
    coords: Tuple[int, int],
) -> int:
    engine.update_tile_info_position(source, coords)
    if engine.tile_info_pause_active:
        return 0
    if not text:
        return 0
    max_width = max(1, console.width - x - 1)
    lines = _wrap_tile_info_text(text, max_width)
    if not lines:
        return 0

    if len(lines) == 1:
        console.print(x=x, y=y, string=lines[0], bg=color.black, fg=color.white)
        return 1

    if engine.is_tile_info_context_suppressed(source, coords, text):
        return 0

    prompt = _("(Press any key)")
    lines_with_prompt = _append_prompt_to_lines(lines, prompt, max_width)
    engine.activate_tile_info_pause(
        lines_with_prompt,
        source=source,
        coords=coords,
        text=text,
        position=(x, y),
    )
    return 0


def render_bar(
    console: Console,
    current_value: int,
    maximum_value: int,
    current_stamina: int,
    max_stamina: int,
    layout: dict,
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
    stats_y = layout["stats_row"]

    console.print(x=layout["hp_label_x"], y=stats_y, string="HP: ", fg=color.bar_text)

    console.print(
        x=layout["hp_value_x"],
        y=stats_y,
        string=f"{current_value}/{maximum_value}",
        fg=hp_color,
    )

    #console.print(
    #    x=13, y=37, string=f"ST: {current_stamina}/{max_stamina}", fg=stamina_color
    #)

    console.print(x=layout["sp_label_x"], y=stats_y, string="SP: ", fg=color.bar_text)

    console.print(
        x=layout["sp_value_x"],
        y=stats_y,
        string=f"{current_stamina}/{max_stamina}",
        fg=stamina_color,
    )


def render_combat_mode(console: Console, hit, defense, layout: dict):
    y = layout["stats_row"]
    console.print(x=layout["combat_label_x"], y=y, string="IN MELEE", fg=color.red)
    console.print(x=layout["combat_hit_x"], y=y, string=f"To-Hit: {hit}", fg=color.white)
    console.print(x=layout["combat_def_x"], y=y, string=f"Def: {defense}", fg=color.white)
    # console.print(
    #     x=47, y=37, string=f"Pow: {power}", fg=color.white
    # )


def render_fortify_indicator(console: Console, layout: dict):
    console.print(x=layout["fortify_x"], y=layout["stats_row"], string="Press WAIT: +1 Def ", fg=color.orange)


def render_dungeon_level(
    console: Console, dungeon_level: int, location: Tuple[int, int]
) -> None:
    """
    Render the level the player is currently on, at the given location.
    """
    x, y = location

    # console.print(x=x, y=y, string=f"Dungeon level: {dungeon_level}")
    console.print(x=x, y=y, string=f"Level: {dungeon_level}")


def render_names_at_mouse_location(
    console: Console, x: int, y: int, engine: Engine
) -> int:
    mouse_x, mouse_y = engine.mouse_location

    names_at_mouse_location = get_names_at_location(
        x=mouse_x, y=mouse_y, game_map=engine.game_map
    )
    return _render_tile_info_block(
        console,
        engine,
        names_at_mouse_location,
        x,
        y,
        source="mouse",
        coords=(mouse_x, mouse_y),
    )


def render_tile_info_overlay(console: Console, engine: Engine) -> None:
    if not engine.tile_info_pause_active:
        return
    x, y = engine.tile_info_overlay_position
    prompt = _("(Press any key)")
    for index, line in enumerate(engine.tile_info_overlay_lines):
        row_y = y + index
        prompt_start = line.rfind(prompt)
        if prompt_start != -1:
            before = line[:prompt_start]
            prompt_text = line[prompt_start:]
            if before:
                console.print(x=x, y=row_y, string=before, bg=color.black, fg=color.white)
            console.print(
                x=x + len(before),
                y=row_y,
                string=prompt_text,
                bg=color.black,
                fg=color.orange,
            )
        else:
            console.print(x=x, y=row_y, string=line, bg=color.black, fg=color.white)

def render_player_tile_info(console: Console, engine: Engine, x: int = 1, y: int = 0) -> int:
    """Render the names of items or stairs that share the player's tile."""
    names_at_player_location = get_items_and_features_at_location(
        x=engine.player.x, y=engine.player.y, game_map=engine.game_map
    )
    return _render_tile_info_block(
        console,
        engine,
        names_at_player_location,
        x,
        y,
        source="player",
        coords=(engine.player.x, engine.player.y),
    )
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
