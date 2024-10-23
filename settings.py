import tcod

## TILES
# 16x16 son el número de casillas en las que se va a dividir el png: 16 ancho x 16 de alto

# Default - Pseudo Ascii
tileset_cod = "pseudo_ascii"
tileset = tcod.tileset.load_tilesheet("data/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)


# Alternative - Ascii
#tileset_cod = "ascii"
#tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 64, 64)
#tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 60, 58)
#tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 128, 128)
#tileset = tcod.tileset.load_truetype_font("data/Terminus.ttf", 64, 64)
#tileset = tcod.tileset.set_truetype_font("data/Terminus.ttf", 128, 128)
#tileset = tcod.tileset.load_truetype_font("data/square.ttf", 64, 64)
#tileset = tcod.tileset.load_truetype_font("data/white-rabbit.regular.ttf", 128, 128)

# Hardcore mode
#tileset_cod = "hardcore"
#tileset = tcod.tileset.load_tilesheet("data/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)


# Original
# 32x8 son el número de casillas en las que se va a dividir el png: 32 ancho x 8 de alto
#tileset = tcod.tileset.load_tilesheet(
#    "data/dejavu10x10_gs_tc_2x.png", 32, 8, tcod.tileset.CHARMAP_TCOD
#)