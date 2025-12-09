import tcod
from random import randint

LANGUAGE = "es"  # Idioma activo de la interfaz. Opciones: en, es.
FALLBACK_LANGUAGE = "en"  # Idioma al que se recurre si falta una cadena.

# -- GRAPHICS ------------------------------------------------
# NOTA: cargas data/graphics/bob20x20.png con tcod.tileset.CHARMAP_CP437, así que cada casilla del PNG se asigna a un código CP437 y no a una tecla física del teclado.
# Como la hoja tiene 16 columnas, el índice del tile se calcula index = x + y * 16 (tomando x y y desde 0, con x=0 en la primera columna y y=0 en la primera fila). Ese índice se usa para buscar el código Unicode real: codepoint = tcod.tileset.CHARMAP_CP437[index] y glyph = chr(codepoint).
# Por ejemplo: supongamos x=1, y=12: index = 1 + 12*16 = 193, codepoint = 193 y el carácter correspondiente es '╣' (U+2563). En el código lo puedes usar como ord('╣'), '\u2563' o incluso tcod.tileset.CHARMAP_CP437[193] al definir el graphic del tile.
# Muchos de esos símbolos no existen como tecla dedicada, por lo que siempre es mejor referirte a ellos por su código (número CP437/Unicode) o pegando el símbolo literal. Si necesitas revisar otros índices, un snippet como el siguiente te imprime cualquier casilla:
# Se pueden copiar los símbolos aquí: 
# https://en.wikipedia.org/wiki/Code_page_437
# https://es.wikipedia.org/wiki/P%C3%A1gina_de_c%C3%B3digos_437

GRAPHIC_MODE = "ascii"

if GRAPHIC_MODE == "pseudo_ascii":
    tileset_cod = "pseudo_ascii"
    # 16x16 son el número de casillas en las que se va a dividir el png: 16 ancho x 16 de alto
    tileset = tcod.tileset.load_tilesheet("data/graphics/bob20x20_chest_3.png", 16, 16, tcod.tileset.CHARMAP_CP437)

if GRAPHIC_MODE == "ascii":
    tileset_cod = "ascii"

    # STANDARD
    tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin.ttf", 128, 128)

    # CUSTOM
    #tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin_bob.ttf", 128, 128)

    # OTHER
    #tileset = tcod.tileset.load_truetype_font("data/graphics/AppleII.ttf", 128, 128)

    ##tileset = tcod.tileset.load_truetype_font("data/graphics/Fix15Mono-Bold.ttf", 16, 16)
    #tileset = tcod.tileset.load_tilesheet("data/graphics/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)
    #tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin.ttf", 64, 64)
    #tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin.ttf", 60, 58)
    #tileset = tcod.tileset.load_truetype_font("data/graphics/Terminus.ttf", 64, 64)
    #tileset = tcod.tileset.set_truetype_font("data/graphics/Terminus.ttf", 128, 128)
    #tileset = tcod.tileset.load_truetype_font("data/graphics/square.ttf", 64, 64)
    #tileset = tcod.tileset.load_truetype_font("data/graphics/white-rabbit.regular.ttf", 128, 128)

if GRAPHIC_MODE == "hardcore":
    tileset_cod = "hardcore"
    tileset = tcod.tileset.load_tilesheet("data/graphics/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)

# Original
# 32x8 son el número de casillas en las que se va a dividir el png: 32 ancho x 8 de alto
#tileset = tcod.tileset.load_tilesheet(
#    "data/graphics/dejavu10x10_gs_tc_2x.png", 32, 8, tcod.tileset.CHARMAP_TCOD
#)

# -- Visual transitions ------------------------------------------------
# Controla la animación de fundido al usar las escaleras.
STAIR_TRANSITION_ENABLED = True
STAIR_TRANSITION_STEPS = 12
STAIR_TRANSITION_FRAME_TIME = 0.03  # segundos entre fotogramas

# -- Window options -----------------------------------------------------
# Define si la ventana arranca en modo pantalla completa. "desktop" usa el
# fullscreen sin cambiar la resolución; "exclusive" intenta usar el modo
# exclusivo de SDL2.
FULLSCREEN = True
FULLSCREEN_MODE = "desktop"  # "desktop" o "exclusive"
# Oculta el cursor del ratón tras unos segundos de inactividad dentro de la ventana.
MOUSE_IDLE_HIDE_SECONDS = 3.0

# -- Intro cinematic ----------------------------------------------------
# Controla si se muestra una breve introducción al iniciar una nueva partida.
INTRO_ENABLED = True
INTRO_FADE_DURATION = 2.7  # segundos para fundir a negro o desde él
INTRO_SLIDE_DURATION = 3.5  # tiempo en pantalla antes de iniciar el fundido
if LANGUAGE == "es":
    INTRO_SLIDES = [
        {
            "text": "Los ancianos han elegido.",
            "hold": 4.2,
        },
        {
            "text": "El ancestral artefacto se perdió generaciones atrás.\n"
            "Los videntes de la tribu lo ven en sueños. Dicen verlo encerrado en\n"
            "una urna de piedra, en el fondo de un antiguo laberinto subterráneo.\n"
            "Nadie sabe quién construyó el laberinto. Ni con qué propósito.\n"
            "Algunos aseguran que es un templo, y que hay en él signos de ser\n"
            "muy anterior al Tercer Nacimiento.\n",
            "hold": 17.3,
        },
        {
            "text": "Los ancianos han elegido a un nuevo buscador. El elegido deberá viajar\n"
            "a través de las montañas del Duule hasta el desierto pálido, encontrar\n"
            "la entrada al laberinto y adentrarse en él.\n"
            "Muchos otros han emprendido la Gran Búsqueda antes. Nadie ha vuelto.",
            "hold": 13.0,
        },
    ]
else:
    INTRO_SLIDES = [
        {
            "text": "The elders have chosen.",
            "hold": 2.2,
        },
        {
            "text": "The ancient artifact was lost generations ago.\n"
            "The seers of the tribe glimpse it in their dreams. They claim to see\n"
            "it sealed within a stone urn, deep in an ancient underground labyrinth.\n"
            "No one knows who built the labyrinth, nor for what purpose. Some say \n"
            "it is a temple, bearing signs of an age long before the Third Birth.\n",
            "hold": 17.3,
        },
        {
            "text": "The elders have chosen a new seeker. The chosen one must travel\n"
            "across the Duule Mountains to the Pale Desert, find the entrance to the\n"
            "labyrinth, and venture into its depths.\n"
            "Many before have embarked on the Great Quest. None have ever returned.",
            "hold": 13.0,
        },
    ]

# -- Audio settings ------------------------------------------------------
# Configuración de audio movida a audio_settings.py

# -- Development helpers ------------------------------------------------------
# Si está activo, el jugador lo ve todo (FOV enorme) y los muros no bloquean la visión.
GOD_MODE = True
GOD_MODE_STEALTH = False
DEBUG_MODE = True # Con la tecla BACKSPACE se hace un ipdb.set_trace() y se pueden ejecutar órdenes desde consola.
DEBUG_DRAW_HOT_PATH = False

# -- Game settings ------------------------------------------------------

if LANGUAGE == "es":
    INTRO_MESSAGE = "Tras un largo viaje, finalmente encuentras la entrada al laberinto."
else:
    INTRO_MESSAGE = "After a long journey, you find the entrance to the labyrinth."

# -- Player progression -------------------------------------------------------
# Permite activar/desactivar el sistema de subida de nivel del jugador.
# Cambia a True si quieres recuperar los mensajes y el menú de subida de niveles por
# xp en el futuro. El sistema está obsoleto y mal implementado ahora mismo.
PLAYER_LEVELING_ENABLED = False
# Ataques fallidos necesarios (contra el jugador) para ganar +1 a base_defense. Usa 0 para desactivar.
PLAYER_DEFENSE_MISS_THRESHOLD = 60

# -- Player starting gear -----------------------------------------------------
# Cada entrada indica el objeto (clave en entity_factories) con el que empieza el
# jugador. `quantity` permite añadir varias copias y `equip` marca si se intenta
# equipar esa copia en cuanto empiece la partida.
PLAYER_STARTING_INVENTORY = [
    {"item": "triple_ration", "quantity": 2},
    # {"item": "accuracy_ring", "equip": True},
    # {"item": "leather_armor", "equip": True},
    {"item": "dagger", "quantity": 1, "equip": True},
    # {"item": "spear", "quantity": 1, "equip": True},
    # {"item": "descend_scroll", "quantity": 16},
    # {"item": "black_key", "quantity": 1},
    # {"item": "red_key", "quantity": 1},
    # {"item": "white_key", "quantity": 1},
    # {"item": "gray_key", "quantity": 1},
    # {"item": "identify_scroll", "quantity": 6},
    # {"item": "antidote_ring", "quantity": 1},
    # {"item": "infra_vision_potion", "quantity": 5},
    # {"item": "remove_curse_scroll", "quantity": 3},
    #{"item": "sand_bag", "quantity": 2},
    #{"item": "scout_hood", "quantity": 1},
    #{"item": "cloak", "quantity": 1},
]
# Límite superior de piezas equipadas automáticamente por tipo de ranura.
PLAYER_STARTING_EQUIP_LIMITS = {
    "weapon": 2,
    "armor": 2,
    "head_armor": 1,
    "cloak": 1,
    "artifact": 1,
    "ring": 2,
}

# -- Dungeon generation ------------------------------------------------
# Forzar un estilo concreto de muro (1, 2 o 3). Usa None para dejarlo al azar.
# TODO: si WALL_STYLE es None, ahora mismo se genera toda la mazmorra con un 
# sólo estilo. Debería hacerse la tirada por cada nivel, de forma que pueda pasar
# que en el nivel 2 el WALL_STYLE es 1 pero en el nivel 3 es 1, por ejemplo.
WALL_STYLE = None

# Parámetros experimentales para el generador generate_dungeon_v2().
# DUNGEON_V2_ROOM_MIN_SIZE = 3
# DUNGEON_V2_ROOM_MAX_SIZE = 8
# DUNGEON_V2_MIN_ROOM_DISTANCE = 2
# DUNGEON_V2_MAX_ROOM_DISTANCE = 12
# DUNGEON_V2_MAX_ROOMS = 75
# DUNGEON_V2_ROOM_PLACEMENT_ATTEMPTS = 150
# DUNGEON_V2_MAX_MAP_ATTEMPTS = 150

# Parámetros experimentales para generate_dungeon_v3().
DUNGEON_V3_MIN_ROOMS = 8
DUNGEON_V3_MAX_ROOMS = 20
DUNGEON_V3_ROOM_MIN_SIZE = 3
DUNGEON_V3_ROOM_MAX_SIZE = 8
DUNGEON_V3_MAX_PLACEMENT_ATTEMPTS = 220
DUNGEON_V3_PADDING = 1  # Espacio mínimo entre salas
DUNGEON_V3_EXTRA_CONNECTION_CHANCE = 0.35
DUNGEON_V3_EXTRA_CONNECTIONS = 3
DUNGEON_V3_LOCKED_DOOR_CHANCE = 0.50
# Las llaves las genera y coloca _ensure_keys_for_locked_doors(), de game_map.py
DUNGEON_V3_LOCKED_DOOR_MIN_FLOOR = {
    "white": 4, # Tiene que ser 4 o más, de lo contrario se generarán llaves en el nivel 1 (en la superficie)
    "red": 8,
    "gray": 12,
    "black": 14,
}

# Probabilidad de que la llave se asigne al inventario de un monstruo en su planta.
KEY_CARRIER_SPAWN_CHANCE = 0.35

# Nombres (case insensitive) de criaturas que pueden recibir llaves en su inventario.
KEY_CARRIER_ALLOWED_MONSTERS = [
    "Goblin",
    "Orc",
    "True Orc",
    "Bandit",
    "Cultist",
    "Sentinel",
]

# Probabilidad de que la llave aparezca dentro de un cofre existente en la planta.
KEY_CHEST_SPAWN_CHANCE = 0.25

DUNGEON_V3_FIXED_ROOMS_ENABLED = True
DUNGEON_V3_ENTRY_FEATURE_PROBS = {
    "none": 0.5,
    "door": 0.55,
    "breakable": 0.15,
}

# -- Dungeon structure -------------------------------------------------------
TOTAL_FLOORS = 16 # Debido al diseño del juego, 16 niveles son 15 (pues la superficie es el verdadero nivel 1)
MAX_DOORS_BY_LEVEL = 8
MAX_BREAKABLE_WALLS = 6

# -- Fixed dungeon floors ----------------------------------------------------
# Cada entrada permite asignar una planta a una plantilla fija definida en fixed_maps.py
# o en alguno de los generadores dedicados (por ejemplo, three_doors.py o the_library.py).
# `map` debe corresponder con el nombre de la plantilla y `walls`/`walls_special`
# con los identificadores de baldosas de tile_types.py.
FIXED_DUNGEON_LAYOUTS = {
    # 6: {
    #     "map": "temple",
    #     "walls": "wall_v1",
    #     "walls_special": "wall_v2",
    # },
    # 2: {
    #     "map": "the_library",
    #     "walls": "wall_v1",
    #     "walls_special": "wall_v2",
    # },
    8: {
        "map": "three_doors",
        "walls": "wall_v2",
        "walls_special": "wall_v1",
    },
}

# -- Breakable wall behavior -------------------------------------------------
# Intervalo de puntos de vida (hp mínimo, hp máximo) para cada muro rompible.
BREAKABLE_WALL_HP_RANGE = (12, 24)
# Probabilidad de que un muro esconda un objeto antes de romperse.
BREAKABLE_WALL_CACHE_CHANCE = 0.07
# Probabilidad de que, si escondía algo, lo suelte al derrumbarse.
BREAKABLE_WALL_LOOT_CHANCE = 0.60

# Configuración de escombros/decoración menor por nivel.
DEBRIS_CHANCES = {
    1: [("debris_a", 90)],
    2: [("debris_a", 30)],
    3: [("debris_a", 20)],
    6: [("debris_a", 10)],
}

# Listado de todos los objetos. Útil para las CHEST_LOOT_TABLES y más
ALL_ITEMS = [
    ("strength_potion", 1), 
    ("increase_max_stamina", 1), 
    ("life_potion", 1), 
    ("infra_vision_potion", 1), 
    ("antidote", 1), 
    ("health_potion", 1), 
    ("poison_potion", 1), 
    ("power_potion", 1), 
    ("stamina_potion", 1), 
    ("temporal_infra_vision_potion", 1), 
    ("blindness_potion", 1), 
    ("confusion_potion", 1), 
    ("paralysis_potion", 1), 
    ("petrification_potion", 1), 
    ("precission_potion", 1),
    ("confusion_scroll", 1),
    ("paralisis_scroll", 1),
    ("identify_scroll", 1),
    ("remove_curse_scroll", 1),
    ("lightning_scroll", 1),
    ("fireball_scroll", 1),
    ("descend_scroll", 1),
    ("teleport_scroll", 1),
    ("prodigious_memory_scroll", 1),
    ("chain_mail", 1),
    ("leather_armor", 1),
    ("cloak", 1),
    ("leather_cap", 1),
    ("scout_hood", 1),
    ("iron_helmet", 1),
    ("orcish_war_helm", 1),
    ("dagger", 1),
    ("short_sword", 1),
    ("short_sword_plus", 1),
    ("long_sword", 1),
    ("long_sword_plus", 1),
    ("spear", 1),
    ("spear_plus", 1),
    ("poisoned_triple_ration", 1),
    ("triple_ration", 1),
    ("banana", 1),
    ("accuracy_ring", 1), 
    ("plain_ring", 1),
    ("strength_ring", 1),
    ("farsight_ring", 1),
    ("vigor_ring", 1),
    ("antidote_ring", 1),
    ("memory_ring", 1),
    ("recovery_ring", 1),
    ("guard_ring", 1),
    ("fortune_ring", 1),
    ("cursed_weakness_ring", 1),
    ("cursed_myopia_ring", 1),
    ("cursed_fatigue_ring", 1),
    ("cursed_lethargy_ring", 1),
    ("cursed_vulnerability_ring", 1),
    ("cursed_misfortune_ring", 1),
    ]

# -- Chest generation -------------------------------------------------
# Probabilidad de que aparezca un cofre en cada nivel (0-1, por nivel mínimo).
# TODO: averiguar qué pasa en los niveles que no tengan aquí una configuración asignada.
CHEST_SPAWN_CHANCES = [
    (2, 0.40),
    (3, 0.40),
    (4, 0.40),
    (5, 0.50),
    (8, 0.60),
]

# Probabilidad independiente para generar mesas con botín.
TABLE_SPAWN_CHANCES = [
    (2, 0.30),
    (4, 0.30),
    (6, 0.35),
]

# Probabilidad independiente para generar estanterías con botín.
BOOKSHELF_SPAWN_CHANCES = [
    (2, 0.25),
    (4, 0.25),
    (6, 0.30),
]
# Rango (mínimo, máximo) de objetos generados en cofres por nivel mínimo.
# El rango min-max extablecido para un nivel se aplica a los subsiguientes niveles, a no 
# ser que se sobre escriba.
CHEST_ITEM_COUNT_BY_FLOOR = [
    (1, (2, 2)), # En el nivel 1 (Town) se genera siempre un cofre junto a El Viejo.
    (2, (1, 2)),
    (4, (1, 3)),
    (6, (1, 3)),
    (8, (3, 4)),
    (10, (3, 4)),
    (12, (3, 5)),
    (14, (3, 5)),
    (16, (3, 5)),
]

OLD_MAN_CHEST = [
    "leather_armor",
]

# Cantidad (min, max) de ítems aleatorios que se añaden al cofre del Viejo.
OLD_MAN_RANDOM_ITEM_COUNT = (0, 1)

# Objetos candidatos para el botín adicional del cofre del Viejo.
# Cada entrada sigue el formato ("id_del_objeto", peso_relativo).
# OLD_MAN_RANDOM_ITEM_POOL = [
#     ("banana", 4),
#     ("triple_ration", 3),
#     ("strength_potion", 1),
#     ("life_potion", 1),
#     ("identify_scroll", 1),
# ]
OLD_MAN_RANDOM_ITEM_POOL = ALL_ITEMS

# Tablas de botín por nivel mínimo: lista de (id_objeto, peso relativo).
# TODO: averiguar qué pasa en los niveles que no tengan aquí una configuración asignada.
CHEST_LOOT_TABLES = {
    2: [
        # ("dagger", 1),
        # ("leather_armor", 1),
        ("strength_potion", 1), 
        ("increase_max_stamina", 1), 
        ("life_potion", 1), 
        ("infra_vision_potion", 1), 
        ("antidote", 1), 
        ("health_potion", 1), 
        ("poison_potion", 1), 
        ("power_potion", 1), 
        ("stamina_potion", 1), 
        ("temporal_infra_vision_potion", 1), 
        ("blindness_potion", 1), 
        ("confusion_potion", 1), 
        ("paralysis_potion", 1), 
        ("petrification_potion", 1), 
        ("precission_potion", 1),
        ("strength_ring", 1),
        ("farsight_ring", 1),
        ("vigor_ring", 1),
        ("antidote_ring", 1),
        ("memory_ring", 1),
        ("recovery_ring", 1),
        ("guard_ring", 1),
        ("fortune_ring", 1),
        ("cursed_weakness_ring", 1),
        ("cursed_myopia_ring", 1),
        ("cursed_fatigue_ring", 1),
        ("cursed_lethargy_ring", 1),
        ("cursed_vulnerability_ring", 1),
        ("cursed_misfortune_ring", 1),
        ("remove_curse_scroll", 1),
    ],
    3: ALL_ITEMS,
    8: [
        ("short_sword_plus", 2),
        ("spear_plus", 2),
        ("chain_mail", 1),
        ("fireball_scroll", 2),
        ("paralisis_scroll", 2),
        ("accuracy_ring", 2),
        ("strength_ring", 2),
        ("farsight_ring", 2),
        ("vigor_ring", 2),
        ("antidote_ring", 2),
        ("memory_ring", 1),
        ("recovery_ring", 2),
        ("guard_ring", 2),
        ("fortune_ring", 1),
        ("cursed_weakness_ring", 2),
        ("cursed_myopia_ring", 2),
        ("cursed_fatigue_ring", 2),
        ("cursed_lethargy_ring", 2),
        ("cursed_vulnerability_ring", 2),
        ("cursed_misfortune_ring", 2),
        ("strength_potion", 2), 
        ("increase_max_stamina", 2), 
        ("life_potion", 2), 
        ("infra_vision_potion", 2), 
        ("antidote", 1),
        ("health_potion", 1), 
        ("poison_potion", 1), 
        ("power_potion", 1), 
        ("stamina_potion", 1), 
        ("temporal_infra_vision_potion", 1), 
        ("blindness_potion", 1), 
        ("confusion_potion", 1), 
        ("paralysis_potion", 1), 
        ("petrification_potion", 1), 
        ("precission_potion", 1),
        ("confusion_scroll", 1),
        ("paralisis_scroll", 1),
        ("identify_scroll", 1),
        ("remove_curse_scroll", 1),
        ("lightning_scroll", 1),
        ("fireball_scroll", 1),
        ("descend_scroll", 1),
        ("teleport_scroll", 1),
        ("prodigious_memory_scroll", 1),
        ("remove_curse_scroll", 1),
        ("leather_cap", 1),
        ("scout_hood", 1),
        ("iron_helmet", 1),
        ("orcish_war_helm", 1),
    ],
    9: ALL_ITEMS,
}

# Botín de mesas: cantidades y tablas por nivel.
TABLE_ITEM_COUNT_BY_FLOOR = [
    (1, (0, 1)),
    (3, (0, 1)),
    (6, (0, 1)),
]

# Botín de estanterías: cantidades y tablas por nivel.
BOOKSHELF_ITEM_COUNT_BY_FLOOR = [
    (1, (0, 1)),
    (3, (0, 2)),
    (6, (1, 2)),
]

# Cada clave marca el nivel mínimo y lista los ítems posibles con su peso.
TABLE_LOOT_TABLES = {
    2: [
        ("library_clue_1", 1),
        ("library_clue_2", 1),
        ("library_clue_3", 1),
        ("library_clue_4", 1),
        ("library_clue_5", 1),
        ("library_clue_6", 1),
        ("triple_ration", 1),
        ("banana", 1),
        ("sand_bag", 1),
        ("note_wizard_1", 1),
        ("antidote", 1),
        ("stamina_potion", 1),
        ("remove_curse_scroll", 1),
        ("strength_potion", 1),
        ("poison_potion", 1)
    ],
}

# Cada clave marca el nivel mínimo y lista los ítems posibles con su peso.
BOOKSHELF_LOOT_TABLES = {
    2: [
        ("library_clue_1", 1),
        ("library_clue_2", 1),
        ("library_clue_3", 1),
        ("library_clue_4", 1),
        ("library_clue_5", 1),
        ("library_clue_6", 1),
        ("note_wizard_1", 1),
        ("triple_ration", 1),
        ("banana", 1),
        ("antidote", 1),
        ("stamina_potion", 1),
        ("remove_curse_scroll", 1),
        ("strength_potion", 1),
        ("confusion_scroll", 1),
        ("paralisis_scroll", 1),
        ("identify_scroll", 1),
        ("remove_curse_scroll", 1),
        ("lightning_scroll", 1),
        ("fireball_scroll", 1),
        ("descend_scroll", 1),
        ("teleport_scroll", 1),
        ("prodigious_memory_scroll", 1),
        ("remove_curse_scroll", 1),
    ],
}

# -- Fixed room templates -----------------------------------------------------
# Probabilidad (por nivel mínimo) de sustituir una sala generada por cada plantilla fija.
FIXED_ROOM_CHANCES = {
    # BUG: Generan a veces mapas sin camino transitable desde unas escaleras a otras
    "room_01": [(2, 0.08), (8, 0.00), (9, 0.08)],
    "room_02": [(2, 0.08), (8, 0.00), (9, 0.08)],
    "room_03": [(2, 0.08), (8, 0.00), (9, 0.08)],
    "room_04": [(2, 0.08), (8, 0.00), (9, 0.08)],
    # "room_secret": [(2, 0.10), (8, 0.10)], # BUGGED
    # "room_door": [(2, 0.08), (5, 0.00)], # BUGGED
    "room_secret_B": [(2, 0.08), (8, 0.00)],
}

# -- Procedural room shapes ---------------------------------------------------
# Probabilidades relativas de que una sala se genere como círculo, elipse o cruz (rectángulo siempre pesa 1.0).
ROOM_SHAPE_WEIGHTS = {
    "circle": 0.0,
    "ellipse": 0.0,
    "cross": 0.0,
}

# Tamaños mínimos requeridos (lado más corto) antes de permitir cada forma alternativa.
ROOM_MIN_SIZE_SHAPES = {
    "circle": 5,
    "ellipse": 5,
    "cross": 5,
}

# Generación de mapas de habitaciones y pasillos.
# Cada variante define el tamaño medio y el número de habitaciones del piso.
# room_min_size establece el ancho (o alto) mínimo para cada habitación (es decir,
# que una room_min_size = 3 quiere decir que la habitación mínima será de 3x3). Y
# lo mismo para max_room_size.
DUNGEON_MAP_VARIANTS = [
    {
        "weight": 0.5,
        "max_rooms": 8,
        "room_min_size": 4,
        "room_max_size": 10,
    },
    {
        "weight": 0.5,
        "max_rooms": 20,
        "room_min_size": 3,
        "room_max_size": 13,
    },
]

# Permite sobreescribir la configuración anterior para pisos concretos.
# Ejemplo: {3: [{"weight": 1.0, "max_rooms": 30, ...}]}
DUNGEON_MAP_VARIANT_OVERRIDES = {}

# Configuración de (entiendo) el generador estandard.
DUNGEON_MAP_STANDARD = {
    "weight": 1.0, 
    "max_rooms": 20, 
    "room_min_size": 2, 
    "room_max_size": 17
    }

# Probabilidad de excavar pasadizos extra entre salas ya existentes.
# Ajusta este valor para reducir o aumentar la cantidad de pasillos secundarios.
# TODO: Con los valores al mínimo parece que aun así se generan demasiados pasillos
# a veces. Esto habría que revisarlo.
DUNGEON_EXTRA_CONNECTION_CHANCE = 0.0
# Intentos que se hacen por cada sala para abrir conexiones extra si la tirada tiene éxito.
DUNGEON_EXTRA_CONNECTION_ATTEMPTS = 1

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

# -- Cavern monster population ------------------------------------------------
# Min/max creatures spawned per cavern level (list of tuples: floor threshold, (min, max)).
CAVERN_MONSTER_COUNT_BY_FLOOR = [(1, (5, 9))]
# Cavern-specific spawn rules follow the same schema as ENEMY_SPAWN_RULES.
CAVERN_MONSTER_SPAWN_RULES = {
    "snake": {"min_floor": 2, "weight_progression": [(2, 15), (7, 2)]},
    "goblin": {"min_floor": 2, "weight_progression": [(2, 10), (3, 20), (5, 15)]},
    "grey_goblin": {"min_floor": 7, "weight_progression": [(7, 15)]},
    "orc": {"min_floor": 4, "weight_progression": [(4, 12), (6, 25), (9, 10)]},
    "cave_bat": {"min_floor": 2, "weight_progression": [(1, 18), (4, 2), (7, 1)]},
    "skeleton": {"min_floor": 6, "weight_progression": [(5, 5), (7, 10)]},
    "slime": {"min_floor": 2, "weight_progression": [(2, 10), (3, 15), (5, 10)]}
}

# -- Cavern item population ---------------------------------------------------
# Rango (mínimo, máximo) de ítems colocados libremente en cuevas por nivel mínimo.
CAVERN_ITEM_COUNT_BY_FLOOR = [
    (1, (2, 5)),
    (2, (2, 5)),
    (3, (3, 5)),
    (5, (3, 5)),
]
# Tabla específica de cuevas reutilizando el mismo formato que ITEM_SPAWN_RULES.
# Configurado más abajo
# CAVERN_ITEM_SPAWN_RULES = {
# }

# -- Column decorations -------------------------------------------------------
# Probabilidad de que las salas generadas (rectangulares, circulares, elípticas o en cruz) aparezcan con columnas.
ROOM_DECORATION_CHANCE = {
    "rectangle": 0.15,
    "circle": 0.12,
    "ellipse": 0.12,
    "cross": 0.12,
}

# -- Dungeon population tables ------------------------------------------------
# Máximo de manchas de escombros por piso (tuplas: nivel mínimo, cantidad máxima).
MAX_DEBRIS_BY_FLOOR = [
    (1, 40),
    (2, 9),
    (4, 7),
    (6, 14),
    (7, 2),
]

# Máximo de objetos por habitación según el nivel del piso.
# La configuración en MAX_ITEMS_BY_FLOOR se aplica POR HABITACIÓN, no por nivel completo.
# En procgen.py, a la función place_entities se llama para cada habitación generada.
# Ahora bien; el elemento (1, 1), por ejemplo, quiere decir que para el nivel 1 SE PUEDE
# generar un máximo de 1 item. No quiere decir que se vaya a generar. Lo que hará la fun-
# ción place_entities() de procgen.py es una randint(0,1) para determinar si ese 1 máximo
# se traduce o no en un ítem.
# TODO: hacer la probabilidad de generación del place_entities dinámico, configurable desde
# el settings.
MAX_ITEMS_BY_FLOOR = [
    #(0, 0),
    (1, 0),
    (2, 1),
    (3, 1),
    (4, 1),
    (6, 1),
    (7, 1),
    (11, 1),
    (12, 1),
]

# Máximo de monstruos por habitación según el nivel del piso.
MAX_MONSTERS_BY_FLOOR = [
    #(1, 0),
    (2, 1),
    (3, 1),
    (5, 1),
    (6, 1),
    (7, 1),
    (11, randint(1,2)),
]

# -- Campfires --------------------------------------------------------------
CAMPFIRE_MIN_HP = 35
CAMPFIRE_MAX_HP = 320
# Chance (0-1) to spawn a nearby cache item when a campfire is placed.
CAMPFIRE_CACHE_ITEM_CHANCE = 0.10
# Prototype names defined in entity_factories.py eligible for cache drops.
CAMPFIRE_CACHE_ITEM_IDS = [
    "meat",
    "triple_ration",
    "health_potion",
    "strength_potion",
    "stamina_potion",
    "dagger",
    "dagger_plus",
]
# Chance (0-1) for a campfire to drop a fireball scroll when it dies out.
CAMPFIRE_SCROLL_DROP_CHANCE = 0.02

# -- Adventurers behavior -----------------------------------------------------
ADVENTURER_COLOR = (120, 120, 120)
ADVENTURER_CORPSE_CHAR = "%"
ADVENTURER_CORPSE_COLOR = (100, 100, 100)
ADVENTURER_CORPSE_NAME = "Remains of an adventurer"
# Base probability (0-1) added per floor after they descend to find their corpse.
ADVENTURER_CORPSE_CHANCE_PER_FLOOR = 0.15

# -- Loot generation -----------------------------------------------------------
# Configuración de botín/objetos. Cada entrada permite controlar:
# - min_floor: nivel mínimo en el que empieza a considerarse.
# - max_instances: número máximo de copias (None = ilimitado).
# - base_weight: peso base a partir de min_floor cuando no se usa weight_progression.
# - weight_per_floor: crecimiento lineal aplicado a partir de min_floor.
# - weight_progression: lista de (nivel, peso) que sobreescribe el peso a partir de ese nivel.
ITEM_SPAWN_RULES = {
    # HI VALUE POTIONS
    "strength_potion": {"min_floor": 2, "min_instances": 3, "max_instances": 5, "base_weight": 8, "weight_progression": [(3, 2)]},
    "increase_max_stamina": {"min_floor": 2, "min_instances": 3, "max_instances": 5, "base_weight": 8, "weight_progression": [(3, 2)]},
    "life_potion": {"min_floor": 2, "min_instances": 3, "max_instances": 5, "base_weight": 8, "weight_progression": [(3, 2)]},
    "infra_vision_potion": {"min_floor": 2, "min_instances": 3, "max_instances": 5, "base_weight": 8, "weight_progression": [(2, 6)]},
    # POTIONS
    "antidote": {"min_floor": 2, "weight_progression": [(1, 5)]},
    "sand_bag": {"min_floor": 2, "weight_progression": [(1, 5)]},
    "health_potion": {"min_floor": 2, "weight_progression": [(1, 5), (2, 15)]},
    "poison_potion": {"min_floor": 2, "weight_progression": [(1, 5), (2, 15)]},
    "power_potion": {"min_floor": 2, "weight_progression": [(1, 5), (2, 15)]},
    "stamina_potion": {"min_floor": 2, "weight_progression": [(1, 5), (2, 15)]},
    "temporal_infra_vision_potion": {"min_floor": 5, "weight_progression": [(5, 4)]},
    "blindness_potion": {"min_floor": 2, "weight_progression": [(1, 3), (2, 15)]},
    "confusion_potion": {"min_floor": 2, "weight_progression": [(1, 5), (2, 15)]},
    "paralysis_potion": {"min_floor": 2, "weight_progression": [(2, 15), (4, 2)]},
    "petrification_potion": {"min_floor": 6, "weight_progression": [(4, 5)]},
    "precission_potion": {"min_floor": 2, "weight_progression": [(1, 5), (2, 15)]},
    # WEAPONS
    "short_sword": {"min_floor": 2, "weight_progression": [(2, 5), (5, 10),(8, 7)]},
    "short_sword_plus": {"min_floor": 2, "weight_progression": [(6, 7)]},
    "long_sword": {"min_floor": 2, "weight_progression": [(5, 10)]},
    "long_sword_plus": {"min_floor": 2, "weight_progression": [(7, 8)]},
    "spear": {"min_floor": 2, "weight_progression": [(2, 5), (7, 10)]},
    "spear_plus": {"min_floor": 2, "weight_progression": [(2, 3), (7, 5)]},
    # FOOD
    "poisoned_triple_ration": {"min_floor": 2, "weight_progression": [(2, 10)]},
    "triple_ration": {"min_floor": 2, "weight_progression": [(2, 10)]},
    "banana": {"min_floor": 2, "weight_progression": [(2, 1)]},
    # SCROLLS
    "confusion_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(1, 10), (4, 12), (4, 15)]},
    "paralisis_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(1, 10), (4, 12), (4, 15)]},
    "identify_scroll": {"min_floor": 2, "max_instances": 6, "weight_progression": [(1, 8), (4, 12)]},
    "remove_curse_scroll": {"min_floor": 3, "max_instances": 4, "weight_progression": [(3, 6), (6, 8)]},
    "lightning_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(1, 7), (4, 10), (4, 10)]},
    "fireball_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(1, 7), (4, 10), (4, 10)]},
    "descend_scroll": {"min_floor": 2, "max_instances": 4, "weight_progression": [(3, 2), (6, 3)]},
    "teleport_scroll": {"min_floor": 2, "max_instances": 6, "weight_progression": [(2, 3), (5, 4)]},
    "prodigious_memory_scroll": {"min_floor": 5, "max_instances": 2, "weight_progression": [(5, 2), (8, 7)]},
    # ARMOR
    "chain_mail": {"min_floor": 5, "weight_progression": [(5, 5)]},
    "leather_armor": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "cloak": {"min_floor": 2, "weight_progression": [(2, 5)]},
    # HEADARMOR
    "leather_cap": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "scout_hood": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "iron_helmet": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "orcish_war_helm": {"min_floor": 3, "weight_progression": [(2, 5)]},
    # RINGS
    "accuracy_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "plain_ring": {"min_floor": 4, "max_instances": 8, "weight_progression": [(4, 2), (6, 5)]},
    "strength_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "farsight_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "vigor_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "antidote_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "memory_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "recovery_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "guard_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "fortune_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "cursed_weakness_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "cursed_myopia_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "cursed_fatigue_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "cursed_lethargy_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "cursed_vulnerability_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    "cursed_misfortune_ring": {"min_floor": 4, "max_instances": 1, "weight_progression": [(4, 2), (6, 5)]},
    # OTHER
    "rock": {"min_floor": 2, "weight_progression": [(2, 15), (3, 45)]},
    "note_wizard_1": {"min_floor": 2, "max_instances": 1, "weight_progression": [(2, 7)]},
    # ARTIFACTS
    # La generación de ALGUNOS artefactos únicos los está gestionando uniques.py
    "goblin_tooth_amulet": {"min_floor": 6, "max_instances": 1, "weight_progression": [(6, 7)]},
    #"grial": {"min_floor": 10, "max_instances": 1, "weight_progression": [(10, 4)]},
}

CAVERN_ITEM_SPAWN_RULES = ITEM_SPAWN_RULES


# Configuración de monstruos con los mismos campos que ITEM_SPAWN_RULES.
ENEMY_SPAWN_RULES = {
    "adventurer": {
        "min_floor": 2, 
        "weight_progression": [
            (1, 0),
            (2, 2),
            (3, 4),
            (4, 6),
            (8, 4),
            (15, 0),
            ],
    },
    # Campfires: 10% chance up to floor 12, then drop 3% per floor.
    "campfire": {
        "min_floor": 2,
        "weight_progression": [
            (2, 10),
            (13, 7),
            (14, 4),
            (15, 1),
            (16, 0),
        ],
    },
    "slime": {"min_floor": 2, "weight_progression": [(2, 10), (3, 15), (5, 10)]},
    "snake": {"min_floor": 2, "weight_progression": [(2, 10), (4, 10), (8, 0)]},
    "rat": {"min_floor": 2, "weight_progression": [(2, 50), (3, 4)]},
    "swarm_rat": {"min_floor": 2, "weight_progression": [(2, 50), (3, 20), (6, 10), (8, 0)]},
    "cave_bat": {"min_floor": 2, "weight_progression": [(2, 25), (3, 18), (5, 10), (6, 3)]},
    "goblin": {"min_floor": 2, "weight_progression": [(2, 100), (4, 50), (6, 20), (10, 15)]},
    "grey_goblin": {"min_floor": 7, "weight_progression": [(7, 15)]},
    "monkey": {"min_floor": 2, "weight_progression": [(2, 10), (4, 0)]},
    "orc": {"min_floor": 3, "weight_progression": [(4, 10), (4, 15), (5, 25), (6, 35), (9, 0)]},
    "true_orc": {"min_floor": 6, "weight_progression": [(6, 5), (8, 20), (10, 0)]},
    "skeleton": {"min_floor": 5, "weight_progression": [(5, 7), (5, 10), (6, 10), (11, 40), (12, 0)]},
    "troll": {"min_floor": 5, "weight_progression": [(7, 5), (8, 0)]},
    "bandit": {"min_floor": 8, "weight_progression": [(8, 10)]},
    "cultist": {"min_floor": 7, "weight_progression": [(7, 9), (8, 70), (9, 20), (10, 7), (11, 0)]},
}

PROFICIENCY_LEVELS = {
    "Beginner": 0.5, 
    "Novice": 1.0, 
    "Apprentice": 1.5, 
    "Adept": 2.0, 
    "Expert": 2.5, 
    "Master": 4.0
    }
