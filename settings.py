import tcod
from random import randint

LANGUAGE = "es"  # Idioma activo de la interfaz. Opciones: en, es.
FALLBACK_LANGUAGE = "en"  # Idioma al que se recurre si falta una cadena.

# -- SCREEN PRESETS -----------------------------------------------------
# [EXPERIMENTAL] Permite elegir el tamaño de pantalla desde settings.py.
# ADVERTENCIA!: Dado que con el tamaño "LARGE" aumenta el tamaño del mapa,
# el número de habitaciones (y entidades) por nivel aumenta también. Ello
# tiene también un considerable impacto en el rendimieto del juego (debido
# fundamentalmente al número de criaturas por nivel y las demandas para el
# procesamiento del pathfinding de estas).
# Este comportamiento se puede modificar más abajo, desrelativizando los
# parámetros del generador en la sección "Dungeon generation".
# Opciones disponibles: "STANDARD" (80x44), "MEDIUM" (90X50) o "LARGE" (100x55).
SCREEN_MODE = "STANDARD"

_BASE_SCREEN = {"width": 80, "height": 44, "map_width": 80, "map_height": 36}
_SCREEN_PRESETS = {
    "STANDARD": {"width": 80, "height": 44},
    "MEDIUM": {"width": 90, "height": 50},
    "LARGE": {"width": 100, "height": 55},
}
_BASE_HUD = {
    "stats_row": 37,
    "bar_total_width": 15,
    "hp_label_x": 1,
    "hp_value_x": 5,
    "sp_label_x": 12,
    "sp_value_x": 16,
    "combat_label_x": 20,
    "combat_hit_x": 30,
    "combat_def_x": 40,
    "fortify_x": 20,
    "dungeon_level_first": (60, 37),
    "dungeon_level_other": (69, 37),
    "message_log": {"x": 1, "y": 39, "width": 60, "height": 4},
    "monster_panel": {
        "x_left": 0,
        "y": 0,
        "width": 38,
        "height": 36,
        "player_threshold": 39,
    },
}


def _compute_screen_config(mode: str) -> dict:
    preset = _SCREEN_PRESETS.get(mode.upper(), _SCREEN_PRESETS["STANDARD"])
    screen_width = int(preset["width"])
    screen_height = int(preset["height"])

    scale_x = screen_width / _BASE_SCREEN["width"]
    scale_y = screen_height / _BASE_SCREEN["height"]

    def sx(value: int) -> int:
        return int(round(value * scale_x))

    def sy(value: int) -> int:
        return int(round(value * scale_y))

    map_width = max(1, sx(_BASE_SCREEN["map_width"]))
    map_height = max(1, sy(_BASE_SCREEN["map_height"]))

    base_log = _BASE_HUD["message_log"]
    log_width = max(10, min(screen_width - sx(base_log["x"]), sx(base_log["width"])))
    log_height = max(3, sy(base_log["height"]))
    log_y = min(sy(base_log["y"]), max(0, screen_height - log_height))

    mp_base = _BASE_HUD["monster_panel"]
    mp_width = max(12, sx(mp_base["width"]))
    mp_height = max(6, min(screen_height, sy(mp_base["height"])))
    mp_y = min(sy(mp_base["y"]), max(0, screen_height - mp_height))
    mp_threshold = sx(mp_base["player_threshold"])
    mp_x_left = sx(mp_base["x_left"])
    mp_x_right = max(0, screen_width - mp_width - 1)

    hud = {
        "stats_row": sy(_BASE_HUD["stats_row"]),
        "bar_total_width": max(1, sx(_BASE_HUD["bar_total_width"])),
        "hp_label_x": sx(_BASE_HUD["hp_label_x"]),
        "hp_value_x": sx(_BASE_HUD["hp_value_x"]),
        "sp_label_x": sx(_BASE_HUD["sp_label_x"]),
        "sp_value_x": sx(_BASE_HUD["sp_value_x"]),
        "combat_label_x": sx(_BASE_HUD["combat_label_x"]),
        "combat_hit_x": sx(_BASE_HUD["combat_hit_x"]),
        "combat_def_x": sx(_BASE_HUD["combat_def_x"]),
        "fortify_x": sx(_BASE_HUD["fortify_x"]),
        "dungeon_level_first": (
            sx(_BASE_HUD["dungeon_level_first"][0]),
            sy(_BASE_HUD["dungeon_level_first"][1]),
        ),
        "dungeon_level_other": (
            sx(_BASE_HUD["dungeon_level_other"][0]),
            sy(_BASE_HUD["dungeon_level_other"][1]),
        ),
        "message_log": {
            "x": sx(base_log["x"]),
            "y": log_y,
            "width": log_width,
            "height": log_height,
        },
        "monster_panel": {
            "x_left": mp_x_left,
            "x_right": mp_x_right,
            "y": mp_y,
            "width": mp_width,
            "height": mp_height,
            "player_threshold": mp_threshold,
        },
    }

    return {
        "screen_width": screen_width,
        "screen_height": screen_height,
        "map_width": map_width,
        "map_height": map_height,
        "hud": hud,
    }


SCREEN_CONFIG = _compute_screen_config(SCREEN_MODE)
SCREEN_WIDTH = SCREEN_CONFIG["screen_width"]
SCREEN_HEIGHT = SCREEN_CONFIG["screen_height"]
MAP_WIDTH = SCREEN_CONFIG["map_width"]
MAP_HEIGHT = SCREEN_CONFIG["map_height"]
HUD_LAYOUT = SCREEN_CONFIG["hud"]

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
    #tileset = tcod.tileset.load_truetype_font("data/graphics/PxPlus_IBM_CGAthin.ttf", 112, 128)
    

    # EXPERIMENTAL
    ## Ventana 1920x10880
    #tileset = tcod.tileset.load_truetype_font("data/graphics/UbuntuMono-Regular.ttf", 16, 20)
    ## Ventana 1366x768
    #tileset = tcod.tileset.load_truetype_font("data/graphics/UbuntuMono-Regular.ttf", 11, 14)


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
STAIR_TRANSITION_STEPS = 8
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
GOD_MODE = False
GOD_MODE_STEALTH = False
DEBUG_MODE = True # Con la tecla BACKSPACE se hace un ipdb.set_trace() y se pueden ejecutar órdenes desde consola.
DEBUG_DRAW_HOT_PATH = False

# Flag temporal para desactivar el sistema de ocultación del jugador.
# Advertencia: mantener desactivado. Entra en conflicto con ScoutV3 y, por lo demás,
# actualmente no es necesaria esta mecánica, ya que es posible hacer un backstab posicionándose
# a la vuelta de una puerta o esquina si se tiene el stealth suficiente.
STEALTH_DISABLED = True

# -- Análisis y configuración de rendimiento ----------------------------
# Telemetría ligera de rendimiento por turno (se muestra cada N turnos).
PERF_PROFILER_ENABLED = False
PERF_PROFILER_REPORT_INTERVAL = 20
# Si está activo, cada mensaje del log también se imprime en stdout.
LOG_ECHO_TO_STDOUT = True

# Número de turnos que se mantiene una ruta de IA antes de recalcularla si no hay bloqueos.
AI_PATH_RECALC_INTERVAL = 4
# Radio (Chebyshev) hasta el que se usa un BFS barato; más lejos se usa A*.
AI_PATH_BFS_RADIUS = 10
# Intentos de ruta fallida antes de rendirse temporalmente.
AI_PATH_FAILURE_LIMIT = 8
# Distancia máxima (Chebyshev) de persecución antes de perder el agro.
AI_MAX_PURSUIT_RANGE = 25
# Turnos consecutivos sin ver/oír al objetivo antes de perder agro; se suma a la agresividad de la criatura.
AI_AGGRO_LOSS_BASE = 3
# Turnos base que los guardianes buscan un objetivo tras perderlo de vista.
WARDEN_SEARCH_TURNS = 5

# -- Game settings ------------------------------------------------------

if LANGUAGE == "es":
    INTRO_MESSAGE = "Tras un largo viaje, finalmente encuentras la entrada al laberinto."
else:
    INTRO_MESSAGE = "After a long journey, you find the entrance to the labyrinth."

# Si está activo, todo el inventario pendiente se identifica automáticamente al morir.
AUTO_IDENTIFY_INVENTORY_ON_DEATH = True

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
    {"item": "triple_ration", "quantity": 1},
    # {"item": "accuracy_ring", "equip": True},
    # {"item": "leather_armor", "equip": True},
    {"item": "dagger", "quantity": 1, "equip": True},
    # {"item": "long_bow", "quantity": 1},
    # {"item": "arrow", "quantity": 20},
    #{"item": "spear", "quantity": 1, "equip": True},
    #{"item": "descend_scroll", "quantity": 16},
    #{"item": "black_key", "quantity": 1},
    #{"item": "red_key", "quantity": 1},
    #{"item": "white_key", "quantity": 1},
    #{"item": "gray_key", "quantity": 1},
    #{"item": "identify_scroll", "quantity": 6},
    #{"item": "antidote_ring", "quantity": 1},
    #{"item": "infra_vision_potion", "quantity": 5},
    #{"item": "confusion_potion", "quantity": 3},
    #{"item": "identify_scroll", "quantity": 9},
    #{"item": "sand_bag", "quantity": 2},
    #{"item": "scout_hood", "quantity": 1},
    #{"item": "cloak", "quantity": 1},
    #{"item": "tunneling_staff", "quantity": 1},
    # {"item": "long_bow", "quantity": 1},
    # {"item": "arrow", "quantity": 15},
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
# Forzar un estilo concreto de muro (1, 2, 3 o 4). Usa None para dejarlo al azar.
# TODO: si WALL_STYLE es None, ahora mismo se genera toda la mazmorra con un 
# sólo estilo. Debería hacerse la tirada por cada nivel, de forma que pueda pasar
# que en el nivel 2 el WALL_STYLE es 1 pero en el nivel 3 es 1, por ejemplo.
WALL_STYLE = None

# Parámetros experimentales para generate_dungeon_v3().
if SCREEN_MODE == "STANDARD":
    DUNGEON_V3_MIN_ROOMS = 8
    DUNGEON_V3_MAX_ROOMS = 20
    DUNGEON_V3_ROOM_MIN_SIZE = 3
    DUNGEON_V3_ROOM_MAX_SIZE = 8
    DUNGEON_V3_MAX_PLACEMENT_ATTEMPTS = 220
    DUNGEON_V3_PADDING = 1  # Espacio mínimo entre salas
    DUNGEON_V3_EXTRA_CONNECTION_CHANCE = 0.35
    DUNGEON_V3_EXTRA_CONNECTIONS = 3
    DUNGEON_V3_LOCKED_DOOR_CHANCE = 0.50

elif SCREEN_MODE == "MEDIUM":
    DUNGEON_V3_MIN_ROOMS = 10
    DUNGEON_V3_MAX_ROOMS = 28
    DUNGEON_V3_ROOM_MIN_SIZE = 3
    DUNGEON_V3_ROOM_MAX_SIZE = 11
    DUNGEON_V3_MAX_PLACEMENT_ATTEMPTS = 520
    DUNGEON_V3_PADDING = 1  # Espacio mínimo entre salas
    DUNGEON_V3_EXTRA_CONNECTION_CHANCE = 0.35
    DUNGEON_V3_EXTRA_CONNECTIONS = 3
    DUNGEON_V3_LOCKED_DOOR_CHANCE = 0.50

elif SCREEN_MODE == "LARGE":
    DUNGEON_V3_MIN_ROOMS = 15
    DUNGEON_V3_MAX_ROOMS = 32
    DUNGEON_V3_ROOM_MIN_SIZE = 3
    DUNGEON_V3_ROOM_MAX_SIZE = 12
    DUNGEON_V3_MAX_PLACEMENT_ATTEMPTS = 620
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
    "Warden",
]

# Probabilidad de que la llave aparezca dentro de un cofre existente en la planta.
KEY_CHEST_SPAWN_CHANCE = 0.75
# Si existe una rama secundaria accesible desde pisos anteriores válidos, probabilidad
# de que la llave se coloque en esa rama en lugar del tronco principal.
KEY_BRANCH_SPAWN_CHANCE = 0.99

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

# -- Dungeon branches --------------------------------------------------------
# Pisos (1-indexed) del tronco principal donde pueden generarse ramas secundarias.
# No se generan ramas en el último nivel ni en niveles fijos.
BRANCH_FLOORS = [randint(3,6), randint(7,14)]
# Número máximo de ramas secundarias por mundo.
MAX_SECONDARY_BRANCHES = 2
# Longitud mínima/máxima de cada rama (en niveles).
BRANCH_MIN_LENGTH = 2
BRANCH_MAX_LENGTH = 3
# Generadores permitidos en ramas secundarias (elige entre: "dungeon_v3", "cavern").
BRANCH_GENERATORS = ["dungeon_v3"]
# Si True, las escaleras de ramas en cavernas se pueden colocar en cualquier casilla transitable.
BRANCH_CAVERN_STAIRS_ANYWHERE = True

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
    8: {
        "map": "three_doors",
        "walls": "wall_v2",
        "walls_special": "wall_v1",
    },
    9: {
        "map": "the_library",
        "walls": "wall_v1",
        "walls_special": "wall_v2",
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
    ("bones", 1),
    ("tunneling_staff", 1),
    ("long_bow", 1),
    ("arrow", 1)
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
    # 2: [
    #     # ("dagger", 1),
    #     # ("leather_armor", 1),
    #     ("strength_potion", 1), 
    #     ("increase_max_stamina", 1), 
    #     ("life_potion", 1), 
    #     ("infra_vision_potion", 1), 
    #     ("antidote", 1), 
    #     ("health_potion", 1), 
    #     ("poison_potion", 1), 
    #     ("power_potion", 1), 
    #     ("stamina_potion", 1), 
    #     ("temporal_infra_vision_potion", 1), 
    #     ("blindness_potion", 1), 
    #     ("confusion_potion", 1), 
    #     ("paralysis_potion", 1), 
    #     ("petrification_potion", 1), 
    #     ("precission_potion", 1),
    #     ("strength_ring", 1),
    #     ("farsight_ring", 1),
    #     ("vigor_ring", 1),
    #     ("antidote_ring", 1),
    #     ("memory_ring", 1),
    #     ("recovery_ring", 1),
    #     ("guard_ring", 1),
    #     ("fortune_ring", 1),
    #     ("cursed_weakness_ring", 1),
    #     ("cursed_myopia_ring", 1),
    #     ("cursed_fatigue_ring", 1),
    #     ("cursed_lethargy_ring", 1),
    #     ("cursed_vulnerability_ring", 1),
    #     ("cursed_misfortune_ring", 1),
    #     ("remove_curse_scroll", 1),
    # ],
    2: ALL_ITEMS,
    # 8: [
    #     ("short_sword_plus", 2),
    #     ("spear_plus", 2),
    #     ("chain_mail", 1),
    #     ("fireball_scroll", 2),
    #     ("paralisis_scroll", 2),
    #     ("accuracy_ring", 2),
    #     ("strength_ring", 2),
    #     ("farsight_ring", 2),
    #     ("vigor_ring", 2),
    #     ("antidote_ring", 2),
    #     ("memory_ring", 1),
    #     ("recovery_ring", 2),
    #     ("guard_ring", 2),
    #     ("fortune_ring", 1),
    #     ("cursed_weakness_ring", 2),
    #     ("cursed_myopia_ring", 2),
    #     ("cursed_fatigue_ring", 2),
    #     ("cursed_lethargy_ring", 2),
    #     ("cursed_vulnerability_ring", 2),
    #     ("cursed_misfortune_ring", 2),
    #     ("strength_potion", 2), 
    #     ("increase_max_stamina", 2), 
    #     ("life_potion", 2), 
    #     ("infra_vision_potion", 2), 
    #     ("antidote", 1),
    #     ("health_potion", 1), 
    #     ("poison_potion", 1), 
    #     ("power_potion", 1), 
    #     ("stamina_potion", 1), 
    #     ("temporal_infra_vision_potion", 1), 
    #     ("blindness_potion", 1), 
    #     ("confusion_potion", 1), 
    #     ("paralysis_potion", 1), 
    #     ("petrification_potion", 1), 
    #     ("precission_potion", 1),
    #     ("confusion_scroll", 1),
    #     ("paralisis_scroll", 1),
    #     ("identify_scroll", 1),
    #     ("remove_curse_scroll", 1),
    #     ("lightning_scroll", 1),
    #     ("fireball_scroll", 1),
    #     ("descend_scroll", 1),
    #     ("teleport_scroll", 1),
    #     ("prodigious_memory_scroll", 1),
    #     ("remove_curse_scroll", 1),
    #     ("leather_cap", 1),
    #     ("scout_hood", 1),
    #     ("iron_helmet", 1),
    #     ("orcish_war_helm", 1),
    # ],
    # 9: ALL_ITEMS,
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
        ("generated_book", 3), # Generador de libros
        # Libros estáticos
        ("forgotten_canticle", 3),
        ("architect_notes", 3),
        ("red_tower_mails", 3),
        ("tired_librarian_notes", 3),
        ("wanderers_diary", 3),
        ("sixteen_rings", 3),
        ("lower_cavern_bestiary", 3),
        ("crack_finder_book", 3),
        ("coal_stories", 3),
        ("nine_lanterns_codex", 3),
        ("living_stoone_theory", 3),
        ("fungi_book", 3),
        ("corridor_chronicles", 3),
        # Libros con pistas
        ("library_clue_1", 3),
        ("library_clue_2", 3),
        ("library_clue_3", 3),
        ("library_clue_4", 3),
        ("library_clue_5", 3),
        ("library_clue_6", 3),
        ("note_wizard_1", 3),
        ("triple_ration", 1),
        # Otros
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
        ("arrow", 1)
    ],
}

# Cada clave marca el nivel mínimo y lista los ítems posibles con su peso.
BOOKSHELF_LOOT_TABLES = {
    2: [
        ("generated_book", 3), # Generador de libros
        # Libros estáticos
        ("forgotten_canticle", 3),
        ("architect_notes", 3),
        ("red_tower_mails", 3),
        ("tired_librarian_notes", 3),
        ("wanderers_diary", 3),
        ("sixteen_rings", 3),
        ("lower_cavern_bestiary", 3),
        ("crack_finder_book", 3),
        ("coal_stories", 3),
        ("nine_lanterns_codex", 3),
        ("living_stoone_theory", 3),
        ("fungi_book", 3),
        ("corridor_chronicles", 3),
        # Libros con pistas
        ("library_clue_1", 3),
        ("library_clue_2", 3),
        ("library_clue_3", 3),
        ("library_clue_4", 3),
        ("library_clue_5", 3),
        ("library_clue_6", 3),
        ("note_wizard_1", 3),
        ("triple_ration", 1),
        # Otros
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
# Cada iteración de generación hace un sorteo por cada plantilla y luego elige una al azar 
# entre las que hayan salido “sí”. Con 7 plantillas al 6% cada una, la probabilidad de que 
# alguna salga es: 1 - (1 - 0.06)^7 ≈ 34% por habitación.
FIXED_ROOM_CHANCES = {
    # BUG: Generan a veces mapas sin camino transitable desde unas escaleras a otras
    "room_01": [(2, 0.01), (8, 0.00), (9, 0.01)],
    "room_02": [(2, 0.01), (8, 0.00), (9, 0.01)],
    "room_03": [(2, 0.01), (8, 0.00), (9, 0.01)],
    "room_04": [(2, 0.01), (8, 0.00), (9, 0.01)],
    "room_05": [(2, 0.01), (8, 0.00), (9, 0.01)],
    "room_06": [(2, 0.01), (8, 0.00), (9, 0.01)],
    "room_07": [(2, 0.01), (8, 0.00), (9, 0.01)],
}

UNIQUE_ROOMS_CHANCES = {
    "blue_chest_room": [(2, 0.05), (4, 0.75), (16, 0.0)],
}

# -- Procedural room shapes ---------------------------------------------------
# Probabilidades relativas de que una sala se genere como círculo, elipse o cruz (rectángulo siempre pesa 1.0).
ROOM_SHAPE_WEIGHTS = {
    "circle": 0.09,
    "ellipse": 0.09,
    "cross": 0.0,
}

# Tamaños mínimos requeridos (lado más corto) antes de permitir cada forma alternativa.
ROOM_MIN_SIZE_SHAPES = {
    "circle": 5,
    "ellipse": 5,
    "cross": 5,
}

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
    "orc": {"min_floor": 4, "weight_progression": [(5, 12), (7, 25), (10, 10)]},
    "orc_servant": {"min_floor": 4, "weight_progression": [(5, 12), (7, 25), (10, 10)]},
    "cave_bat": {"min_floor": 2, "weight_progression": [(1, 18), (4, 2), (7, 1)]},
    "skeleton": {"min_floor": 6, "weight_progression": [(5, 5), (7, 10)]},
    "slime": {"min_floor": 2, "weight_progression": [(2, 10), (3, 15), (5, 10)]},
    #"warden": {"min_floor": 6, "weight_progression": [(6, 4), (8, 10), (10, 0)]},
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
    "antidote": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "sand_bag": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "health_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "poison_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "power_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "stamina_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "temporal_infra_vision_potion": {"min_floor": 5, "weight_progression": [(2, 5)]},
    "blindness_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "confusion_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "paralysis_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "petrification_potion": {"min_floor": 6, "weight_progression": [(4, 5)]},
    "precission_potion": {"min_floor": 2, "weight_progression": [(2, 5)]},
    # WEAPONS
    "short_sword": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "short_sword_plus": {"min_floor": 2, "weight_progression": [(6, 5)]},
    "long_sword": {"min_floor": 2, "weight_progression": [(2, 5), (7, 6)]},
    "long_sword_plus": {"min_floor": 2, "weight_progression": [(7, 5)]},
    "spear": {"min_floor": 2, "weight_progression": [(2, 5), (7, 10)]},
    "spear_plus": {"min_floor": 2, "weight_progression": [(2, 3), (7, 5)]},
    "long_bow": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "arrow": {"min_floor": 2, "weight_progression": [(2, 5)]},
    # WANDS
    "tunneling_staff": {"min_floor": 3, "min_instances": 1, "max_instances": 1, "base_weight": 1},
    # FOOD
    "poisoned_triple_ration": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "triple_ration": {"min_floor": 2, "weight_progression": [(2, 5)]},
    "banana": {"min_floor": 2, "weight_progression": [(2, 1)]},
    # SCROLLS
    "confusion_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(4, 5)]},
    "paralisis_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(4, 5)]},
    "identify_scroll": {"min_floor": 2, "max_instances": 6, "weight_progression": [(4, 5)]},
    "remove_curse_scroll": {"min_floor": 3, "max_instances": 4, "weight_progression": [(4, 5)]},
    "lightning_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(4, 5)]},
    "fireball_scroll": {"min_floor": 2, "max_instances": 8, "weight_progression": [(4, 5)]},
    "descend_scroll": {"min_floor": 2, "max_instances": 4, "weight_progression": [(4, 5)]},
    "teleport_scroll": {"min_floor": 2, "max_instances": 6, "weight_progression": [(4, 5)]},
    "prodigious_memory_scroll": {"min_floor": 5, "max_instances": 2, "weight_progression": [(4, 5)]},
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
    "bones": {"min_floor": 2, "weight_progression": [(2, 90), (4, 20), (6, 5)]},
    "rock": {"min_floor": 2, "weight_progression": [(2, 15), (3, 45)]},
    "note_wizard_1": {"min_floor": 2, "max_instances": 1, "weight_progression": [(2, 5)]},
    # ARTIFACTS
    # La generación de ALGUNOS artefactos únicos los está gestionando uniques.py
    "goblin_tooth_amulet": {"min_floor": 6, "max_instances": 1, "weight_progression": [(6, 5)]},
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
    "goblin": {"min_floor": 2, "weight_progression": [(2, 40), (4, 50), (6, 20), (10, 15)]},
    "grey_goblin": {"min_floor": 7, "weight_progression": [(7, 15)]},
    "monkey": {"min_floor": 2, "weight_progression": [(2, 10), (4, 0)]},
    "orc": {"min_floor": 4, "weight_progression": [(4, 8), (5, 15), (6, 25), (11, 0)]},
    "orc_servant": {"min_floor": 2, "weight_progression": [(2, 4), (3, 6), (4, 10), (6, 35), (9, 0)]},
    "true_orc": {"min_floor": 6, "weight_progression": [(7, 5), (8, 20), (12, 0)]},
    "skeleton": {"min_floor": 5, "weight_progression": [(5, 7), (5, 10), (6, 10), (11, 40), (12, 0)]},
    "troll": {"min_floor": 5, "weight_progression": [(7, 5), (8, 0)]},
    "bandit": {"min_floor": 8, "weight_progression": [(8, 10)]},
    "cultist": {"min_floor": 7, "weight_progression": [(7, 9), (8, 70), (9, 20), (10, 7), (11, 0)]},
    #"warden": {"min_floor": 6, "weight_progression": [(6, 6), (8, 14), (10, 6), (12, 0)]},
}

PROFICIENCY_LEVELS = {
    "Beginner": 0.5, 
    "Novice": 1.0, 
    "Apprentice": 1.5, 
    "Adept": 2.0, 
    "Expert": 2.5, 
    "Master": 4.0
    }
