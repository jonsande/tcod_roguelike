"""Audio-related configuration."""

# Ambient loops --------------------------------------------------------------
AMBIENT_SOUND_ENABLED = True
AMBIENT_SOUND_VOLUME = 1.0  # 0.0 - 1.0
AMBIENT_SOUND_TRACKS = {
    # 1: "data/audio/ambient/town.ogg",
    # 2: "data/audio/ambient/dungeon_floor_2.ogg",
    1: "data/audio/ambient/CO.AG_InTheHeartOfThisAncientCity.ogg",
    2: "data/audio/ambient/CO.AG_DarkRooms.ogg",
}
AMBIENT_SOUND_DEFAULT_TRACK = None

# Player footsteps -----------------------------------------------------------
PLAYER_FOOTSTEP_SOUND_ENABLED = True
PLAYER_FOOTSTEP_SOUNDS = [
    "data/audio/sfx/walk/gravel/walk_t_gravel_1.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_2.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_3.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_4.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_5.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_6.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_7.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_8.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_9.ogg",
    "data/audio/sfx/walk/gravel/walk_t_gravel_10.ogg",
]
PLAYER_FOOTSTEP_VOLUME = 0.1  # 0.0 - 1.0

# Door interactions ----------------------------------------------------------
DOOR_OPEN_SOUND_ENABLED = True
DOOR_OPEN_SOUNDS = [
    # "data/audio/sfx/doors/open_1.ogg",
    "data/audio/sfx/doors/open_door.ogg",
    
]
DOOR_OPEN_VOLUME = 0.75

DOOR_CLOSE_SOUND_ENABLED = True
DOOR_CLOSE_SOUNDS = [
    # "data/audio/sfx/doors/close_1.ogg",
    "data/audio/sfx/doors/close_door.ogg"
]
DOOR_CLOSE_VOLUME = 0.75
