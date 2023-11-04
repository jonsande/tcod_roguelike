from typing import Tuple
import random
import render_order

import numpy as np  # type: ignore

# Tile graphics structured type compatible with Console.tiles_rgb.
graphic_dt = np.dtype(
    [
        ("ch", np.int32),  # Unicode codepoint.
        ("fg", "3B"),  # 3 unsigned bytes, for RGB colors.
        ("bg", "3B"),
    ]
)

# Tile struct used for statically defined tile data.
tile_dt = np.dtype(
    [
        ("walkable", np.bool_),  # True if this tile can be walked over.
        ("transparent", np.bool_),  # True if this tile doesn't block FOV.
        ("dark", graphic_dt),  # Graphics for when this tile is not in FOV.
        ("light", graphic_dt),  # Graphics for when the tile is in FOV.
    ]
)

import render_order
def new_tile(
    *,  # Enforce the use of keywords, so that parameter order doesn't matter.
    walkable: int,
    transparent: int,
    dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
) -> np.ndarray:
    """Helper function for defining individual tile types """
    return np.array((walkable, transparent, dark, light), dtype=tile_dt)

# SHROUD represents unexplored, unseen tiles
SHROUD = np.array((ord(" "), (255, 255, 255), (0, 0, 0)), dtype=graphic_dt)


door = new_tile(
    walkable=True,
    transparent=False,
    #dark=(ord("∞"), (15,15,15), (0,0,0)),
    #light=(ord("%"), (250,250,250), (0,0,0)),
    dark=(ord("+"), (15,15,15), (0,0,0)),
    light=(ord("+"), (93,59,0), (0,0,0)),
)

# BALDOSAS: δ
floor = new_tile(
    walkable=True,
    transparent=True,
    #dark=(ord("∞"), (15,15,15), (0,0,0)),
    #light=(ord("∞"), (50,50,40), (5,5,5)),
    dark=(ord("."), (15,15,15), (0,0,0)),
    light=(ord("."), (80,80,80), (0,0,0)),
)

classic_floor = new_tile(
    walkable=True,
    transparent=True,
    #dark=(ord("∞"), (15,15,15), (0,0,0)),
    #light=(ord("∞"), (50,50,40), (5,5,5)),
    dark=(ord("."), (15,15,15), (0,0,0)),
    light=(ord("."), (50,50,40), (5,5,5)),
)

town_floor = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("~"), (133,116,66), (0,0,0)),
    light=(ord("~"), (133,116,66), (0,0,0)),
)
town_wall = new_tile(
    walkable=False,
    transparent=False,
    dark=(ord("~"), (133,116,66), (0,0,0)),
    light=(ord("~"), (133,116,66), (0,0,0)),
    )

classic_wall = new_tile(
    walkable=False,
    transparent=False,
    dark=(ord("#"), (15,15,15), (0,0,0)),
    light=(ord("#"), (50,50,40), (5,5,5)),
    )

wall_v1 = new_tile(
        walkable=False,
        transparent=False,
        light=(ord('√'), (170,170,120), (0,0,0)),
        dark=(ord('√'), (39,7,47), (5,5,5)),
        )

wall_v2 = new_tile(
        walkable=False,
        transparent=False,
        light=(ord("√"), (70,40,70), (0,0,0)),
        dark=(ord("√"), (39,50,47), (5,5,5)),
    )

dummy_wall = new_tile(
        walkable=False,
        transparent=True,
        light=(ord("√"), (70,40,70), (0,0,0)),
        dark=(ord("√"), (39,50,47), (5,5,5)),
    )

# No se pueden generar diferentes baldosas por este medio,
# Hay que hacerlo con items

# MUROS: √
## Randomizar muros

wall_roulette = random.randint(1,3)

if wall_roulette == 1:
    wall = new_tile(
        walkable=False,
        transparent=False,
        #light=(ord('√'), (170,170,120), (0,0,0)),
        #dark=(ord('√'), (39,7,47), (5,5,5)),
        light=(ord('#'), (170,170,120), (0,0,0)),
        dark=(ord('#'), (39,7,47), (5,5,5)),
        )
    breakable_wall = new_tile(
        walkable=True,
        transparent=False,
        #light=(ord('√'), (170,170,120), (0,0,0)),
        #dark=(ord('√'), (39,7,47), (5,5,5)),
        light=(ord('#'), (170,170,120), (0,0,0)),
        dark=(ord('#'), (39,7,47), (5,5,5)),
    )
elif wall_roulette == 2:
    wall = new_tile(
        walkable=False,
        transparent=False,
        #light=(ord("√"), (255,255,184), (0,0,0)),
        #dark=(ord("√"), (39,7,47), (5,5,5)),
        light=(ord("#"), (255,255,184), (0,0,0)),
        dark=(ord("#"), (39,7,47), (5,5,5)),
        # Modo Hardcore:
        #dark=(ord("√"), (0,0,0), (0,0,0)),
        )
    breakable_wall = new_tile(
        walkable=True,
        transparent=False,
        #light=(ord("√"), (255,255,184), (0,0,0)),
        #dark=(ord("√"), (39,7,47), (5,5,5)),
        light=(ord("#"), (255,255,184), (0,0,0)),
        dark=(ord("#"), (39,7,47), (5,5,5)),
    )
else:
    wall = new_tile(
        walkable=False,
        transparent=False,
        #light=(ord("√"), (70,40,70), (0,0,0)),
        #dark=(ord("√"), (39,50,47), (5,5,5)),
        light=(ord("#"), (70,40,70), (0,0,0)),
        dark=(ord("#"), (39,50,47), (5,5,5)),
    )
    breakable_wall = new_tile(
        walkable=True,
        transparent=False,
        #light=(ord("√"), (70,40,70), (0,0,0)),
        #dark=(ord("√"), (39,50,47), (5,5,5)),
        light=(ord("#"), (70,40,70), (0,0,0)),
        dark=(ord("#"), (39,50,47), (5,5,5)),
    )
    
# MURO DEBBUG
"""
wall = new_tile(
    walkable=False,
    transparent=True,
    #dark=(ord("#"), (39,7,47), (5,5,5)),
    dark=(ord("#"), (39,7,47), (5,5,5)),
    #light=(ord("#"), (255,255,184), (0,0,0)),
    light=(ord("#"), (170,170,120), (0,0,0)),
)
"""
    
# MURO PUEBLO:
town_wall = new_tile(
    walkable=False,
    transparent=True,
    #dark=(ord("#"), (39,7,47), (5,5,5)),
    dark=(ord("#"), (39,7,47), (5,5,5)),
    #light=(ord("#"), (255,255,184), (0,0,0)),
    light=(ord("#"), (170,170,120), (0,0,0)),
)

# ESCALERAS:
down_stairs = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord(">"), (25, 25, 25), (5, 5, 5)),
    light=(ord(">"), (50,50,40), (6,9,3)),
    #render_order=render_order.RenderOrder.ITEM,
)