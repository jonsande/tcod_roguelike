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
