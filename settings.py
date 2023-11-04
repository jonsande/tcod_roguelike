from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING
from game_map import GameMap, GameMapTown
import tile_types
import random
import tcod
from entity_factories import *
import uniques

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

# Número máximo de puertas por nivel
max_doors = 4
# Número de muros rompibles
max_breakable_walls = 3

# Escombros máximos por planta
max_debris_by_floor = [
    (1, 30),
    (2, 9),
    (4, 7),
    (6, 2),
]

# Items máximos por habitación
# Nivel mazmorra | nº items
treasure_floor = random.randint(5,9)
max_items_by_floor = [
    #(1, 25),
    (1, 1),
    (2, 1),
    (3, 2),
    (4, 2),
    (treasure_floor , 2), # Esta sería algo así como la cámara del tesoro, con algún artefacto poderoso. Para que un personaje con sigilo pueda aprovecharse de una estrategia basada en el STEALTH
    (12, 1),
]

# Monstruos máximos por habitación
# Nivel mazmorra | nº monstruos
max_monsters_by_floor = [
    (0, 1),
    (1, 3),
    #(1, 1),
    (2, 1),
    (3, 2),
    (4, 2),
    (6, 3),
]
# Probabilidades de que se generen estas entidades por sala.
# El nivel 0 al parecer es lo que se aplica por defecto a todos los niveles
# Al parecer las tiradas se hacen en orden?!
item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    #0: [(health_potion, 1), (damage_potion, 1)],
    #1: [(power_potion, 100), (damage_potion, 100), (health_potion, 100), (confusion_scroll, 100), (paralisis_scroll, 100), (lightning_scroll, 100), (fireball_scroll, 100)],
    #1: [(chain_mail, 100), (short_sword, 100), (long_sword, 100), (grial, 100)],
    #1: [(dagger_plus_one, 100)],
    1: [(health_potion, 10), (damage_potion, 10), (power_potion, 10), (stamina_potion, 10), (confusion_potion, 10), (precission_potion, 10), (strength_potion, 5)],
    2: [(health_potion, 15), (damage_potion, 15), (power_potion, 15), (stamina_potion, 15), (confusion_potion, 15), (precission_potion, 15), (rock, 15), (table, 15)],
    3: [(poisoned_triple_ration, 10), (triple_ration, 10), (rock, 45), (confusion_scroll, 10), (paralisis_scroll, 10), (lightning_scroll, 5), (fireball_scroll, 5), (short_sword, 5)],
    4: [(confusion_scroll, 15), (paralisis_scroll, 15), (lightning_scroll, 10), (fireball_scroll, 5)],
    5: [(lightning_scroll, 10), (fireball_scroll, 10), (long_sword, 5), (chain_mail, 5)],
    7: [(spear, 5)],
    8: [(short_sword, 15)],
}
enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    #0: [(rat, 100)], # Esto no hace nada porque el max_monsters_by_floor está a 0
    #1: [(bandit, 100)],
    1: [(adventurer, 0), (rat, 20), (swarm_rat, 20), (goblin, 10)],
    2: [(adventurer, 2), (rat, 50), (swarm_rat, 50), (goblin, 50)],
    3: [(orc, 50), (goblin, 50), (bandit, 10)],
    4: [(swarm_rat, 0), (rat, 5), (true_orc, 20), (orc, 30), (goblin, 30)],
    5: [(true_orc, 25), (orc, 30), (goblin, 30), (troll, 15)],
    6: [(adventurer, 25), (true_orc, 30), (orc, 30), (goblin, 15)],
    7: [(adventurer, 0), (true_orc, 30), (orc, 30), (goblin, 15)],
}
debris_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(debris_a, 30)],
    3: [(debris_a, 20)],
    6: [(debris_a, 10)],
}