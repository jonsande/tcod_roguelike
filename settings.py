import tcod
from random import randint

# -- GRAPHICS ------------------------------------------------
# NOTA: cargas data/graphics/bob20x20.png con tcod.tileset.CHARMAP_CP437, así que cada casilla del PNG se asigna a un código CP437 y no a una tecla física del teclado.
# Como la hoja tiene 16 columnas, el índice del tile se calcula index = x + y * 16 (tomando x y y desde 0, con x=0 en la primera columna y y=0 en la primera fila). Ese índice se usa para buscar el código Unicode real: codepoint = tcod.tileset.CHARMAP_CP437[index] y glyph = chr(codepoint).
# Por ejemplo: supongamos x=1, y=12: index = 1 + 12*16 = 193, codepoint = 193 y el carácter correspondiente es '╣' (U+2563). En el código lo puedes usar como ord('╣'), '\u2563' o incluso tcod.tileset.CHARMAP_CP437[193] al definir el graphic del tile.
# Muchos de esos símbolos no existen como tecla dedicada, por lo que siempre es mejor referirte a ellos por su código (número CP437/Unicode) o pegando el símbolo literal. Si necesitas revisar otros índices, un snippet como el siguiente te imprime cualquier casilla:
# Se pueden copiar los símbolos aquí: 
# https://en.wikipedia.org/wiki/Code_page_437
# https://es.wikipedia.org/wiki/P%C3%A1gina_de_c%C3%B3digos_437

GRAPHIC_MODE = "pseudo_ascii"

if GRAPHIC_MODE == "pseudo_ascii":
    tileset_cod = "pseudo_ascii"
    # 16x16 son el número de casillas en las que se va a dividir el png: 16 ancho x 16 de alto
    tileset = tcod.tileset.load_tilesheet("data/graphics/bob20x20_chest_3.png", 16, 16, tcod.tileset.CHARMAP_CP437)

if GRAPHIC_MODE == "ascii":
    tileset_cod = "ascii"
    #tileset = tcod.tileset.load_tilesheet("data/graphics/bob20x20.png", 16, 16, tcod.tileset.CHARMAP_CP437)
    
    #tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin.ttf", 64, 64)
    #tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin.ttf", 60, 58)
    tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin.ttf", 128, 128)
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

# -- Intro cinematic ----------------------------------------------------
# Controla si se muestra una breve introducción al iniciar una nueva partida.
INTRO_ENABLED = True
INTRO_FADE_DURATION = 2.7  # segundos para fundir a negro o desde él
INTRO_SLIDE_DURATION = 3.5  # tiempo en pantalla antes de iniciar el fundido
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

# -- Audio settings ------------------------------------------------------
# Configuración de audio movida a audio_settings.py

# -- Development helpers ------------------------------------------------------
# Si está activo, el jugador lo ve todo (FOV enorme) y los muros no bloquean la visión.
GOD_MODE = False
GOD_MODE_STEALTH = False
DEBUG_MODE = True # Con la tecla BACKSPACE se hace un ipdb.set_trace() y se pueden ejecutar órdenes desde consola.

# -- Game settings ------------------------------------------------------

INTRO_MESSAGE = "After a long journey, you find the entrance to the dungeon."

# -- Player progression -------------------------------------------------------
# Permite activar/desactivar el sistema de subida de nivel del jugador.
# Cambia a True si quieres recuperar los mensajes y el menú de subida de niveles por
# xp en el futuro.
PLAYER_LEVELING_ENABLED = False

# -- Player starting gear -----------------------------------------------------
# Cada entrada indica el objeto (clave en entity_factories) con el que empieza el
# jugador. `quantity` permite añadir varias copias y `equip` marca si se intenta
# equipar esa copia en cuanto empiece la partida.
PLAYER_STARTING_INVENTORY = [
    # {"item": "dagger", "equip": True},
    # {"item": "leather_armor", "equip": True},
    # {"item": "dagger", "quantity": 3},
    {"item": "triple_ration", "quantity": 2},
]
# Límite superior de piezas equipadas automáticamente por tipo de ranura.
PLAYER_STARTING_EQUIP_LIMITS = {
    "weapon": 2,
    "armor": 2,
    "artefact": 2,
    "ring": 2,
}

# -- Dungeon generation ------------------------------------------------
# Forzar un estilo concreto de muro (1, 2 o 3). Usa None para dejarlo al azar.
# TODO: si WALL_STYLE es None, ahora mismo se genera toda la mazmorra con un 
# sólo estilo. Debería hacerse la tirada por cada nivel, de forma que pueda pasar
# que en el nivel 2 el WALL_STYLE es 1 pero en el nivel 3 es 1, por ejemplo.
WALL_STYLE = None

# -- Dungeon structure -------------------------------------------------------
TOTAL_FLOORS = 16
MAX_DOORS_BY_LEVEL = 8
MAX_BREAKABLE_WALLS = 6

# -- Fixed dungeon floors ----------------------------------------------------
# Cada entrada permite asignar una planta a una plantilla fija definida en fixed_maps.py.
# `map` debe corresponder con el nombre de la plantilla y `walls`/`walls_special`
# con los identificadores de baldosas de tile_types.py.
FIXED_DUNGEON_LAYOUTS = {
    # 6: {
    #     "map": "temple",
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
    0: [("debris_a", 30)],
    3: [("debris_a", 20)],
    6: [("debris_a", 10)],
}

# -- Chest generation -------------------------------------------------
# Probabilidad de que aparezca un cofre en cada nivel (0-1, por nivel mínimo).
# TODO: averiguar qué pasa en los niveles que no tengan aquí una configuración asignada.
CHEST_SPAWN_CHANCES = [
    (2, 0.20),
    (4, 0.20),
    (8, 0.20),
]
# Rango (mínimo, máximo) de objetos generados en cofres por nivel mínimo.
# TODO: averiguar qué pasa en los niveles que no tengan aquí una configuración asignada.
CHEST_ITEM_COUNT_BY_FLOOR = [
    (1, (1, 1)), # En el primer nivel se genera siempre un cofre junto al viejo.
    (4, (1, 3)),
    (8, (1, 3)),
]

OLD_MAN_CHEST = ["dagger", "leather_armor"]

# Listado de todos los objetos. Útil para las CHEST_LOOT_TABLES
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
    ("lightning_scroll", 1),
    ("fireball_scroll", 1),
    ("descend_scroll", 1),
    ("teleport_scroll", 1),
    ("prodigious_memory_scroll", 1),
    ("chain_mail", 1),
    ("leather_armor", 1),
    ("short_sword", 1),
    ("short_sword_plus", 1),
    ("long_sword", 1),
    ("long_sword_plus", 1),
    ("spear", 1),
    ("spear_plus", 1),
    ("poisoned_triple_ration", 1),
    ("triple_ration", 1),
    ("banana", 1),
    ]
# Tablas de botín por nivel mínimo: lista de (id_objeto, peso relativo).
# TODO: averiguar qué pasa en los niveles que no tengan aquí una configuración asignada.
CHEST_LOOT_TABLES = {
    1: [
        ("accuracy_ring", 1), 
        ("plain_ring", 1),
    ],
    2: [
        ("dagger", 1),
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
    ],
    3: ALL_ITEMS,
    8: [
        ("short_sword_plus", 2),
        ("spear_plus", 2),
        ("chain_mail", 1),
        ("fireball_scroll", 2),
        ("paralisis_scroll", 2),
        ("accuracy_ring", 2),
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
        ("lightning_scroll", 1),
        ("fireball_scroll", 1),
        ("descend_scroll", 1),
        ("teleport_scroll", 1),
        ("prodigious_memory_scroll", 1),
    ],
}

# -- Fixed room templates -----------------------------------------------------
# Probabilidad (por nivel mínimo) de sustituir una sala generada por cada plantilla fija.
FIXED_ROOM_CHANCES = {
    # BUG: Generan a veces mapas sin camino transitable desde unas escaleras a otras
    # "room_01": [(1, 0.08), (6, 0.08)],
    # "room_secret": [(1, 0.10), (8, 0.10)],
    # "room_door": [(1, 0.08), (5, 0.08)],
    # "room_secret_B": [(1, 0.08), (8, 0.08)],
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
        "room_max_size": 12,
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
CAVERN_MONSTER_COUNT_BY_FLOOR = [(1, (8, 14))]
# Cavern-specific spawn rules follow the same schema as ENEMY_SPAWN_RULES.
CAVERN_MONSTER_SPAWN_RULES = {
    "snake": {"min_floor": 1, "weight_progression": [(1, 15), (4, 6), (7, 2)]},
    "goblin": {"min_floor": 1, "weight_progression": [(1, 10), (3, 20), (5, 15)]},
    "orc": {"min_floor": 3, "weight_progression": [(3, 12), (6, 25), (9, 10)]},
    "cave_bat": {"min_floor": 1, "weight_progression": [(1, 18), (4, 10), (7, 3)]},
    "skeleton": {"min_floor": 4, "weight_progression": [(4, 5), (7, 10)]},
}

# -- Cavern item population ---------------------------------------------------
# Rango (mínimo, máximo) de ítems colocados libremente en cuevas por nivel mínimo.
CAVERN_ITEM_COUNT_BY_FLOOR = [
    (1, (0, 1)),
    (2, (10, 20)),
    (3, (1, 2)),
    (5, (2, 4)),
]
# Tabla específica de cuevas reutilizando el mismo formato que ITEM_SPAWN_RULES.
CAVERN_ITEM_SPAWN_RULES = {
    "health_potion": {"min_floor": 1, "weight_progression": [(1, 6), (4, 3)]},
    "stamina_potion": {"min_floor": 2, "weight_progression": [(2, 5), (5, 3)]},
    "confusion_scroll": {"min_floor": 3, "weight_progression": [(3, 2), (6, 4)]},
    "sand_bag": {"min_floor": 1, "weight_progression": [(1, 2), (4, 1)]},
}

# -- Column decorations -------------------------------------------------------
# Probabilidad de que las salas generadas (rectangulares, circulares, elípticas o en cruz) aparezcan con columnas.
ROOM_DECORATION_CHANCE = {
    "rectangle": 0.10,
    "circle": 0.12,
    "ellipse": 0.07,
    "cross": 0.07,
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
# En procgen.py, la función place_entities se llama para cada habitación generada.
# Ahora bien; el elemento (1, 1), por ejemplo, quiere decir que para el nivel 1 SE PUEDE
# generar un máximo de 1 item. No quiere decir que se vaya a generar. Lo que hará la fun-
# ción place_entities() de procgen.py es una randint(0,1) para determinar si ese 1 máximo
# se traduce o no en un ítem. 
MAX_ITEMS_BY_FLOOR = [
    #(0, 0),
    (1, 0),
    (2, 1),
    (3, 1),
    (4, 1),
    (6, 1),
    (7, randint(1, 2)),
    (11, 1),
    (12, 1),
]

# Máximo de monstruos por habitación según el nivel del piso.
MAX_MONSTERS_BY_FLOOR = [
    #(1, 0),
    (2, 1),
    (3, 1),
    (5, randint(1,2)),
    (6, 0),
    (7, 1),
    (11, randint(1,2)),
]

# -- Campfires --------------------------------------------------------------
CAMPFIRE_MIN_HP = 35
CAMPFIRE_MAX_HP = 320
# Chance (0-1) to spawn a nearby cache item when a campfire is placed.
CAMPFIRE_CACHE_ITEM_CHANCE = 0.15
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
ADVENTURER_COLOR = (150, 150, 150)
ADVENTURER_CORPSE_CHAR = "%"
ADVENTURER_CORPSE_COLOR = (100, 100, 100)
ADVENTURER_CORPSE_NAME = "Remains of an adventurer"
# Base probability (0-1) added per floor after they descend to find their corpse.
ADVENTURER_CORPSE_CHANCE_PER_FLOOR = 0.04

# -- Loot generation -----------------------------------------------------------
# Configuración de botín/objetos. Cada entrada permite controlar:
# - min_floor: nivel mínimo en el que empieza a considerarse.
# - max_instances: número máximo de copias (None = ilimitado).
# - base_weight: peso base a partir de min_floor cuando no se usa weight_progression.
# - weight_per_floor: crecimiento lineal aplicado a partir de min_floor.
# - weight_progression: lista de (nivel, peso) que sobreescribe el peso a partir de ese nivel.
ITEM_SPAWN_RULES = {
    # HI VALUE POTIONS
    "strength_potion": {"min_floor": 2, "max_instances": 8, "base_weight": 8, "weight_progression": [(3, 2)]},
    "increase_max_stamina": {"min_floor": 2, "max_instances": 8, "base_weight": 8, "weight_progression": [(3, 2)]},
    "life_potion": {"min_floor": 2, "max_instances": 8, "base_weight": 8, "weight_progression": [(3, 2)]},
    "infra_vision_potion": {"min_floor": 2, "max_instances": 8, "base_weight": 8, "weight_progression": [(2, 6)]},
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
    "lightning_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(1, 7), (4, 10), (4, 10)]},
    "fireball_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(1, 7), (4, 10), (4, 10)]},
    "descend_scroll": {"min_floor": 2, "max_instances": 4, "weight_progression": [(3, 2), (6, 3)]},
    "teleport_scroll": {"min_floor": 2, "max_instances": 6, "weight_progression": [(2, 3), (5, 4)]},
    "prodigious_memory_scroll": {"min_floor": 5, "max_instances": 2, "weight_progression": [(5, 1), (8, 2)]},
    # ARMOR
    "chain_mail": {"min_floor": 5, "weight_progression": [(5, 5)]},
    "leather_armor": {"min_floor": 2, "weight_progression": [(2, 5)]},
    # RINGS
    "accuracy_ring": {"min_floor": 2, "max_instances": 1, "weight_progression": [(1, 2), (4, 7), (6, 9)]},
    "plain_ring": {"min_floor": 2, "max_instances": 8, "weight_progression": [(1, 2), (4, 7), (6, 9)]},
    # OTHER
    "rock": {"min_floor": 2, "weight_progression": [(2, 15), (3, 45)]},
    "table": {"min_floor": 2, "weight_progression": [(2, 15)]},
    "note_wizard_1": {"min_floor": 2, "max_instances": 1, "weight_progression": [(2, 7)]},
    # ARTIFACTS
    # La generación de artefactos únicos los está gestionando uniques.py
    #"goblin_tooth_amulet": {"min_floor": 7, "max_instances": 1, "weight_progression": [(7, 4)]},
    #"grial": {"min_floor": 10, "max_instances": 1, "weight_progression": [(10, 4)]},
}

# Configuración de monstruos con los mismos campos que ITEM_SPAWN_RULES.
ENEMY_SPAWN_RULES = {
    "adventurer": {
        "min_floor": 1, 
        "weight_progression": [
            (1, 7),
            (2, 7),
            (3, 7),
            (4, 6),
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
    "snake": {"min_floor": 1, "weight_progression": [(1, 10)]},
    "rat": {"min_floor": 1, "weight_progression": [(1, 50), (3, 0)]},
    "swarm_rat": {"min_floor": 3, "weight_progression": [(3, 20), (6, 10)]},
    "cave_bat": {"min_floor": 1, "weight_progression": [(1, 25), (3, 18), (5, 10), (7, 3)]},
    "goblin": {"min_floor": 1, "weight_progression": [(1, 10), (2, 50), (4, 30), (6, 20), (10, 15)]},
    "monkey": {"min_floor": 1, "weight_progression": [(1, 8), (2, 10), (4, 0)]},
    "orc": {"min_floor": 3, "weight_progression": [(3, 10), (4, 15), (5, 25), (6, 35), (9, 20)]},
    "true_orc": {"min_floor": 5, "weight_progression": [(5, 5), (8, 20)]},
    "skeleton": {"min_floor": 4, "weight_progression": [(4, 15), (6, 18), (9, 12)]},
    "troll": {"min_floor": 5, "weight_progression": [(7, 5)]},
    "bandit": {"min_floor": 8, "weight_progression": [(8, 10)]},
    "cultist": {"min_floor": 6, "weight_progression": [(6, 8), (9, 16)]},
}

PROFICIENCY_LEVELS = {
    "Beginner": 0.5, 
    "Novice": 1.0, 
    "Apprentice": 1.5, 
    "Adept": 2.0, 
    "Expert": 2.5, 
    "Master": 4.0
    }
