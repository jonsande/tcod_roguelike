import sys
import os
# Un truco para asegurarse de que se cargan las librerías adecuadas
# en caso de que haya instaladas varias versiones de python
#os.environ["path"] = os.path.dirname(sys.executable) + ";" + os.environ["path"]
import glob

import tcod as libtcod

DATA_FOLDER = "data"
FONT_FILE = os.path.join(DATA_FOLDER, "dejavu10x10_gs_tc.png")

def main():
    screen_width = 80
    screen_heigth = 50

    libtcod.console_set_custom_font(FONT_FILE, libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
    libtcod.console_init_root(screen_width, screen_heigth, "ombarus libtcod tutorial revised", False)

    while not libtcod.console_is_window_closed():
        libtcod.console_set_default_foreground(0, libtcod.white)
        libtcod.console_put_char(0, 1, 1, '@', libtcod.BKGND_NONE)
        libtcod.console_flush()

        key = libtcod.console_check_for_keypress()
        
        if key.vk == libtcod.KEY_ESCAPE:
            return True


# Esta condición sirve para que se puedan usar funciones de este main.py desde otro archivo.py
# sin que por ello ejecute el código entero. Ejecutará todo el código en caso de que quien esté
# acudiendo a este main.py sea el propio main.py
if __name__ == "__main__":
    main()