from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

import entity_factories
import random
from settings import TOTAL_FLOORS

if TYPE_CHECKING:
    from game_map import GameMap

# Chequeadores de si existen ya o no:
sauron_exists = False
grial_exists = False
goblin_amulet_exists = False
artifact_exists = False

artifact_location: Optional[Tuple[int, Tuple[int, int]]] = None

campfire_counter = 0
campfire_exist = False

# Asignamos nivel en que generar el artefacto
grial_floor = random.randint(10, 16)
goblin_amulet_floor = random.randint(6,14)
the_artifact_floor = TOTAL_FLOORS


def _get_hot_path_target(dungeon: "GameMap") -> Optional[Tuple[int, int]]:
    hot_path = getattr(dungeon, "hot_path", None) or []
    if not hot_path:
        return None
    return hot_path[-1]


def _record_spawn(*, entity, floor: int, category: str, key: str, source: str) -> None:
    # Import diferido para evitar el ciclo de importación con procgen.
    from procgen import record_entity_spawned

    record_entity_spawned(entity, floor, category, key=key, procedural=False, source=source)


def _place_the_artifact(dungeon: "GameMap") -> bool:
    """Coloca The Artifact en la última sala del hot_path del último piso."""
    global artifact_exists, artifact_location

    if artifact_exists:
        return False

    target = _get_hot_path_target(dungeon)
    if not target:
        return False

    x, y = target
    if hasattr(dungeon, "in_bounds") and not dungeon.in_bounds(x, y):
        return False
    if hasattr(dungeon, "tiles") and not dungeon.tiles["walkable"][x, y]:
        return False

    # Evitar superponer con entidades que bloqueen movimiento, buscando una casilla cercana.
    blocking_entity = (
        dungeon.get_blocking_entity_at_location(x, y)
        if hasattr(dungeon, "get_blocking_entity_at_location")
        else None
    )
    final_target = (x, y)
    if blocking_entity:
        found_spot = False
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                nx, ny = x + dx, y + dy
                if not dungeon.in_bounds(nx, ny):
                    continue
                if not dungeon.tiles["walkable"][nx, ny]:
                    continue
                if hasattr(dungeon, "get_blocking_entity_at_location") and dungeon.get_blocking_entity_at_location(nx, ny):
                    continue
                final_target = (nx, ny)
                found_spot = True
                break
            if found_spot:
                break
        if not found_spot:
            return False

    spawned = entity_factories.the_artifact.spawn(dungeon, *final_target)
    _record_spawn(entity=spawned, floor=the_artifact_floor, category="items", key="the_artifact", source="unique")
    artifact_exists = True
    artifact_location = (the_artifact_floor, final_target)
    return True


def debug_print_artifact_location() -> None:
    """Imprime en consola dónde se ha generado The Artifact."""
    if artifact_location:
        floor, (x, y) = artifact_location
        print(f"DEBUG: The Artifact -> piso {floor} en ({x}, {y})")
    elif artifact_exists:
        print("DEBUG: The Artifact se marcó como generado, pero no hay ubicación registrada.")
    else:
        print("DEBUG: The Artifact aún no se ha generado.")


# Colocamos entidades especiales
def place_uniques(floor, center_of_last_room, dungeon):

    # Artefactos:

    ## The Artifact

    if floor == the_artifact_floor:
        _place_the_artifact(dungeon)

    ## Grial
    if floor == 13:
        if center_of_last_room != (0,0):

            # ESTO HAY QUE HACERLO SIN VARIABLES GLOBALES
            global grial_exists
            if grial_exists == True:
                pass
            else:
                spawned = entity_factories.grial.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
                _record_spawn(entity=spawned, floor=floor, category="items", key="grial", source="unique")
                grial_exists = True
    else:
        pass

    ## Goblin amulet
    # Lo vamos a generar por procedimientos normales,
    # if floor == goblin_amulet_floor:
    #     if random.randint(1, 6) == 6:
    #         if center_of_last_room != (0, 0):
    #             global goblin_amulet_exists
    #             if goblin_amulet_exists == True:
    #                 pass
    #             else:
    #                 entity_factories.goblin_tooth_amulet.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
    #                 goblin_amulet_exists = True


    # Jefes:
    ## Sauron
    if floor == 16:
        if center_of_last_room != (0,0):
            global sauron_exists
            if sauron_exists == True:
                pass
            else:
                spawned = entity_factories.sauron.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
                _record_spawn(entity=spawned, floor=floor, category="monsters", key="sauron", source="unique")
                sauron_exists = True
    else:
        pass
