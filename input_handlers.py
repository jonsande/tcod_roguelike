# Aquí definimos los tipos de eventos asociados a pulsación de teclas ?¿

from __future__ import annotations
from tcod import libtcodpy
import os
import random
import textwrap
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING, Union

import tcod
import tcod.event
import actions
from actions import (
    Action,
    BumpAction,
    PickupAction,
    WaitAction,
    ToogleLightAction,
    ThrowItemAction,
    ItemAction,
    PassAction,
)
import color
import exceptions
from entity import Chest, Book, SilenceBook, TableContainer, BookShelfContainer
from audio import play_chest_open_sound, play_table_open_sound, play_bookshelf_open_sound
from i18n import _

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Item

from components.ai import Dummy
from components.fighter import BreakableWallFighter
import settings
from settings import DEBUG_MODE

MOVE_KEYS = {
    # Arrow keys.
    #tcod.event.K_UP: (0, -1),
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
    tcod.event.KeySym.HOME: (-1, -1),
    tcod.event.KeySym.END: (-1, 1),
    tcod.event.KeySym.PAGEUP: (1, -1),
    tcod.event.KeySym.PAGEDOWN: (1, 1),
    # Numpad keys.
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_3: (1, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_9: (1, -1),
    # Vi keys.
    tcod.event.KeySym.h: (-1, 0),
    tcod.event.KeySym.j: (0, 1),
    tcod.event.KeySym.k: (0, -1),
    tcod.event.KeySym.l: (1, 0),
    tcod.event.KeySym.y: (-1, -1),
    tcod.event.KeySym.u: (1, -1),
    tcod.event.KeySym.b: (-1, 1),
    tcod.event.KeySym.n: (1, 1),
}

ADJACENT_DELTAS = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
]

def _is_friendly_target(player: "Actor", target: "Actor") -> bool:
    if settings.get_faction_relation(
        getattr(player, "faction", ""),
        getattr(target, "faction", ""),
    ) != "friendly":
        return False
    return settings.resolve_player_attitude(player, target) == "friendly"

WAIT_KEYS = {
    tcod.event.KeySym.PERIOD,
    tcod.event.KeySym.KP_5,
    tcod.event.KeySym.CLEAR,
}

SHIFT_MODIFIERS = (
    tcod.event.Modifier.LSHIFT
    | tcod.event.Modifier.RSHIFT
    | tcod.event.KMOD_LSHIFT
    | tcod.event.KMOD_RSHIFT
    | getattr(tcod.event, "KMOD_SHIFT", 0)
    | getattr(tcod.event.Modifier, "SHIFT", 0)
)

SCANCODE_SLASH = getattr(tcod.event.Scancode, "SLASH", None)
SCANCODE_QUESTION = getattr(tcod.event.Scancode, "QUESTION", None)

CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
}

INTERACT_OPTION_KEYS = {
    tcod.event.KeySym.N1: 0,
    tcod.event.KeySym.N2: 1,
    tcod.event.KeySym.N3: 2,
    tcod.event.KeySym.N4: 3,
    tcod.event.KeySym.N5: 4,
    tcod.event.KeySym.N6: 5,
    tcod.event.KeySym.N7: 6,
    tcod.event.KeySym.N8: 7,
    tcod.event.KeySym.N9: 8,
    tcod.event.KeySym.N0: 9,
    tcod.event.KeySym.KP_1: 0,
    tcod.event.KeySym.KP_2: 1,
    tcod.event.KeySym.KP_3: 2,
    tcod.event.KeySym.KP_4: 3,
    tcod.event.KeySym.KP_5: 4,
    tcod.event.KeySym.KP_6: 5,
    tcod.event.KeySym.KP_7: 6,
    tcod.event.KeySym.KP_8: 7,
    tcod.event.KeySym.KP_9: 8,
    tcod.event.KeySym.KP_0: 9,
}


ActionOrHandler = Union[Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler.
"""

# Variables globales:

# Contador para la mecánica de autoheal (en EventHandler)
counter = 0
satiety_counter = 0

# Contadores para mecánica de efectos temporales:
effect_timer = 0
amount_affected = 0
number_of_turns = None


def _direction_label(dx: int, dy: int) -> str:
    labels = {
        (-1, 0): "W",
        (1, 0): "E",
        (0, -1): "N",
        (0, 1): "S",
        (-1, -1): "NW",
        (-1, 1): "SW",
        (1, -1): "NE",
        (1, 1): "SE",
    }
    return labels.get((dx, dy), f"{dx},{dy}")


def _current_room_name(engine: "Engine") -> Optional[str]:
    player = engine.player
    center = engine.game_map.get_room_center_for_tile(player.x, player.y)
    if not center:
        return None
    return engine.game_map.room_names_by_center.get(center)


def _items_here_sorted(engine: "Engine") -> list["Item"]:
    player = engine.player
    items = [
        item
        for item in engine.game_map.items
        if item.x == player.x and item.y == player.y
    ]
    return sorted(items, key=lambda item: item.name)


def _pickup_action_or_handler(engine: "Engine") -> ActionOrHandler:
    player = engine.player
    items_here = _items_here_sorted(engine)
    if len(items_here) > 1:
        return GroundItemPickupHandler(engine)
    if items_here:
        return PickupAction(player, items_here[0])
    room_name = _current_room_name(engine)
    if room_name == "Blue moss chamber":
        import entity_factories
        moss = entity_factories.blue_moss.spawn(
            engine.game_map, player.x, player.y
        )
        return PickupAction(player, moss)
    return PickupAction(player)


class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, console: tcod.Console) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()


class PopupMessage(BaseEventHandler):
    """Display a popup text window."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def _wrap_lines(self, console: tcod.Console) -> list[str]:
        """Wrap text preserving explicit newlines and returning individual lines."""
        width = console.width - 10
        wrapped_lines: list[str] = []
        for paragraph in self.text.splitlines():
            if not paragraph:
                wrapped_lines.append("")
                continue
            wrapped = textwrap.wrap(
                paragraph,
                width=width,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=False,
            )
            wrapped_lines.extend(wrapped or [""])
        return wrapped_lines

    def on_render(self, console: tcod.Console) -> None:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        # Canales alfa
        console.rgb["fg"] //= 60 # Nivel de opacidad/oscurecimiento de los caracteres del fondo. Con 255 el texto se vuelve blanco. Con 0, negro. Default: 8.
        console.rgb["bg"] //= 8 # Nivel de opacidad/oscurecimiento del fondo de los caracteres del fondo. 255 es blanco. 0, negro. Default: 8.

        lines = self._wrap_lines(console)
        center_x = console.width // 2
        start_y = console.height // 2 - len(lines) // 2

        for i, line in enumerate(lines):
            y = start_y + i
            stripped = line.strip()
            if ":" in stripped and stripped:
                label, value = stripped.split(":", 1)
                label = label.strip()
                value_text = value.strip()
                x = center_x - len(stripped) // 2
                console.print(
                    x,
                    y,
                    label,
                    fg=color.white,
                    bg=color.black,
                    alignment=libtcodpy.LEFT,
                )
                console.print(
                    x + len(label),
                    y,
                    ": ",
                    fg=color.white,
                    bg=color.black,
                    alignment=libtcodpy.LEFT,
                )
                console.print(
                    x + len(label) + 2,
                    y,
                    value_text,
                    fg=color.orange,
                    bg=color.black,
                    alignment=libtcodpy.LEFT,
                )
                continue
            console.print(
                center_x,
                y,
                line,
                fg=color.white, # Color de los caracteres de fondo (su alfa se configura arriba)
                bg=color.black, # Color del fondo de los caracteres del fondo (su alfa se configura arriba)
                alignment=libtcodpy.CENTER,
            )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent


class ConfirmQuitHandler(PopupMessage):
    """Ask the player to confirm saving and exiting the game."""

    def __init__(self, parent_handler: BaseEventHandler):
        super().__init__(
            parent_handler,
            _("Save game and exit? \n\nPress 'y' to confirm or ESC to keep playing."),
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Only quit on explicit confirmation, otherwise stay or go back."""
        if event.sym == tcod.event.KeySym.ESCAPE:
            return self.parent

        if event.sym in (
            tcod.event.KeySym.y,
            getattr(tcod.event.KeySym, "Y", tcod.event.KeySym.y),
        ):
            raise SystemExit()

        return None


class EventHandler(BaseEventHandler):

    """We’re creating a class called EventHandler, which is a subclass 
    of tcod’s EventDispatch class. EventDispatch is a class that 
    allows us to send an event to its proper method based on what 
    type of event it is. Let’s take a look at the methods we’re 
    creating for EventHandler to see a few examples of this."""

    def __init__(self, engine: Engine):
        self.engine = engine

    #def handle_events(self, event: tcod.event.Event) -> None:
    #    self.handle_action(self.dispatch(event))

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        if getattr(self.engine, "tile_info_pause_active", False):
            if isinstance(event, tcod.event.KeyDown):
                self.engine.dismiss_tile_info_pause()
                return self
            if not isinstance(event, tcod.event.Quit):
                return self

        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            # A valid action was performed.
            if not self.engine.player.is_alive:
                # The player was killed sometime during or after the action.
                return GameOverEventHandler(self.engine)
            elif self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)
            return MainGameEventHandler(self.engine)  # Return to the main handler.
        return self

    # Para lo que interesa esto es lo que mueve el turno:
    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.

        Returns True if the action will advance a turn.
        """        
        
        if action is None:
            return False

        action = self._maybe_scramble_player_action(action)
        actor = getattr(action, "entity", None)
        is_wait_action = isinstance(action, WaitAction)

        if actor is self.engine.player and getattr(self.engine.player.fighter, "is_player_paralyzed", False):
            if not is_wait_action:
                self.engine.message_log.add_message(
                    "You are paralyzed and cannot act!",
                    color.impossible,
                )
                return False

        if actor is self.engine.player and not is_wait_action:
            self.engine.reset_listen_state()
            self.engine.reset_listen_mode_counter()
            self.engine.exit_listen_mode()

        profiler = getattr(self.engine, "profiler", None)

        if profiler:
            profiler.start_phase("player_action")
        try:
            action.perform()
        except exceptions.Impossible as exc:
            if profiler:
                profiler.end_phase("player_action")
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False  # Skip enemy turn on exceptions.

        fighter = getattr(actor, "fighter", None)
        if fighter:
            fighter.handle_post_action(is_wait_action, action.__class__.__name__)
        
        self.engine.extra_turn_manager()

        if actor is self.engine.player:
            self.engine.player.fighter.advance_player_confusion()
            self.engine.player.fighter.advance_player_paralysis()
            self.engine.player.fighter.advance_player_petrification()

        if profiler:
            profiler.end_phase("player_action")

        # Move THE CLOCK
        self.engine.clock()

        self.engine.restore_time_pts()

        # ¿What time is it?
        now = self.engine.what_time_it_is()
        print(f"\n{color.bcolors.BOLD}{color.bcolors.WARNING}=============== Turn: {now} ==============={color.bcolors.ENDC}\n")

        if profiler:
            profiler.start_phase("enemy_turns")
        self.engine.handle_enemy_turns()
        if profiler:
            profiler.end_phase("enemy_turns")

        if profiler:
            profiler.start_phase("fov")
        self.engine.update_fov()
        if profiler:
            profiler.end_phase("fov")

        # Autoheal, Hunger, Poison
        if profiler:
            profiler.start_phase("upkeep")
        self.engine.autohealmonsters()
        self.engine.update_hunger()
        self.engine.update_poison()
        self.engine.update_fire()

        # Fortify indicator
        #self.engine.update_fortify_indicator()

        # Melee indicator
        # ToDo: estaría bien limitar la cantidad de veces que se ejecuta esto,
        # por ejemplo: que si no hay enemigos visibles alrededor no se ejecute,
        # pues hay que tener en cuenta que itera sobre todos los actores, cada
        # cada vez que se ejecuta.
        self.engine.update_melee_indicator()

        # Actualizamos efectos temporales
        self.engine.update_temporal_effects()
        self.engine.update_silence_effects()

        # Monstruos que entran por las escaleras
        self.engine.spawn_monsters_upstairs()

        # Restore Energy Points for all actors (Speed System)
        #self.engine.restore_energy_all()

        # TODO: evitar que la debris o los cadáveres puedan tapar el sprite de
        # las escaleras de subida o de bajada.
        # BugFix provisional:
        # Colocar escaleras para que no queden ocultas por la debris
        self.engine.bugfix_downstairs()
        self.engine.bugfix_upstairs()

        if profiler:
            profiler.end_phase("upkeep")
            profiler.end_turn(self.engine.turn)

        return True

    def _maybe_scramble_player_action(self, action: Action) -> Action:
        player = self.engine.player
        fighter = player.fighter
        if getattr(action, "_confusion_override", False):
            return action
        if action.entity is not player or not fighter.is_player_confused:
            return action
        if isinstance(action, (WaitAction, PassAction)):
            return action

        self.engine.message_log.add_message(
            "In your confusion you act unpredictably!", color.impossible
        )

        if isinstance(action, ItemAction):
            random_action = self._random_confused_item_action(action)
            if random_action:
                random_action._confusion_override = True
                return random_action

        random_action = self._random_confused_movement_action()
        random_action._confusion_override = True
        return random_action

    def _random_confused_movement_action(self) -> Action:
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
        dx, dy = random.choice(directions)
        return BumpAction(self.engine.player, dx, dy)

    def _random_confused_item_action(self, original_action: ItemAction) -> Optional[Action]:
        inventory = self.engine.player.inventory
        usable_items = [item for item in inventory.items if getattr(item, "consumable", None)]
        if not usable_items:
            return None
        item = random.choice(usable_items)
        target_xy = getattr(original_action, "target_xy", (self.engine.player.x, self.engine.player.y))
        return ItemAction(self.engine.player, item, target_xy)
    

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if hasattr(event, "position") and self.engine.game_map.in_bounds(*event.position):
            self.engine.mouse_location = event.position

    #def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
    #    raise SystemExit()
    
    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)


class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.KeySym.LSHIFT,
            tcod.event.KeySym.RSHIFT,
            tcod.event.KeySym.LCTRL,
            tcod.event.KeySym.RCTRL,
            tcod.event.KeySym.LALT,
            tcod.event.KeySym.RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.

        By default this returns to the main event handler.
        """
        return MainGameEventHandler(self.engine)


class ConfirmFriendlyAttackHandler(AskUserEventHandler):
    """Ask the player to confirm attacking a friendly creature."""

    def __init__(
        self,
        engine: Engine,
        parent_handler: BaseEventHandler,
        attacker: Actor,
        target: Actor,
        action_factory: Callable[[], Action],
        target_position: Optional[Tuple[int, int]] = None,
    ):
        super().__init__(engine)
        self.parent = parent_handler
        self.attacker = attacker
        self.target = target
        self._action_factory = action_factory
        self._target_position = target_position
        self.text = _(
            "Attack {target}? This will turn them hostile. \n\nPress 'y' to confirm or ESC to cancel."
        ).format(target=self.target.name)

    def _wrap_lines(self, console: tcod.Console) -> list[str]:
        """Wrap text preserving explicit newlines and returning individual lines."""
        width = console.width - 10
        wrapped_lines: list[str] = []
        for paragraph in self.text.splitlines():
            if not paragraph:
                wrapped_lines.append("")
                continue
            wrapped = textwrap.wrap(
                paragraph,
                width=width,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=False,
            )
            wrapped_lines.extend(wrapped or [""])
        return wrapped_lines

    def on_render(self, console: tcod.Console) -> None:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        console.rgb["fg"] //= 60
        console.rgb["bg"] //= 8

        lines = self._wrap_lines(console)
        center_x = console.width // 2
        start_y = console.height // 2 - len(lines) // 2

        for i, line in enumerate(lines):
            y = start_y + i
            console.print(
                center_x,
                y,
                line,
                fg=color.white,
                bg=color.black,
                alignment=libtcodpy.CENTER,
            )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Only proceed on explicit confirmation."""
        if event.sym == tcod.event.KeySym.ESCAPE:
            return self.parent
        if event.sym in (
            tcod.event.KeySym.y,
            getattr(tcod.event.KeySym, "Y", tcod.event.KeySym.y),
            tcod.event.KeySym.RETURN,
            tcod.event.KeySym.KP_ENTER,
        ):
            if self._should_attack():
                self._execute_action()
            return self.parent
        return None

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """Left click confirms a selection."""
        if event.button == tcod.event.MouseButton.LEFT and self._should_attack():
            self._execute_action()
        return self.parent

    def _execute_action(self) -> None:
        action = self._action_factory()
        if not action:
            return
        handler = self.parent if isinstance(self.parent, EventHandler) else self
        handler.handle_action(action)

    def _should_attack(self) -> bool:
        """Ensure the target is still valid before confirming the attack."""
        if getattr(self.attacker, "gamemap", None) is not self.engine.game_map:
            return False
        fighter = getattr(self.target, "fighter", None)
        if not fighter or getattr(fighter, "hp", 0) <= 0:
            return False
        if self._target_position and (self.target.x, self.target.y) != self._target_position:
            return False
        if getattr(self.target, "gamemap", None) is not self.engine.game_map:
            return False
        return True


class CombatControlHandler(AskUserEventHandler):
    TITLE = "MONSTER INFO"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        layout = settings.HUD_LAYOUT["monster_panel"]
        width = min(layout["width"], console.width)
        height = min(layout["height"], console.height)
        y = min(layout["y"], max(0, console.height - height))

        # Place panel on the opposite side of the player for readability.
        if self.engine.player.x <= layout["player_threshold"]:
            x = min(layout["x_right"], max(0, console.width - width))
        else:
            x = max(0, min(layout["x_left"], console.width - width))

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            # Para que el fondo sea transparente o no:
            clear=True,
            # fg=(99,238,99),
            # bg=(2,45,0),
            fg=(150,150,150),
            bg=(20,20,20),
        )

        #console.print(
        #    x=2, y=2, string="LEVEL:", fg=(99,238,99)
        #)

        monsters_list = []

        for i in self.engine.game_map.actors:
            if (
                self.engine.game_map.visible[i.x, i.y]
                and i != self.engine.player
                and not isinstance(i.fighter, BreakableWallFighter)
            ):
                monsters_list.append(i)
    
        sorted_monsters_list = sorted(monsters_list, key=lambda e: self.engine.player.distance(e.x, e.y))

        #number_of_monsters = len(monsters_list)
        #print(number_of_monsters)

        counter_mons = 0
        counter_lines = 0
        for i, e in enumerate(sorted_monsters_list):
            counter_mons += 1
            name = e.name.upper()
            distance = int(self.engine.player.distance(e.x, e.y))
            stamina = f"{e.fighter.stamina}"
            defense = f"{e.fighter.defense}"
            armor_value = f"{e.fighter.armor_value}"
            hp = f"{e.fighter.hp}"
            aggravated = f"{e.fighter.aggravated}"
            strength = f"({e.fighter.strength} + {e.fighter.weapon_dmg_info} * {e.fighter.weapon_proficiency}" # + {e.fighter.no_weapon_dmg_info})

            # if DEBUG_MODE:
            #     print("DEBUG: e.name: ", e.name)
            #     print("DEBUG: e.fighter.aggravated: ", e.fighter.aggravated)

            if isinstance(e.ai, Dummy) == False:
                if e.fighter.aggravated == True:
                    string=f"{name} (Distance: {distance}) (!) HP:{e.fighter.hp}\n SP:  DEF:  DMG:        THit:  AV:"
                else:
                    string=f"{name} (Distance: {distance}) HP:{e.fighter.hp}\n SP:  DEF:  DMG:        THit:  AV:"

                console.print(
                    x=x+1, 
                    y=1+i+counter_mons +counter_lines, 
                    string=string,
                )

                console.print(x + 5, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.stamina}", fg=color.blue)
                console.print(x + 11, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.defense}", fg=color.orange)
                console.print(x + 17, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.strength}+{e.fighter.weapon_dmg_info}", fg=color.red)
                console.print(x + 30, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.to_hit}", fg=color.orange)
                console.print(x + 35, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.armor_value}", fg=color.orange)
                #console.print(x + 40, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.hp}", fg=color.orange)
                counter_lines += 1
                #self.engine.player.fighter.armor_value
                #console.print(x=x+1, y=1+i+2, string=f"ESTAMINA: {e.fighter.stamina}")
  


                    
        #console.print(x=x + 2, y=n+1, string=f"{i.name}", fg=(99,238,99))
        #print(f"{monsters_list}")

        """
        if distance <= 1:
            return MeleeAction(self.entity, dx, dy).perform()

        self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()"""


class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Character Information"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        #if self.engine.player.x <= 30:
        #    x = 40
        #else:
        #    x = 0

        x = 1
        y = 1

        #width = len(self.TITLE) + 35
        width = 78

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=35,
            title=self.TITLE,
            # Para que el fondo sea transparente o no:
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(
            x=2, y=3, string="NAME: ",  fg=color.blue,
        )
        console.print(
            x=9, y=3, string=f"{self.engine.player.name}",  fg=color.descend
        )

        console.print(
            x=2, 
            y=5, 
            string="TO HIT CHANCE: ", fg=color.blue,
        )
        console.print(
            x=17, 
            y=5, 
            string=f"1D6 + ", fg=color.orange,
        )
        console.print(
            x=23, 
            y=5, 
            string=f"({self.engine.player.fighter.to_hit} * {self.engine.player.fighter.weapon_proficiency}) VS Target DV", fg=color.orange,
        )
    
        console.print(
            x=2, 
            y=7, 
            string=f"STRENGTH: ", fg=color.blue,
        )
        console.print(
            x=12, 
            y=7, 
            string=f"{self.engine.player.fighter.strength}", fg=color.orange,
        )
        console.print(
            x=15, 
            y=7, 
            string=f"WEAPON DMG: ", fg=color.blue,
        )
        console.print(
            x=27, 
            y=7, 
            string=f"{self.engine.player.fighter.weapon_dmg_info}", fg=color.orange,
        )
        console.print(
            x=27 + len(self.engine.player.fighter.weapon_dmg_info) + 2,
            y=7, 
            string=f"BONUS DMG: ", fg=color.blue
        )
        console.print(
            x=27 + len(self.engine.player.fighter.weapon_dmg_info) + 13, 
            y=7, 
            # TODO: comprobar que el cálculo de non_weapon_dmg_bonus es correcto:
            # debería ser la suma de los bonus de todas las piezas equipadas menos
            # el bonus del arma.
            string=f"{self.engine.player.fighter.non_weapon_dmg_bonus}", fg=color.orange,
        )
        console.print(
            x=27 + len(self.engine.player.fighter.weapon_dmg_info) + 16,
            y=7,
            string=f"PROFICIENCY: ", fg=color.blue,
        )

        console.print(
            x=43  + len(self.engine.player.fighter.weapon_dmg_info) + 13,
            y=7,
            string=f"{self.engine.player.fighter.weapon_proficiency}", fg=color.orange,
        )
        console.print(
            x=2, 
            y=9, 
            string="DEFENSE: ", fg=color.blue
        )
        console.print(
            x=11, 
            y=9,
            string=f"{self.engine.player.fighter.defense}", fg=color.orange,
        )
        console.print(
            x=13, 
            y=9, 
            string="ARMOR VALUE: ", fg=color.blue,
        )
        console.print(
            x=26, 
            y=9, 
            string=f"{self.engine.player.fighter.armor_value}", fg=color.orange,
        )
        console.print(
            x=2, 
            y=11, 
            string="STEALTH: ", fg=color.blue,
        )
        console.print(
            x=11, 
            y=11, 
            string=f"{self.engine.player.fighter.stealth}", fg=color.orange,
        )
        console.print(
            x=14, 
            y=11, 
            string="LUCK: ", fg=color.blue,
        )
        console.print(
            x=20, 
            y=11, 
            string=f"{self.engine.player.fighter.luck}", fg=color.orange,
        )

        console.print(
            x=2, 
            y=20, 
            string=f"DAMAGE FORMULA: "
        )
        console.print(
            x=3, 
            y=21, 
            string=f"(STRENGTH + WEAPON DMG + BONUS DMG) * PROFICIENCY - ARMOR VALUE ",
        )
        console.print(
            x=2, 
            y=23, 
            string=f"TO HIT FORMULA: "
        )
        console.print(
            x=3, 
            y=24, 
            string=f"1d6 + (TO-HIT * PROFICIENCY) VS DEFENSE VALUE",
        )


class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        #if self.engine.player.x <= 30:
        #    x = 40
        #else:
        #    x = 0

        x = 1
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            #width=45,
            width=78,
            height=11,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=2, string="Congratulations! You level up!")
        console.print(x=x + 1, y=3, string="Select an attribute to increase.")

        console.print(
            x=x + 1,
            y=5,
            string=f"a) Base Stealth + 1 (current: {self.engine.player.fighter.stealth})",
        )
        """
        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {self.engine.player.fighter.max_hp})",
        )
        """
        console.print(
            x=x + 1,
            y=6,
            string=f"b) To Hit mod +1 (current {self.engine.player.fighter.to_hit})",
        )
        console.print(
            x=x + 1,
            y=7,
            string=f"c) Parry (defense) +1 (current: {self.engine.player.fighter.defense})",
        )
        console.print(
            x=x + 1,
            y=8,
            string=f"d) Max stamina +1 (current: {self.engine.player.fighter.max_stamina})",
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 3:
            if index == 0:
                #player.level.increase_max_hp()
                player.level.increase_stealth()
            elif index == 1:
                player.level.increase_to_hit()
            elif index == 2:
                player.level.increase_defense()
            else:
                player.level.increase_stamina()
                
        else:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)

            return None

        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """
        Don't allow the player to click to exit the menu, like normal.
        """
        return None


class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"

    def on_render(self, console: tcod.Console) -> None:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)
        entries = self._inventory_entries()

        height = len(entries) + 2

        if height <= 3:
            height = 3

        #if self.engine.player.x <= 30:
        #    x = 40
        #else:
        #    x = 0

        x = 1
        y = 1

        #width = len(self.TITLE) + 35
        width = 78

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if entries:

            for i, (item_name, items, is_equipped) in enumerate(entries):
                count = len(items)
                item = items[0]  # Use the first item for properties

                # Esto asigna una tecla a cada entrada
                item_key = chr(ord("a") + i)

                item_string = f"({item_key}) {item_name}"

                if count > 1:
                    item_string = f"{item_string} ({count})"

                if is_equipped:
                    item_string = f"{item_string} (E)"

                text_color = color.orange if is_equipped else color.white
                console.print(x + 1, y + i + 1, item_string, fg=text_color)

        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 26:
            entries = self._inventory_entries()
            try:
                item_name, items, _ = entries[index]
                selected_item = items[0]  # Select the first item of the group
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[Action]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()

    def _inventory_entries(
        self,
        filter_fn: Optional[Callable[[Item], bool]] = None,
        skip: Optional[Item] = None,
    ):
        """Return sorted entries for inventory listing, splitting equipped items."""
        player = self.engine.player
        return player.inventory.get_entries(
            equipment=player.equipment,
            filter_fn=filter_fn,
            skip=skip,
        )


class BookOptionsHandler(AskUserEventHandler):
    TITLE = "Opciones del libro"

    def __init__(self, engine: Engine, book: Book):
        super().__init__(engine)
        self.book = book

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        x = 1
        y = 1
        width = 78
        height = 7

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=2, string=f"Libro: {self.book.name}")
        console.print(x=x + 1, y=3, string="a) Leer el libro")
        console.print(x=x + 1, y=4, string="b) Leerlo en voz alta")
        console.print(x=x + 1, y=5, string="c) Desequiparlo")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.a

        if key == tcod.event.KeySym.ESCAPE:
            return super().ev_keydown(event)

        if index == 0:
            return PopupMessage(self, self.book.read_message())
        if index == 1:
            message = self.book.read_aloud(self.engine.player)
            if message:
                self.engine.message_log.add_message(message, color.orange)
            if isinstance(self.book, SilenceBook) and getattr(self.book, "_silence_spawn_pending", False):
                self.book._silence_spawn_pending = False
                self.engine.maybe_spawn_silence_creature(
                    self.engine.player,
                    target_id_name=getattr(self.book, "id_name", None),
                )
            return super().ev_keydown(event)
        if index == 2:
            return actions.BookToggleEquipAction(self.engine.player, self.book)

        self.engine.message_log.add_message("Invalid entry.", color.invalid)
        return None


class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if isinstance(item, Book):
            if self.engine.player.equipment.item_is_equipped(item):
                return BookOptionsHandler(self.engine, item)
            return actions.BookToggleEquipAction(self.engine.player, item)
        if item.consumable:
            # Return the action for the selected item.
            return item.consumable.get_action(self.engine.player)
        elif item.equippable:
            activator = getattr(item.equippable, "get_activation_handler", None)
            if callable(activator) and self.engine.player.equipment.item_is_equipped(item):
                handler = activator(self.engine.player)
                if handler:
                    return handler
            return actions.EquipAction(self.engine.player, item)
        else:
            return None


class InventoryIdentifyHandler(InventoryEventHandler):
    """Handle picking an unidentified item to reveal with a scroll."""

    TITLE = "Elige un objeto sin identificar"

    def __init__(self, engine: Engine, scroll: Item):
        super().__init__(engine)
        self.scroll = scroll

    def _unidentified_entries(self):
        return self._inventory_entries(
            filter_fn=lambda item: not getattr(item, "identified", False)
            and item is not self.scroll,
        )

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        entries = self._unidentified_entries()
        height = max(3, len(entries) + 2)
        x = 1
        y = 1
        width = 78

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if entries:
            for i, (item_name, items, is_equipped) in enumerate(entries):
                item_key = chr(ord("a") + i)
                item_string = f"({item_key}) {item_name}"
                if len(items) > 1:
                    item_string = f"{item_string} ({len(items)})"
                if is_equipped:
                    item_string = f"{item_string} (E)"
                text_color = color.orange if is_equipped else color.white
                console.print(x + 1, y + i + 1, item_string, fg=text_color)
        else:
            console.print(x + 1, y + 1, "(Sin objetos sin identificar)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.a
        entries = self._unidentified_entries()

        if 0 <= index < len(entries):
            try:
                _, items, _ = entries[index]
                selected_item = items[0]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        return actions.IdentifyItemAction(self.engine.player, self.scroll, item)


class InventoryRemoveCurseHandler(InventoryEventHandler):
    """Handle picking any item to attempt to remove a curse with a scroll."""

    TITLE = "Elige un objeto para romper la maldición"

    def __init__(self, engine: Engine, scroll: Item):
        super().__init__(engine)
        self.scroll = scroll

    def _item_entries(self):
        return self._inventory_entries(filter_fn=lambda item: item is not self.scroll)

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        entries = self._item_entries()
        height = max(3, len(entries) + 2)
        x = 1
        y = 1
        width = 78

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if entries:
            for i, (item_name, items, is_equipped) in enumerate(entries):
                item_key = chr(ord("a") + i)
                item_string = f"({item_key}) {item_name}"
                if len(items) > 1:
                    item_string = f"{item_string} ({len(items)})"
                if is_equipped:
                    item_string = f"{item_string} (E)"
                text_color = color.orange if is_equipped else color.white
                console.print(x + 1, y + i + 1, item_string, fg=text_color)
        else:
            console.print(x + 1, y + 1, "(Inventario vacío)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.a
        entries = self._item_entries()

        if 0 <= index < len(entries):
            try:
                _, items, _ = entries[index]
                selected_item = items[0]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        return actions.RemoveCurseItemAction(self.engine.player, self.scroll, item)
        
    
class InventoryThrowHandler(InventoryEventHandler):
    """Handler for throwing items."""

    TITLE = "Select an item to throw"

    def _inventory_entries(
        self,
        filter_fn: Optional[Callable[[Item], bool]] = None,
        skip: Optional[Item] = None,
    ):
        def combined(item: Item) -> bool:
            if getattr(item, "projectile_type", None):
                return False
            return filter_fn(item) if filter_fn else True

        return super()._inventory_entries(filter_fn=combined, skip=skip)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """User selects an item to throw, then select target position."""
        player = self.engine.player

        def _throw_action(pos: Tuple[int, int]) -> Optional[ActionOrHandler]:
            target = self.engine.game_map.get_actor_at_location(*pos)
            action_factory = lambda: ThrowItemAction(player, item, pos)
            if target and _is_friendly_target(player, target):
                return ConfirmFriendlyAttackHandler(
                    self.engine,
                    MainGameEventHandler(self.engine),
                    player,
                    target,
                    action_factory,
                    target_position=pos,
                )
            return action_factory()

        return SingleRangedAttackHandler(self.engine, _throw_action)


class InventoryExamineHandler(InventoryEventHandler):
    """Handle examine an inventory item."""

    TITLE = "Select an item to examine"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        return PopupMessage(self, f"{item.full_info()}")
        

class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Drop this item."""
        return actions.DropItem(self.engine.player, item)


class GroundItemPickupHandler(AskUserEventHandler):
    """Handler to pick a specific item from the ground when multiple are present."""

    TITLE = "Objetos en el suelo"

    def _items_here(self) -> list[Item]:
        px, py = self.engine.player.x, self.engine.player.y
        items_here = [
            item for item in self.engine.game_map.items if item.x == px and item.y == py
        ]
        return sorted(items_here, key=lambda item: item.name)

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        items = self._items_here()
        height = max(3, len(items) + 2)
        width = 40
        x = 1
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if not items:
            console.print(x + 1, y + 1, "(Vacío)")
            return

        for index, item in enumerate(items):
            key = chr(ord("a") + index)
            console.print(x + 1, y + index + 1, f"({key}) {item.name}")

    def _pickup_item_and_choose_next_handler(self, item: Item) -> BaseEventHandler:
        """Pick the given item, advance the turn, and decide which handler stays active."""
        action_performed = self.handle_action(PickupAction(self.engine.player, item))

        if action_performed:
            if not self.engine.player.is_alive:
                return GameOverEventHandler(self.engine)
            if self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)

        if self._items_here():
            return self
        return MainGameEventHandler(self.engine)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym

        if key in {
            tcod.event.KeySym.ESCAPE,
            tcod.event.KeySym.RETURN,
            tcod.event.KeySym.KP_ENTER,
        }:
            return self.on_exit()

        items = self._items_here()
        index = key - tcod.event.KeySym.a
        if 0 <= index < len(items):
            return self._pickup_item_and_choose_next_handler(items[index])
        return None


class ChestLootHandler(AskUserEventHandler):
    """Handler to inspect and loot an opened chest or table."""

    TITLE = "Contenido"

    def __init__(self, engine: Engine, chest: Chest):
        super().__init__(engine)
        self.chest = chest
        if self.chest.open():
            is_table = isinstance(self.chest, TableContainer)
            is_bookshelf = isinstance(self.chest, BookShelfContainer)
            if is_table:
                play_table_open_sound()
            elif is_bookshelf:
                play_bookshelf_open_sound()
            else:
                play_chest_open_sound()
            if is_bookshelf:
                msg = "You search the bookshelf."
            elif is_table:
                msg = "You search the table."
            else:
                msg = "You open the chest."
            self.engine.message_log.add_message(msg, color.white)
        # Ajusta el título según el contenedor.
        if isinstance(self.chest, BookShelfContainer):
            self.TITLE = "Contenido de la estantería"
        elif isinstance(self.chest, TableContainer):
            self.TITLE = "Contenido de la mesa"
        else:
            self.TITLE = "Contenido del cofre"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        items = list(self.chest.inventory.items)
        height = max(3, len(items) + 2)
        width = 40
        x = 1
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if not items:
            console.print(x + 1, y + 1, "(Vacío)")
            return

        for index, item in enumerate(items):
            key = chr(ord("a") + index)
            console.print(x + 1, y + index + 1, f"({key}) {item.name}")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        items = list(self.chest.inventory.items)

        if key in {
            tcod.event.KeySym.ESCAPE,
            tcod.event.KeySym.RETURN,
            tcod.event.KeySym.KP_ENTER,
        }:
            return self.on_exit()

        index = key - tcod.event.KeySym.a
        if 0 <= index < len(items):
            self._take_item(items[index])
        return None

    def _take_item(self, item: Item) -> None:
        inventory = self.engine.player.inventory
        if len(inventory.items) >= inventory.capacity:
            self.engine.message_log.add_message("Your inventory is full.", color.impossible)
            return
        try:
            self.chest.inventory.items.remove(item)
        except ValueError:
            return
        inventory.items.append(item)
        item.parent = inventory
        item_key = inventory.entry_letter(item, equipment=self.engine.player.equipment)
        suffix = f" ({item_key})" if item_key else ""
        self.engine.message_log.add_message(
            f"You take the {item.name}{suffix}.", color.white
        )

    def on_exit(self) -> Optional[ActionOrHandler]:
        return actions.OpenChestAction(self.engine.player, self.chest)


class InteractionMenuHandler(AskUserEventHandler):
    """Modal interaction menu for context-sensitive environment actions."""

    TITLE = "Interacciones"

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self._options = self._build_options()

    def _build_options(self) -> List[Tuple[str, Callable[[], ActionOrHandler]]]:
        options: List[Tuple[str, Callable[[], ActionOrHandler]]] = []
        player = self.engine.player

        if getattr(player.fighter, "is_player_paralyzed", False):
            return options

        gamemap = self.engine.game_map
        if gamemap.is_downstairs_location(player.x, player.y):
            options.append(("Bajar escaleras", lambda: actions.TakeStairsAction(player)))
        if gamemap.upstairs_location and (
            player.x,
            player.y,
        ) == gamemap.upstairs_location:
            options.append(("Subir escaleras", lambda: actions.TakeStairsAction(player)))

        for dx, dy in ADJACENT_DELTAS:
            dest_x = player.x + dx
            dest_y = player.y + dy
            if not gamemap.in_bounds(dest_x, dest_y):
                continue
            blocker = gamemap.get_blocking_entity_at_location(dest_x, dest_y)
            if isinstance(blocker, (Chest, TableContainer, BookShelfContainer)):
                direction = _direction_label(dx, dy)
                label = f"Abrir {blocker.name} ({direction})"
                options.append(
                    (
                        label,
                        lambda chest=blocker: ChestLootHandler(self.engine, chest),
                    )
                )
                continue
            fighter = getattr(blocker, "fighter", None)
            if fighter and hasattr(fighter, "set_open") and not getattr(fighter, "is_open", False):
                direction = _direction_label(dx, dy)
                label = f"Abrir puerta ({direction})"
                options.append(
                    (label, lambda dx=dx, dy=dy: BumpAction(player, dx, dy))
                )

        has_open_door = any(
            gamemap.in_bounds(player.x + dx, player.y + dy)
            and gamemap.is_open_door(player.x + dx, player.y + dy)
            for dx, dy in ADJACENT_DELTAS
        )
        if has_open_door:
            options.append(
                ("Cerrar puerta cercana", lambda: actions.CloseDoorAction(player))
            )

        items_here = _items_here_sorted(self.engine)
        if items_here:
            options.append(("Coger objetos", lambda: _pickup_action_or_handler(self.engine)))
        else:
            if _current_room_name(self.engine) == "Blue moss chamber":
                options.append(("Recoger musgo", lambda: _pickup_action_or_handler(self.engine)))

        return options

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        height = max(3, len(self._options) + 2)
        width = 78
        x = 1
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if not self._options:
            console.print(x + 1, y + 1, "(Sin opciones disponibles)")
            return

        for index, (label, _) in enumerate(self._options):
            key_num = index + 1
            key_label = "0" if key_num == 10 else str(key_num)
            console.print(x + 1, y + index + 1, f"({key_label}) {label}")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym

        if key in {
            tcod.event.KeySym.ESCAPE,
            tcod.event.KeySym.RETURN,
            tcod.event.KeySym.KP_ENTER,
        }:
            return self.on_exit()

        if key in INTERACT_OPTION_KEYS:
            index = INTERACT_OPTION_KEYS[key]
            if 0 <= index < len(self._options):
                _, action_factory = self._options[index]
                return action_factory()
            self.engine.message_log.add_message("Invalid entry.", color.invalid)
            return None

        return None


class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""

    def __init__(self, engine: Engine):
        """Sets the cursor to the player when this handler is constructed."""
        super().__init__(engine)
        player = self.engine.player
        engine.mouse_location = player.x, player.y
        self._cursor_reset = False

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Force exit after the cursor has been reset (e.g., after a failed action)."""
        handler = super().handle_events(event)
        cursor_reset = self._cursor_reset
        self._cursor_reset = False
        if handler is self and cursor_reset:
            return MainGameEventHandler(self.engine)
        return handler

    def _reset_mouse_location(self) -> None:
        """Return the cursor to the player's current tile."""
        player = self.engine.player
        # Esto si quisiéramos que el cursor volviera a la posición del jugador.
        #self.engine.mouse_location = player.x, player.y
        # Esto para que el cursor vuelva a la esquina superior izquierda.
        self.engine.mouse_location = 0, 0
        self._cursor_reset = True

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        # Esto renderiza el cursor en la posición indicada
        x, y = self.engine.mouse_location
        console.rgb["bg"][x, y] = color.white
        console.rgb["fg"][x, y] = color.black

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1  # Holding modifier keys will speed up key movement.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20

            x, y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Clamp the cursor index to the map size.
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self._select_index(*self.engine.mouse_location)
        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """Left click confirms a selection."""
        if hasattr(event, "position") and self.engine.game_map.in_bounds(*event.position):
            if event.button == 1:
                return self._select_index(*event.position)
        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()

    def _select_index(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Invoke index selection and ensure the cursor resets afterwards."""
        try:
            return self.on_index_selected(x, y)
        finally:
            self._reset_mouse_location()

    def on_exit(self) -> Optional[ActionOrHandler]:
        self._reset_mouse_location()
        return super().on_exit()


class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""

    def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
        """Return to main handler."""
        self._reset_mouse_location()
        return MainGameEventHandler(self.engine)

    def on_exit(self) -> Optional[ActionOrHandler]:
        self._reset_mouse_location()
        return super().on_exit()


class ExamineScreenEventHandler(SelectIndexHandler):
    TITLE = "Examine Information"
    
    
#class FireRangedHandler(SelectIndexHandler):
#    TITLE = "Select a target"
        

class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""

    def __init__(
        self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[Action]]
    ):
        super().__init__(engine)

        self.callback = callback

    def _draw_target_path(self, console: tcod.Console) -> None:
        player = self.engine.player
        x, y = self.engine.mouse_location
        gamemap = self.engine.game_map
        if not gamemap.in_bounds(x, y):
            return
        line = tcod.los.bresenham((player.x, player.y), (x, y)).tolist()
        for lx, ly in line[1:]:
            if not gamemap.in_bounds(lx, ly):
                break
            if not gamemap.visible[lx, ly]:
                continue
            console.rgb["bg"][lx, ly] = color.target_path

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        self._draw_target_path(console)
        x, y = self.engine.mouse_location
        console.rgb["bg"][x, y] = color.white
        console.rgb["fg"][x, y] = color.black

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))


class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting an area within a given radius. Any entity within the area will be affected."""

    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[Action]],
    ):
        super().__init__(engine)

        self.radius = radius
        self.callback = callback

    def _draw_target_path(self, console: tcod.Console) -> None:
        player = self.engine.player
        x, y = self.engine.mouse_location
        gamemap = self.engine.game_map
        if not gamemap.in_bounds(x, y):
            return
        line = tcod.los.bresenham((player.x, player.y), (x, y)).tolist()
        for lx, ly in line[1:]:
            if not gamemap.in_bounds(lx, ly):
                break
            if not gamemap.visible[lx, ly]:
                continue
            console.rgb["bg"][lx, ly] = color.target_path

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        self._draw_target_path(console)
        x, y = self.engine.mouse_location
        console.rgb["bg"][x, y] = color.white
        console.rgb["fg"][x, y] = color.black

        x, y = self.engine.mouse_location

        # Draw-frame call disabled to avoid revealing scroll identity before identification.
        # console.draw_frame(
        #     x=x - self.radius - 1,
        #     y=y - self.radius - 1,
        #     width=self.radius ** 2,
        #     height=self.radius ** 2,
        #     fg=color.red,
        #     clear=False,
        # )

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))


class MainGameEventHandler(EventHandler):

    def _is_help_key(self, key: int, modifier: int, scancode: Optional[int]) -> bool:
        """Return True if the key combination should open the help screen."""
        question_sym = getattr(tcod.event.KeySym, "QUESTION", None)
        question_sym_alt = getattr(tcod.event.KeySym, "QUESTIONMARK", None)
        shift_down = bool(modifier & SHIFT_MODIFIERS)

        if key in (question_sym, question_sym_alt):
            return True

        if key == tcod.event.KeySym.SLASH and shift_down:
            return True

        # Some layouts may send the ASCII code directly.
        if isinstance(key, int) and key == ord("?"):
            return True

        if scancode in (SCANCODE_QUESTION, SCANCODE_SLASH) and shift_down:
            return True

        # Extra fallback: F1 always opens help.
        if key == tcod.event.KeySym.F1:
            return True

        return False

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:

        """This method will receive key press events, and return either an 
        Action subclass, or None, if no valid key was pressed."""

        # 'action' is the variable that will hold whatever subclass of Action 
        # we end up assigning it to. If no valid key press is found, it will 
        # remain set to None. We’ll return it either way.
        action: Optional[Action]= None

        key = event.sym
        modifier = event.mod
        shift_down = bool(modifier & SHIFT_MODIFIERS)
        scancode = getattr(event, "scancode", None)

        player = self.engine.player

        # Moverse
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            chest_handler = self._maybe_open_chest(player, dx, dy)
            if chest_handler:
                return chest_handler
            confirm_handler = self._maybe_confirm_friendly_attack(player, dx, dy)
            if confirm_handler:
                return confirm_handler
            action = BumpAction(player, dx, dy)
        # Bajar escaleras
        elif key == tcod.event.KeySym.SPACE:
            return InteractionMenuHandler(self.engine)
        # Pasar turno
        elif key in WAIT_KEYS:
            action = WaitAction(player)
        # Salir del juego
        elif key == tcod.event.KeySym.ESCAPE:
            return ConfirmQuitHandler(self)
        # Ayuda y documentación (antes de SLASH para no chocar con "look")
        elif self._is_help_key(key, modifier, scancode):
            return HelpScreenEventHandler(self.engine)
        # Ver el historial
        elif key == tcod.event.KeySym.v:
            return HistoryViewer(self.engine, parent_handler=self)
        # Coger objeto
        elif key == tcod.event.KeySym.g:
            return _pickup_action_or_handler(self.engine)
        # Activar item del inventario
        elif key == tcod.event.KeySym.a:
            return InventoryActivateHandler(self.engine)
        # Inspeccionar item del inventario
        elif key == tcod.event.KeySym.i:
            return InventoryExamineHandler(self.engine)
        # Soltar objeto
        elif key == tcod.event.KeySym.d:
            return InventoryDropHandler(self.engine)
        # Ver ficha del heroe. '@' suele ser SHIFT+2 (EN) o AltGr+2 (ES).
        elif key == tcod.event.KeySym.AT or (
            key == tcod.event.KeySym.N2
            and modifier
            & (
                tcod.event.Modifier.LSHIFT
                | tcod.event.Modifier.RSHIFT
                | tcod.event.Modifier.RALT
            )
        ):
            return CharacterScreenEventHandler(self.engine)
        # Cerrar puerta cercana
        elif key == tcod.event.KeySym.c:
            return actions.CloseDoorAction(player)
        # Inspeccionar alrededores
        elif key == tcod.event.KeySym.SLASH:
            return LookHandler(self.engine)
        elif key == tcod.event.KeySym.x:
            return LookHandler(self.engine)
        elif key == tcod.event.KeySym.z:
            return ExamineScreenEventHandler(self.engine)
        elif key == tcod.event.KeySym.p:
            return CombatControlHandler(self.engine)
        #elif key == tcod.event.K_f:
        #    return SingleRangedAttackHandler(self.engine)
        elif key == tcod.event.KeySym.f:
            ranged_handler = self._maybe_fire_ranged_weapon(player)
            if ranged_handler:
                return ranged_handler
        elif key == tcod.event.KeySym.q:
            return ToogleLightAction(player)
        # Ataque con alcance (arma con alcance >= 2)
        elif key == tcod.event.KeySym.TAB:
            reach_handler = self._maybe_reach_attack(player)
            if reach_handler:
                return reach_handler
        # Lanzar item del inventario
        elif key == tcod.event.KeySym.t:
            # Selecciona el ítem primero, luego el objetivo.
            return InventoryThrowHandler(self.engine)
        # Debug console
        elif self.engine.debug == True:
            if key == tcod.event.KeySym.BACKSPACE:
                if DEBUG_MODE == True:
                    import ipdb
                    return ipdb.set_trace()

        return action

    def _maybe_confirm_friendly_attack(
        self, player: Actor, dx: int, dy: int
    ) -> Optional[ActionOrHandler]:
        dest_x = player.x + dx
        dest_y = player.y + dy
        target = self.engine.game_map.get_actor_at_location(dest_x, dest_y)
        if not target:
            return None
        fighter = getattr(target, "fighter", None)
        if not fighter or getattr(fighter, "hp", 0) <= 0:
            return None
        if not _is_friendly_target(player, target):
            return None
        return ConfirmFriendlyAttackHandler(
            self.engine,
            self,
            player,
            target,
            lambda: BumpAction(player, dx, dy),
            target_position=(dest_x, dest_y),
        )

    def _maybe_open_chest(self, player, dx: int, dy: int) -> Optional[ActionOrHandler]:
        dest_x = player.x + dx
        dest_y = player.y + dy
        blocker = self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y)
        if isinstance(blocker, (Chest, TableContainer, BookShelfContainer)):
            return ChestLootHandler(self.engine, blocker)
        return None

    def _find_projectile(self, projectile_type: str) -> Optional["Item"]:
        for item in self.engine.player.inventory.items:
            if getattr(item, "projectile_type", None) == projectile_type:
                return item
        return None

    def _maybe_fire_ranged_weapon(self, player: Actor) -> Optional[ActionOrHandler]:
        weapon = getattr(player.equipment, "weapon", None)
        equippable = getattr(weapon, "equippable", None)
        weapon_range = getattr(equippable, "ranged_range", 0) if equippable else 0

        if not weapon or weapon_range <= 0:
            self.engine.message_log.add_message(
                "Necesitas un arma a distancia equipada.",
                color.impossible,
            )
            return None

        arrow = self._find_projectile("arrow")
        if not arrow:
            self.engine.message_log.add_message(
                "No tienes flechas.",
                color.impossible,
            )
            return None

        self.engine.message_log.add_message(
            "Selecciona un objetivo a distancia.",
            color.needs_target,
        )
        def _ranged_action(pos: Tuple[int, int]) -> Optional[ActionOrHandler]:
            target = self.engine.game_map.get_actor_at_location(*pos)
            action_factory = lambda: ThrowItemAction(
                player, arrow, pos, ranged_weapon=weapon
            )
            if target and _is_friendly_target(player, target):
                return ConfirmFriendlyAttackHandler(
                    self.engine,
                    MainGameEventHandler(self.engine),
                    player,
                    target,
                    action_factory,
                    target_position=pos,
                )
            return action_factory()

        return SingleRangedAttackHandler(self.engine, _ranged_action)

    def _maybe_reach_attack(self, player: Actor) -> Optional[ActionOrHandler]:
        weapon = getattr(player.equipment, "weapon", None)
        equippable = getattr(weapon, "equippable", None)
        weapon_reach = getattr(equippable, "reach", 0) if equippable else 0

        if not weapon or weapon_reach < 1:
            self.engine.message_log.add_message(
                "Necesitas un arma con alcance para atacar.",
                color.impossible,
            )
            return None

        targets: List[Actor] = []
        for actor in self.engine.game_map.actors:
            if actor is player:
                continue
            if not getattr(actor, "fighter", None):
                continue
            dx = abs(player.x - actor.x)
            dy = abs(player.y - actor.y)
            if max(dx, dy) <= weapon_reach:
                targets.append(actor)

        if not targets:
            self.engine.message_log.add_message(
                "No hay criaturas en alcance.",
                color.impossible,
            )
            return None

        if len(targets) == 1:
            target = targets[0]
            action_factory = lambda: actions.ReachMeleeAction(
                player,
                target.x - player.x,
                target.y - player.y,
                weapon_reach,
            )
            if _is_friendly_target(player, target):
                return ConfirmFriendlyAttackHandler(
                    self.engine,
                    self,
                    player,
                    target,
                    action_factory,
                    target_position=(target.x, target.y),
                )
            return action_factory()

        self.engine.message_log.add_message(
            "Selecciona un objetivo en alcance.",
            color.needs_target,
        )
        def _reach_action(pos: Tuple[int, int]) -> Optional[ActionOrHandler]:
            target = self.engine.game_map.get_actor_at_location(*pos)
            action_factory = lambda: actions.ReachMeleeAction(
                player,
                pos[0] - player.x,
                pos[1] - player.y,
                weapon_reach,
            )
            if target and _is_friendly_target(player, target):
                return ConfirmFriendlyAttackHandler(
                    self.engine,
                    MainGameEventHandler(self.engine),
                    player,
                    target,
                    action_factory,
                    target_position=pos,
                )
            return action_factory()

        return SingleRangedAttackHandler(self.engine, _reach_action)


class GameOverEventHandler(EventHandler):

    def on_quit(self) -> None:
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuitWithoutSaving()  # Avoid saving a finished game.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.on_quit()
        elif event.sym in WAIT_KEYS:
            return WaitAction(self.engine.player)
        elif event.sym == tcod.event.KeySym.v:
            return HistoryViewer(self.engine, parent_handler=self)
        return None
    

CURSOR_Y_KEYS = {
    # tcod.event.K_UP: -1,
    # tcod.event.K_DOWN: 1,
    # tcod.event.K_PAGEUP: -10,
    # tcod.event.K_PAGEDOWN: 10,
    tcod.event.KeySym.UP: -1,
    tcod.event.KeySym.DOWN: 1,
    tcod.event.KeySym.PAGEUP: -10,
    tcod.event.KeySym.PAGEDOWN: 10,
}


class HistoryViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(
        self, engine: Engine, parent_handler: Optional[BaseEventHandler] = None
    ):
        super().__init__(engine)
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length - 1
        self.parent_handler = parent_handler

    def on_render(self, console: tcod.console.Console) -> None:
        super().on_render(console)  # Draw the main state as the background.

        log_console = tcod.console.Console(console.width - 6, console.height - 6)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Message history├", alignment=libtcodpy.CENTER
        )

        # Render the message log using the cursor parameter.
        self.engine.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.engine.message_log.messages[: self.cursor + 1],
            name_colors=self.engine._get_message_name_colors(),
        )
        log_console.blit(console, 3, 3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        # Fancy conditional movement to make it feel right.
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                # Only move from the top to the bottom when you're on the edge.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                # Same with bottom to top movement.
                self.cursor = 0
            else:
                # Otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0  # Move directly to the top message.
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self.log_length - 1  # Move directly to the last message.
        else:  # Any other key moves back to the previous state (defaults to main).
            return self.parent_handler or MainGameEventHandler(self.engine)
        return None


class HelpScreenEventHandler(EventHandler):
    """Display controls and extended documentation with scroll support."""

    TITLE = "Ayuda y controles"

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.cursor = 0
        self._max_cursor = 0
        self._raw_lines = self._build_content_lines()

    def _build_content_lines(self) -> List[str]:
        controls = [
            #_("CONTROLS"),
            "",
            _("Use the arrows (or Page Up/Page Down) to navigate through this help."),
            "",
            _("You can also open this help with F1."),
            "",
            "",
            "NUMPAD",
            "",
            "   7 8 9",
            "   4 5 6",
            "   1 2 3",
            "",
            "   5 - Wait",
            "",
            "",
            "VI KEYS (recommended)",
            "",
            "   y k u",
            "   j . l",
            "   b j n",
            "",
            "   . - Wait",
            "",
            "",
            "OTHER",
            "",
            "   i           Examine inventory",
            "",
            "   g           Pickup item",
            "",
            "   d           Drop item",
            "",
            "   a           Use/wear/wield item (from inventory)",
            "",
            "   t           Throw item",
            "",
            "   f           Fire weapon",
            "",
            "   TAB         Reach attack (with spears, etc.)",
            "",
            "   x, z, /     Look/examine",
            "",
            "   c           Close door",
            "",
            "   SPACE       Interact (context menu)",
            "",
            "   q           On/Off lantern",
            "",
            "   c, @, \"     Character information",
            "",
            "   p           Visible monster information panel",
            "",
            "   v           Message log",
            "",
            "   ESC         Save game and quit",
            "",
            "   BACKSPACE   Debug Console (only on debug mode)",
            "",
            "",
            #"DOCUMENTACIÓN DEL JUEGO",
            #"",
        ]
        # Esta opción para imprimir también el game_documentation.txt
        return controls + self._load_documentation_lines()
        #return controls

    def _load_documentation_lines(self) -> List[str]:
        doc_path = os.path.join(os.path.dirname(__file__), "game_documentation.txt")
        try:
            with open(doc_path, "r", encoding="utf-8") as doc_file:
                contents = doc_file.read().splitlines()
        except FileNotFoundError:
            return ["(No se encontró game_documentation.txt)."]
        except OSError as exc:
            return [f"(No se pudo leer game_documentation.txt: {exc})"]

        return contents if contents else ["(game_documentation.txt está vacío.)"]

    def _wrap_lines(self, width: int) -> List[str]:
        wrapped: List[str] = []
        for line in self._raw_lines:
            if not line:
                wrapped.append("")
                continue
            parts = textwrap.wrap(
                line,
                width=width,
                expand_tabs=False,
                replace_whitespace=False,
                drop_whitespace=False,
            )
            wrapped.extend(parts or [""])
        return wrapped

    def on_render(self, console: tcod.console.Console) -> None:
        super().on_render(console)  # Draw the main state as the background.

        help_console = tcod.console.Console(console.width - 6, console.height - 6)
        help_console.draw_frame(0, 0, help_console.width, help_console.height)
        help_console.print_box(
            0,
            0,
            help_console.width,
            1,
            f"┤{self.TITLE}├",
            alignment=libtcodpy.CENTER,
        )

        wrap_width = help_console.width - 2
        wrapped_lines = self._wrap_lines(wrap_width)
        visible_height = help_console.height - 2

        self._max_cursor = max(len(wrapped_lines) - visible_height, 0)
        self.cursor = max(0, min(self.cursor, self._max_cursor))

        for i, line in enumerate(
            wrapped_lines[self.cursor : self.cursor + visible_height]
        ):
            help_console.print(1, 1 + i, line)

        help_console.blit(console, 3, 3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            self.cursor = max(0, min(self.cursor + adjust, self._max_cursor))
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self._max_cursor
        else:
            return MainGameEventHandler(self.engine)
        return None
        
