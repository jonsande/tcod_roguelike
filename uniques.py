from __future__ import annotations

from typing import TYPE_CHECKING

import entity_factories
import random


# Chequeadores de si existen ya o no:
sauron_exists = False
grial_exists = False
goblin_amulet_exists = False
adventurer_unique_exists = False


fireplace_counter = 0
fireplace_exist = False

# Asignamos nivel en que generar el artefacto
#grial_floor = random.randint(8, 12)
goblin_amulet_floor = random.randint(2,8)

# Colocamos entidades especiales
def place_uniques(floor, center_of_last_room, dungeon):

    # Neutrales:
    if floor == 8:

        if center_of_last_room != (0,0):

            # ESTO HAY QUE HACERLO SIN VARIABLES GLOBALES
            global adventurer_unique_exists
            if adventurer_unique_exists == True:
                pass
            else:
                entity_factories.adventurer_unique.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
                adventurer_unique_exists = True
    else:
        pass


    # Artefactos:

    ## Grial
    if floor == 13:
        if center_of_last_room != (0,0):

            # ESTO HAY QUE HACERLO SIN VARIABLES GLOBALES
            global grial_exists
            if grial_exists == True:
                pass
            else:
                entity_factories.grial.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
                grial_exists = True
    else:
        pass

    ## Goblin amulet
    if floor == goblin_amulet_floor:
        if random.randint(1, 6) >= 5:
            if center_of_last_room != (0, 0):
                global goblin_amulet_exists
                if goblin_amulet_exists == True:
                    pass
                else:
                    entity_factories.goblin_tooth_amulet.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
                    goblin_amulet_exists = True


    # Jefes:
    ## Sauron
    if floor == 13:
        if center_of_last_room != (0,0):
            global sauron_exists
            if sauron_exists == True:
                pass
            else:
                entity_factories.sauron.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
                sauron_exists = True
    else:
        pass


    # Especiales:

    ## Fire place
    """
    if floor > 1 and floor < 12:
        if center_of_last_room != (0, 0):
            global fireplace_counter
            if fireplace_counter == floor:     
                if random.randint(1,12) >= 1:
                    fireplace_counter += 1                    
                    entity_factories.fireplace.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
    """
    """
    if floor == 2:
        if center_of_last_room != (0, 0):
            global fireplace_exist
            if fireplace_exist == False:
                entity_factories.fireplace.spawn(dungeon, center_of_last_room[0], center_of_last_room[1])
                fireplace_exist = True
    """
