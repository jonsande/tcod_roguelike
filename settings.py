import tcod

# -- Tiles ------------------------------------------------
GRAPHIC_MODE = "pseudo_ascii"
# Forzar un estilo concreto de muro (1, 2 o 3). Usa None para dejarlo al azar.
WALL_STYLE = None

if GRAPHIC_MODE == "pseudo_ascii":
    tileset_cod = "pseudo_ascii"
    # 16x16 son el número de casillas en las que se va a dividir el png: 16 ancho x 16 de alto
    tileset = tcod.tileset.load_tilesheet("data/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)

if GRAPHIC_MODE == "ascii":
    tileset_cod = "ascii"
    tileset = tcod.tileset.load_tilesheet("data/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)
    #tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 64, 64)
    #tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 60, 58)
    #tileset = tcod.tileset.load_truetype_font("data/PxPlus_IBM_CGAthin.ttf", 128, 128)
    #tileset = tcod.tileset.load_truetype_font("data/Terminus.ttf", 64, 64)
    #tileset = tcod.tileset.set_truetype_font("data/Terminus.ttf", 128, 128)
    #tileset = tcod.tileset.load_truetype_font("data/square.ttf", 64, 64)
    #tileset = tcod.tileset.load_truetype_font("data/white-rabbit.regular.ttf", 128, 128)

if GRAPHIC_MODE == "hardcore":
    tileset_cod = "hardcore"
    tileset = tcod.tileset.load_tilesheet("data/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)

# Original
# 32x8 son el número de casillas en las que se va a dividir el png: 32 ancho x 8 de alto
#tileset = tcod.tileset.load_tilesheet(
#    "data/dejavu10x10_gs_tc_2x.png", 32, 8, tcod.tileset.CHARMAP_TCOD
#)

# -- Development helpers ------------------------------------------------------
# Si está activo, el jugador lo ve todo (FOV enorme) y los muros no bloquean la visión.
GOD_MODE = True
GOD_MODE_STEALTH = False

# -- Cavern generation --------------------------------------------------------
# Probabilidad de que un piso generado proceduralmente sea una caverna en vez de un conjunto de habitaciones.
CAVERN_SPAWN_CHANCE = 0.10
# Porcentaje inicial de roca en el mapa; cuanto más alto, más estrechas y cerradas son las cuevas.
CAVERN_FILL_PROBABILITY = 0.60
# Número mínimo de vecinos muro necesarios para que un muro "nazca" (afecta al tamaño de los huecos abiertos).
CAVERN_BIRTH_LIMIT = 4
# Número de vecinos muro a partir del cual un muro muere/se convierte en suelo (ajusta lo agresivo del suavizado).
CAVERN_DEATH_LIMIT = 3
# Iteraciones del autómata celular; más pasos producen cavernas más suaves y con menos ruido.
CAVERN_SMOOTHING_STEPS = 5

# -- Column decorations -------------------------------------------------------
# Probabilidad de que las salas generadas (rectangulares, circulares, elípticas o en cruz) aparezcan con columnas.
ROOM_DECORATION_CHANCE = {
    "rectangle": 0.05,
    "circle": 0.05,
    "ellipse": 0.05,
    "cross": 0.05,
}

# -- Dungeon population tables ------------------------------------------------
# Máximo de manchas de escombros por piso (tuplas: nivel mínimo, cantidad máxima).
MAX_DEBRIS_BY_FLOOR = [
    (1, 30),
    (2, 9),
    (4, 7),
    (6, 14),
    (7, 2),
]

# Máximo de objetos por habitación según el nivel del piso.
MAX_ITEMS_BY_FLOOR = [
    (1, 2),
    (2, 1),
    (3, 0),
    (4, 2),
    (6, 3),
    (7, 2),
    (11, 5),
    (12, 1),
]

# Máximo de monstruos por habitación según el nivel del piso.
MAX_MONSTERS_BY_FLOOR = [
    (0, 0),
    (1, 1),
    (2, 1),
    (3, 1),
    (4, 2),
    (6, 0),
    (7, 2),
    (11, 2),
]

# Configuración de botín/objetos: por cada nivel mínimo, lista de (nombre_del_item, peso).
ITEM_CHANCES = {
    1: [
        ("antidote", 5), ("sand_bag", 5), ("health_potion", 5), ("posion_potion", 5),
        ("power_potion", 5), ("stamina_potion", 5), ("confusion_potion", 5),
        ("precission_potion", 5), ("strength_potion", 2),
    ],
    2: [
        ("health_potion", 15), ("posion_potion", 15), ("power_potion", 15),
        ("stamina_potion", 15), ("confusion_potion", 15), ("precission_potion", 15),
        ("rock", 15), ("table", 15), ("short_sword", 5), ("short_sword_plus", 2),
        ("long_sword", 5), ("long_sword_plus", 3), ("spear", 5), ("spear_plus", 3),
    ],
    3: [
        ("poisoned_triple_ration", 10), ("triple_ration", 10), ("rock", 45),
        ("confusion_scroll", 10), ("paralisis_scroll", 10), ("lightning_scroll", 5),
        ("fireball_scroll", 5), ("short_sword", 5), ("short_sword_plus", 2),
        ("long_sword", 5), ("long_sword_plus", 3), ("spear", 5), ("spear_plus", 3),
    ],
    4: [
        ("confusion_scroll", 15), ("paralisis_scroll", 15), ("lightning_scroll", 10),
        ("fireball_scroll", 5),
    ],
    5: [
        ("lightning_scroll", 10), ("fireball_scroll", 10), ("long_sword", 5), ("chain_mail", 5),
    ],
    7: [
        ("spear", 10), ("spear_plus", 5),
    ],
    8: [
        ("short_sword", 15),
    ],
}

# Configuración de monstruos por habitación: (nombre_del_monstruo, peso) por nivel mínimo.
ENEMY_CHANCES = {
    1: [
        ("adventurer", 100), ("monkey", 20), ("fireplace", 10), ("snake", 10),
        ("rat", 50), ("swarm_rat", 20), ("goblin", 10),
    ],
    2: [
        ("monkey", 10), ("adventurer", 2), ("rat", 50), ("swarm_rat", 50), ("goblin", 50),
    ],
    3: [
        ("orc", 20), ("goblin", 50),
    ],
    4: [
        ("swarm_rat", 20), ("rat", 0), ("orc", 30), ("goblin", 30),
    ],
    5: [
        ("true_orc", 5), ("orc", 30), ("goblin", 30), ("troll", 5),
    ],
    8: [
        ("adventurer", 15), ("true_orc", 20), ("orc", 50), ("goblin", 15), ("bandit", 10),
    ],
    12: [
        ("adventurer", 0),
    ],
}

# Configuración de escombros/decoración menor por nivel.
DEBRIS_CHANCES = {
    0: [("debris_a", 30)],
    3: [("debris_a", 20)],
    6: [("debris_a", 10)],
}

# -- Fixed room templates -----------------------------------------------------
# Probabilidad (por nivel mínimo) de sustituir una sala generada por cada plantilla fija.
FIXED_ROOM_CHANCES = {
    "room_01": [(1, 0.08), (6, 0.08)],
    "room_secret": [(1, 0.90), (8, 0.10)],
    "room_door": [(1, 0.08), (5, 0.08)],
}

# -- Procedural room shapes ---------------------------------------------------
# Probabilidades relativas de que una sala se genere como círculo, elipse o cruz (rectángulo siempre pesa 1.0).
ROOM_SHAPE_WEIGHTS = {
    "circle": 0.45,
    "ellipse": 0.35,
    "cross": 0.28,
}

# Tamaños mínimos requeridos (lado más corto) antes de permitir cada forma alternativa.
ROOM_MIN_SIZE_SHAPES = {
    "circle": 6,
    "ellipse": 7,
    "cross": 7,
}
