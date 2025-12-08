"""main.py file is responsible for:

+ Setting up the initial variables, like screen size and the tileset.
+ Creating the entities
+ Drawing the screen and everything on it.
+ Reacting to the player’s input."""

#!/usr/bin/env python3
import time
import traceback
import tcod
import color
import exceptions
import input_handlers
import setup_game
import settings
from i18n import _


def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """If the current event handler has an active Engine then save it."""
    # Some handlers (like ConfirmQuitHandler) wrap the main game handler and
    # don't inherit from EventHandler, but still carry or point to the engine.
    current = handler
    visited = set()
    engine = None

    while current and id(current) not in visited:
        visited.add(id(current))
        engine = getattr(current, "engine", None)
        if engine:
            break
        current = getattr(current, "parent", None)

    if engine:
        engine.save_as(filename)
        print(_("Game saved."))


def main() -> None:

    screen_width = 80
    screen_heigth = 44
    
    #screen_width = 95
    #screen_heigth = 51
    #screen_width = 70
    #screen_heigth = 45

    tileset = settings.tileset  

    handler: input_handlers.BaseEventHandler = setup_game.MainMenu()

    window_flags = 0
    if getattr(settings, "FULLSCREEN", False):
        fullscreen_mode = str(getattr(settings, "FULLSCREEN_MODE", "desktop")).lower()
        flag_attr = "SDL_WINDOW_FULLSCREEN"
        if fullscreen_mode != "exclusive":
            flag_attr = "SDL_WINDOW_FULLSCREEN_DESKTOP"
        window_flags = getattr(tcod.context, flag_attr, 0)
    mouse_idle_hide_seconds = float(getattr(settings, "MOUSE_IDLE_HIDE_SECONDS", 0) or 0)
    cursor_hidden = False
    mouse_inside_window = False
    mouse_state_supported = hasattr(tcod.event, "get_mouse_state")
    mouse_visibility_supported = (
        hasattr(tcod, "sdl") and hasattr(tcod.sdl, "mouse") and hasattr(tcod.sdl.mouse, "show")
    ) or hasattr(tcod, "lib")
    mouse_last_move = time.monotonic()

    def _set_cursor_visible(visible: bool) -> None:
        nonlocal cursor_hidden, mouse_visibility_supported
        if not mouse_visibility_supported:
            return
        if cursor_hidden == (not visible):
            return
        try:
            if hasattr(tcod, "sdl") and hasattr(tcod.sdl, "mouse") and hasattr(tcod.sdl.mouse, "show"):
                tcod.sdl.mouse.show(visible)
            elif hasattr(tcod, "lib") and hasattr(tcod.lib, "SDL_ShowCursor"):
                tcod.lib.SDL_ShowCursor(1 if visible else 0)
            cursor_hidden = not visible
        except Exception:
            mouse_visibility_supported = False

    def _position_inside_window(position: object) -> bool:
        if position is None:
            return False
        try:
            x, y = position  # type: ignore[misc]
        except Exception:
            try:
                x, y = position.x, position.y  # type: ignore[attr-defined]
            except Exception:
                return False
        return 0 <= x < screen_width and 0 <= y < screen_heigth

    def _refresh_mouse_inside_from_state() -> None:
        nonlocal mouse_inside_window
        if not mouse_state_supported:
            return
        try:
            state = tcod.event.get_mouse_state()
        except Exception:
            return
        state = context.convert_event(state)
        mouse_inside_window = _position_inside_window(getattr(state, "position", None))

    with tcod.context.new_terminal(
        screen_width,
        screen_heigth,
        tileset=tileset,
        title=_("The Seeker"),
        vsync=True,
        sdl_window_flags=window_flags,
    ) as context:
        #root_console = tcod.Console(screen_width, screen_heigth, order="F")   # DEPRECATED
        root_console = tcod.console.Console(screen_width, screen_heigth, order="F")
        try:
            while True:
                root_console.clear()
                engine = getattr(handler, "engine", None)
                _refresh_mouse_inside_from_state()
                if engine:
                    engine.bind_display(context, root_console)
                    engine.play_intro_if_ready()
                    root_console.clear()
                handler.on_render(console=root_console)
                context.present(root_console)
                if engine:
                    engine.play_queued_animations(context, root_console)

                try:
                    events = list(tcod.event.get())
                    if not events:
                        time.sleep(0.016)
                    for event in events:
                        event = context.convert_event(event)
                        if event is None:
                            continue
                        if isinstance(
                            event,
                            (
                                tcod.event.MouseMotion,
                                tcod.event.MouseButtonDown,
                                tcod.event.MouseButtonUp,
                                tcod.event.MouseWheel,
                            ),
                        ):
                            mouse_inside_window = _position_inside_window(getattr(event, "position", None))
                            if cursor_hidden:
                                _set_cursor_visible(True)
                            mouse_last_move = time.monotonic()
                        handler = handler.handle_events(event)
                    if (
                        mouse_idle_hide_seconds > 0
                        and mouse_visibility_supported
                        and mouse_inside_window
                        and not cursor_hidden
                        and time.monotonic() - mouse_last_move >= mouse_idle_hide_seconds
                    ):
                        _set_cursor_visible(False)
                    elif cursor_hidden and not mouse_inside_window:
                        _set_cursor_visible(True)
                except Exception:  # Handle exceptions in game.
                    traceback.print_exc()  # Print error to stderr.
                    # Then print the error to the message log.
                    if isinstance(handler, input_handlers.EventHandler):
                        handler.engine.message_log.add_message(
                            traceback.format_exc(), color.error
                        )
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit:  # Save and quit.
            save_game(handler, "savegame.sav")
            raise
        except BaseException:  # Save on any other unexpected exception.
            save_game(handler, "savegame.sav")
            raise
                

# Esta condición sirve para que se puedan usar funciones de este main.py desde otro archivo.py
# sin que por ello ejecute el código entero. Ejecutará todo el código en caso de que quien esté
# acudiendo a este main.py sea el propio main.py
if __name__ == "__main__":
    main()
