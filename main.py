"""main.py file is responsible for:

+ Setting up the initial variables, like screen size and the tileset.
+ Creating the entities
+ Drawing the screen and everything on it.
+ Reacting to the player’s input."""

#!/usr/bin/env python3
import traceback
import tcod
import color
import exceptions
import input_handlers
import setup_game


def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """If the current event handler has an active Engine then save it."""
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")


def main() -> None:

    #screen_width = 95
    #screen_heigth = 51
    screen_width = 80
    screen_heigth = 44
    #screen_width = 70
    #screen_heigth = 45

    # 32x8 son el número de casillas en las que se va a dividir el png: 32 ancho x 8 de alto
    #tileset = tcod.tileset.load_tilesheet(
    #    "data/dejavu10x10_gs_tc_2x.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    #)

    tileset = tcod.tileset.load_tilesheet("data/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)
    #tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 64, 64)
    #tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 60, 58)
    #tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 128, 128)
    #tileset = tcod.tileset.load_truetype_font("data/Terminus.ttf", 64, 64)
    #tileset = tcod.tileset.set_truetype_font("data/Terminus.ttf", 128, 128)
    #tileset = tcod.tileset.load_truetype_font("data/square.ttf", 64, 64)
    
    #tileset = tcod.tileset.load_truetype_font("data/white-rabbit.regular.ttf", 128, 128)
    
    
    

    handler: input_handlers.BaseEventHandler = setup_game.MainMenu()

    with tcod.context.new_terminal(
        screen_width,
        screen_heigth,
        tileset=tileset,
        title="MONKEY ISLAND RL",
        vsync=True,
    ) as context:
        #root_console = tcod.Console(screen_width, screen_heigth, order="F")   # DEPRECATED
        root_console = tcod.console.Console(screen_width, screen_heigth, order="F")
        try:
            while True:
                root_console.clear()
                handler.on_render(console=root_console)
                context.present(root_console)

                try:
                    for event in tcod.event.wait():
                        context.convert_event(event)
                        handler = handler.handle_events(event)
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