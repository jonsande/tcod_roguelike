"""Audio-related configuration."""

# Ambient loops --------------------------------------------------------------
AMBIENT_SOUND_ENABLED = True
AMBIENT_SOUND_VOLUME = 1.0  # 0.0 - 1.0
AMBIENT_SOUND_TRACKS = {
    # Puedes usar un string o una lista/tupla para elegir aleatoriamente entre varias pistas.
    1: [
        "data/audio/ambient/CO.AG_InTheHeartOfThisAncientCity.ogg",
        "data/audio/ambient/CO.AG_16_TheDesert.ogg",
    ],
    3: [
        "data/audio/ambient/CO.AG_DarkRooms.ogg",
        "data/audio/ambient/CO.AG_12_LetsRead.ogg",
    ],
    4: ["data/audio/ambient/CO.AG_09_ForTerror.ogg"],
}
# Se acepta string único o lista/tupla para escoger aleatoriamente.
AMBIENT_SOUND_DEFAULT_TRACK = [
    "data/audio/ambient/CO.AG_DarkRooms.ogg",
    "data/audio/ambient/CO.AG_09_ForTerror.ogg",
    "data/audio/ambient/CO.AG_12_LetsRead.ogg",
    "data/audio/ambient/CO.AG_22_Magnetic.ogg",
    "data/audio/ambient/underground_1.ogg",
]

# Player footsteps -----------------------------------------------------------
PLAYER_FOOTSTEP_SOUND_ENABLED = True
PLAYER_FOOTSTEP_SOUNDS = [
    "data/audio/sfx/walk/talmarc/walk_tarmac_1.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_2.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_3.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_4.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_5.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_6.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_7.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_8.ogg",
    "data/audio/sfx/walk/talmarc/walk_tarmac_9.ogg",
]
PLAYER_FOOTSTEP_VOLUME = 0.3  # 0.0 - 1.0

# Door interactions ----------------------------------------------------------
DOOR_OPEN_SOUND_ENABLED = True
DOOR_OPEN_SOUNDS = [
    # "data/audio/sfx/doors/open_1.ogg",
    "data/audio/sfx/doors/open_4.ogg",
    "data/audio/sfx/doors/open_5.ogg",
    "data/audio/sfx/doors/open_6.ogg",
    "data/audio/sfx/doors/open_7.ogg",
    "data/audio/sfx/doors/open_8.ogg",
    "data/audio/sfx/doors/open_9.ogg",
    
]
DOOR_OPEN_VOLUME = 0.25

DOOR_CLOSE_SOUND_ENABLED = True
DOOR_CLOSE_SOUNDS = [
    # "data/audio/sfx/doors/close_1.ogg",
    "data/audio/sfx/doors/close_1.ogg",
    "data/audio/sfx/doors/close_2.ogg",
    "data/audio/sfx/doors/close_3.ogg",
    "data/audio/sfx/doors/close_4.ogg",
    "data/audio/sfx/doors/close_5.ogg",
    "data/audio/sfx/doors/close_6.ogg",
    "data/audio/sfx/doors/close_7.ogg",
    "data/audio/sfx/doors/close_8.ogg",
    "data/audio/sfx/doors/close_9.ogg",
    "data/audio/sfx/doors/close_10.ogg",
]
DOOR_CLOSE_VOLUME = 0.25

# Item pickups --------------------------------------------------------------
ITEM_PICKUP_SOUND_ENABLED = True
ITEM_PICKUP_VOLUME = 0.4  # Volumen por defecto

POTION_PICKUP_SOUNDS = ["data/audio/sfx/pickup/Backpack.wav",]
POTION_PICKUP_SOUND = None # No entiendo por qué esta opción
POTION_PICKUP_VOLUME = None  # Usa ITEM_PICKUP_VOLUME cuando sea None

SCROLL_PICKUP_SOUNDS = ["data/audio/sfx/pickup/Backpack.wav",]
SCROLL_PICKUP_SOUND = None # No entiendo por qué esta opción
SCROLL_PICKUP_VOLUME = None

GENERIC_PICKUP_SOUNDS = ["data/audio/sfx/pickup/Backpack.wav",]
GENERIC_PICKUP_SOUND = None # No entiendo por qué esta opción
GENERIC_PICKUP_VOLUME = None

# Chest interactions --------------------------------------------------------
CHEST_OPEN_SOUND_ENABLED = True
CHEST_OPEN_SOUNDS = ["data/audio/sfx/chests/Chest_Open_1.ogg",
                     "data/audio/sfx/chests/Chest_Open_2.ogg",
                     ]
CHEST_OPEN_SOUND = None # No entiendo por qué esta opción
CHEST_OPEN_VOLUME = 0.4

# Campfire ambience ---------------------------------------------------------
CAMPFIRE_SOUND_ENABLED = True
CAMPFIRE_SOUNDS = ["data/audio/sfx/campfire/campfire_1.mp3",]
CAMPFIRE_SOUND = None
CAMPFIRE_VOLUME = 0.75

# Stair interactions --------------------------------------------------------
STAIR_DESCEND_SOUND_ENABLED = True
STAIR_DESCEND_SOUNDS = ["data/audio/sfx/stairs/Arcane_Symbol_Activate_01.wav",]
STAIR_DESCEND_SOUND = None
STAIR_DESCEND_VOLUME = 0.1

# Melee weapon attacks ------------------------------------------------------
MELEE_ATTACK_SOUND_ENABLED = True
MELEE_ATTACK_DEFAULT_VOLUME = 0.55

# Esto sólo es la plantilla, para usar más abajo
def _empty_melee_sound_entry():
    return {"hit_damage": {"tracks": [], "track": None, "volume": None},
            "hit_no_damage": {"tracks": [], "track": None, "volume": None},
            "miss": {"tracks": [], "track": None, "volume": None},}

MELEE_ATTACK_SOUNDS = {
    "dagger": {
        "hit_damage": {
            "tracks": [
                "data/audio/sfx/combat/Sword Impact Hit 1.ogg",
                "data/audio/sfx/combat/Sword Impact Hit 2.ogg",
                "data/audio/sfx/combat/Sword Impact Hit 3.ogg",
                ], 
                "track": None, 
                "volume": 0.3
                },
        "hit_no_damage": {
            "tracks": [
                "data/audio/sfx/combat/Sword Blocked 1.ogg",
                "data/audio/sfx/combat/Sword Blocked 2.ogg",
                "data/audio/sfx/combat/Sword Blocked 3.ogg",
                "data/audio/sfx/combat/Sword Parry 1.ogg",
                "data/audio/sfx/combat/Sword Parry 2.ogg",
                "data/audio/sfx/combat/Sword Parry 3.ogg",
                ], 
                "track": None, 
                "volume": 0.3
                },
        "miss": {
            "tracks": [
                "data/audio/sfx/combat/Sword Attack 1.ogg",
                "data/audio/sfx/combat/Sword Attack 2.ogg",
                "data/audio/sfx/combat/Sword Attack 3.ogg",
                ], 
                "track": None, 
                "volume": 0.3
                },
    },
    "short_sword": _empty_melee_sound_entry(),
    "long_sword": _empty_melee_sound_entry(),
    "spear": _empty_melee_sound_entry(),
    "natural": _empty_melee_sound_entry(),
    "generic": {
        "hit_damage": {
            "tracks": [
                "data/audio/sfx/combat/hit_and_damage/generic/hit_flesh_1.ogg",
                "data/audio/sfx/combat/hit_and_damage/generic/hit_flesh_2.ogg",
                "data/audio/sfx/combat/hit_and_damage/generic/hit_flesh_3.ogg",
                "data/audio/sfx/combat/hit_and_damage/generic/hit_flesh_4.ogg",
                ], 
                "track": None, 
                "volume": 0.3
                },
        "hit_no_damage": {
            "tracks": [
                "data/audio/sfx/combat/hit_no_damage/generic/Sword Blocked 1.ogg",
                "data/audio/sfx/combat/hit_no_damage/generic/Sword Blocked 2.ogg",
                "data/audio/sfx/combat/hit_no_damage/generic/Sword Blocked 3.ogg",
                ], 
                "track": None, 
                "volume": 0.3
                },
        "miss": {
            "tracks": [
                "data/audio/sfx/combat/no_hit/generic/fist_6.ogg",
                "data/audio/sfx/combat/no_hit/generic/fist_5.ogg",
                "data/audio/sfx/combat/no_hit/generic/fist_3.ogg",
                ], 
                "track": None, 
                "volume": 0.3
                },
    },
}

del _empty_melee_sound_entry

# Dummy targets -------------------------------------------------------------
MELEE_DUMMY_SOUNDS = {
    "hit_damage": {"tracks": ["data/audio/sfx/combat/dummy_target/generic/mixkit-body-punch-quick-hit-2153.wav"], "track": None, "volume": 0.3},
    "hit_no_damage": {"tracks": ["data/audio/sfx/combat/dummy_target/generic/mixkit-body-punch-quick-hit-2153.wav"], "track": None, "volume": 0.3},
    "miss": {"tracks": ["data/audio/sfx/combat/dummy_target/generic/mixkit-body-punch-quick-hit-2153.wav"], "track": None, "volume": 0.3},
}

# Pain reactions ------------------------------------------------------------
PAIN_SOUND_ENABLED = True
PAIN_SOUND_DEFAULT_VOLUME = 0.4
PAIN_SOUNDS = {
    "player": {"tracks": ["data/audio/sfx/combat/hurt/player/hurt_6.ogg",
                          "data/audio/sfx/combat/hurt/player/male_hurt7.mp3"], "track": None, "volume": None},
    "default": {"tracks": [], "track": None, "volume": None},
}

# Death reactions -----------------------------------------------------------
DEATH_SOUND_ENABLED = True
DEATH_SOUND_DEFAULT_VOLUME = 0.7
DEATH_SOUNDS = {
    "player": {"tracks": [], "track": None, "volume": None},
    "goblin": {"tracks": [], "track": "data/audio/sfx/combat/death/goblin/goblin-scream-87564.mp3", "volume": None},
    "default": {"tracks": [], "track": None, "volume": None},
}

# Player stamina ------------------------------------------------------------
PLAYER_STAMINA_DEPLETED_SOUND_ENABLED = True
PLAYER_STAMINA_DEPLETED_SOUNDS = ["data/audio/sfx/combat/no_stamina/player/fatigue_high.ogg",
                                  "data/audio/sfx/combat/no_stamina/player/fatigue_low.ogg",
                                  "data/audio/sfx/combat/no_stamina/player/fatigue_med.ogg"]
PLAYER_STAMINA_DEPLETED_SOUND = None
PLAYER_STAMINA_DEPLETED_VOLUME = 0.9

# Environment destruction ---------------------------------------------------
BREAKABLE_WALL_DESTROY_SOUND_ENABLED = True
BREAKABLE_WALL_DESTROY_SOUNDS = ["data/audio/sfx/combat/dummy_target/break_wall/smash_rock_1.ogg",
                                 "data/audio/sfx/combat/dummy_target/break_wall/smash_rock_2.ogg",
                                 "data/audio/sfx/combat/dummy_target/break_wall/smash_rock_3.ogg",
                                 "data/audio/sfx/combat/dummy_target/break_wall/smash_rock_4.ogg"]
BREAKABLE_WALL_DESTROY_SOUND = None
BREAKABLE_WALL_DESTROY_VOLUME = 0.3

TABLE_DESTROY_SOUND_ENABLED = True
TABLE_DESTROY_SOUNDS = ["data/audio/sfx/combat/dummy_target/break_table/crash_wooden_1.ogg",
                        "data/audio/sfx/combat/dummy_target/break_table/crash_wooden_2.ogg",]
TABLE_DESTROY_SOUND = None
TABLE_DESTROY_VOLUME = 0.3
