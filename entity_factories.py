# Aquí generamos los modelos de entidades que existen en el juego

from components.ai import HostileEnemy, Neutral, Dummy, ConfusedEnemy, HostileEnemyPlus, SneakeEnemy, SleepingEnemy, Scout, SentinelEnemy
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter, Door
from components.inventory import Inventory
from components.level import Level
from entity import Actor, Item, Decoration, Obstacle
import random
import numpy as np


def color_roulette():
    winner = list(np.random.choice(range(256), size=3))
    return winner


# TO EAT THINGS

meat = Item(
    char="%",
    color=(236,113,64),
    name="Meat",
    id_name = "Meat",
    consumable=consumable.FoodConsumable(amount=8)
)
triple_ration = Item(
    char="%",
    color=(153,97,0),
    name="Triple ration",
    id_name = "Triple ration",
    consumable=consumable.FoodConsumable(amount=15)
)
poisoned_triple_ration = Item(
    char="%",
    color=(153,97,0),
    name="Triple ration",
    id_name = "Poisoned triple ration",
    consumable=consumable.FoodConsumable(amount=-8)
)

# SCROLLS

scroll_options = ["Scroll named AXME ZU TIKA", "Scroll named ZAKALOM ERMIS", "Scroll named PROQUIUM PARIS", "Scroll named ELAM EBOW"]

def scroll_name_roulette():

    global scroll_options
    if scroll_options:
        roulette = random.randint(0, len(scroll_options) - 1)
        winner = scroll_options[roulette]
        scroll_options.remove(scroll_options[roulette])
        return winner
    else:
        pass
        #print("Scroll Name Roulette fails!")
        #raise Impossible("Scroll Name Roulette fails!")

sand_bag = Item(
    char="(",
    color=(210,210,110),
    name="Sand bag",
    id_name = "Sand bag",
    uses=3,
    consumable=consumable.BlindConsumable(number_of_turns=2),
)

confusion_scroll = Item(
    char="~",
    color=color_roulette(),
    name=scroll_name_roulette(),
    id_name = "Confusion scroll",
    consumable=consumable.ConfusionConsumable(number_of_turns=10),
)

paralisis_scroll = Item(
    char="~",
    color=color_roulette(),
    name=scroll_name_roulette(),
    id_name = "Paralisis scroll",
    consumable=consumable.ParalisisConsumable(number_of_turns=10),
)

lightning_scroll = Item(
    char="~",
    color=color_roulette(),
    name=scroll_name_roulette(),
    id_name = "Lightning scroll",
    consumable=consumable.LightningDamageConsumable(damage=15, maximum_range=8),
)

fireball_scroll = Item(
    char="~",
    color=color_roulette(),
    name=scroll_name_roulette(),
    id_name = "Fireball scroll",
    consumable=consumable.FireballDamageConsumable(damage=12, radius=2),
)

# POTIONS:
potion_options = [
    "Suspicious purple brew",
    "Smoky potion", 
    "Muddy water potion", 
    "Deep purple potion", 
    "Milky potion", 
    "Magenta potion",
    "Dark potion",
    "Grey potion",
    "Bloody potion",
]

def potion_name_roulette():
    global potion_options
    if potion_options:
        roulette = random.randint(0, len(potion_options) - 1)
        winner = potion_options[roulette]
        potion_options.remove(winner)
        return winner
    
    else:
        pass

health_potion = Item(
    char="!",
    color=(200, 200, 200),
    #name="Suspicious purple brew",
    name=potion_name_roulette(),
    id_name = "Health potion",
    consumable=consumable.HealingConsumable(amount=random.randint(1, 6) + 4),
)

strength_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Strength potion",
    consumable=consumable.StrenghtConsumable(amount=1),
)

posion_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Posion potion",
    #consumable=consumable.PosionConsumable(amount=1, counter=random.randint(6,10)),
    consumable=consumable.PosionConsumable(amount=1, counter=8),
)

antidote = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Antidote",
    consumable=consumable.AntidoteConsumable(),
)

#damage_potion = Item(
#    char="!",
#    color=(200, 200, 200),
#    name=potion_name_roulette(),
#    id_name = "Acid potion",
#    consumable=consumable.DamageConsumable(amount=random.randint(1, 6) + 4),
#)
#poison_potion = Item(
#    char="!",
#    color=(200, 200, 200),
#    name=potion_name_roulette(),
#    id_name = "Poison",
#    consumable=consumable.TemporalEffectConsumable(random.randint(5,10), -1, 'hp', "You are poisoned!", "You are no longer poisoned"),
#)

power_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Power brew",
    consumable=consumable.TemporalEffectConsumable(20, 5, 'base_power', "You feel strong!", "You feel weak"),
)
precission_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Amphetamine brew",
    consumable=consumable.TemporalEffectConsumable(20, 5, 'base_to_hit', "You feel sharp!", "You feel retarded!"),
)
stamina_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Stamina Potion",
    consumable=consumable.RestoreStaminaConsumable(),
)
confusion_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Self confusion potion",
    consumable=consumable.SelfConfusionConsumable(random.randint(5, 10)),
)
#TO DO Potions:
## Infravision potion: fov + 4

# DECORATION

debris_a = Decoration(
    char='"', # ∞
    #color=(207, 63, 255),
    color=(35, 25, 35),
    name="Debris",
)

rock = Decoration(
    char=";",
    #color=(207, 63, 255),
    color=(95, 85, 95),
    name="Rock",
)

table = Actor(
    char="#",
    color=(100,100,100),
    name="Table",
    ai_cls=Dummy,
    equipment=Equipment(),
    #fighter=Fighter(hp=10, base_defense=1, base_power=0, recover_rate=0, fov=0),
    fighter=Door(hp=15, base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=1),
    inventory=Inventory(capacity=1),
    level=Level(xp_given=0),
)

fireplace = Actor(
    char="x",
    color=(255,170,0),
    name="Fire place",
    ai_cls=Dummy,
    equipment=Equipment(),
    fighter=Fighter(hp=15, base_defense=0, base_power=0, recover_rate=0, fov=3),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=5),
)

#fireplace = Entity(char="x", color=(218,52,99), name="Fireplace", blocks_movement=False)

# OBSTACLES:

door = Obstacle(

    char='+',
    color=(120,120,120),
    name="Door",
    ai_cls=Dummy,
    fighter=Door(hp=random.randint(10,20), base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=3),
    #obstacle=Door(hp=random.randint(15,35), base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=3),
    level=Level(xp_given=1),
    inventory=Inventory(capacity=0),
    equipment=Equipment(),
)

breakable_wall = Obstacle(

    char='√',
    #char='#',
    # Poniendo color=None el color es transparente
    color=None,
    name="Suspicious wall",
    ai_cls=Dummy,
    fighter=Door(hp=random.randint(10,20), base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=0),
    #obstacle=Door(hp=random.randint(20,40), base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=4),
    level=Level(xp_given=2),
    inventory=Inventory(capacity=1),
    equipment=Equipment(),
)

# EQUIPPABLES

"""
revolver = Item(
    char="¬", 
    color=(0, 191, 255), 
    name="Revolver", 
    equippable=equippable.Revolver(damage=random.randint(6, 12), maximum_range=12, ammo=6)
)
"""

dagger = Item(
    char="/", 
    color=(0, 191, 125), 
    name="Dagger", 
    equippable=equippable.Dagger(),
    throwable=True
)

dagger_plus = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Dagger",
    id_name="Dagger (good)",
    equippable=equippable.DaggerPlus()
)

#sword = Item(char="/", color=(0, 191, 255), name="Sword", equippable=equippable.Sword())

short_sword = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Short Sword",
    id_name="Short Sword",
    equippable=equippable.ShortSword()
)

long_sword = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Long Sword", 
    equippable=equippable.LongSword()
)

spear = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Spear", 
    equippable=equippable.Spear(),
    throwable=True
)

leather_armor = Item(
    char="[",
    color=(139, 69, 19),
    name="Leather armor",
    equippable=equippable.LeatherArmor(),
    info=f"Stealth penalty: 1"
)

chain_mail = Item(
    char="[", 
    color=(139, 69, 19), 
    name="Chain Mail", 
    equippable=equippable.ChainMail()
)

# ARTEFACTS

grial = Item(
    char="y", 
    color=(139, 69, 19), 
    name="Grial",
    id_name="The Grial",
    equippable=equippable.Grial()
)

goblin_tooth_amulet = Item(
    char='"', 
    color=(139, 69, 19), 
    name="Tooth necklace",
    id_name="Xzy, the goblin tooth amulet",
    equippable=equippable.GoblinAmulet()
)

# INVENTORIES AND MONSTER DROPS

def inv_roulette(monster_type, amount):

    """
    monster_type: monster name; amount: amount of max items in inventory 
    """

    if monster_type == "Giant rat":
        choices = [meat]
    if monster_type == "Goblin":
        choices = [meat, dagger, posion_potion]
    if monster_type == "Orc":
        choices = [dagger, power_potion, health_potion]
    if monster_type == "True Orc":
        choices = [short_sword, power_potion, health_potion, confusion_scroll, posion_potion]
    if monster_type == "Bandit":
        choices = [short_sword, precission_potion, stamina_potion, posion_potion, dagger]
    if monster_type == "Adventurer Unique":
        choices = [long_sword, health_potion, health_potion]

    inventory = []

    for i in range(1, amount+1):
        inventory.append(random.choice(choices))

    #print(f"{monster_type} inventory: {inventory}")
    
    return inventory


def drop_roulette(chances, inventory):

    """
    Triggered when the monster dies.
    """

    choices = []

    if inventory:
        for i in inventory:
            choices.append(i)

        #print(f"Drop roulette choices: {choices}")

    # Las chances se deciden en el drop_loot() de fighter.py
    #chances = 10
    if choices:

        if random.randint(1, 12) <= chances:
            return random.choice(choices)  
        else:   
            if random.randint(1, 12) <= 1:
                return meat
            else:
                pass
                

# CREATURES

player = Actor(
    char="@",
    color=(255, 255, 255),
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        #hp=32,
        hp=999, # Debugg
        base_defense=0, 
        base_power=0,
        recover_rate=1, 
        fov=6,
        #fov=90, # Debugg
        dmg_mod = (1, 4), 
        base_stealth=1, 
        #base_stealth=100, # Debugg
        base_to_hit=0,
        luck=1,
        critical_chance=1,
        # satiety=32,
        satiety=24,
        stamina=3, 
        max_stamina=3,
        poison_resistance=1
    ),
    inventory=Inventory(capacity=20),
    level=Level(level_up_base=20), # Default: 200
)

adventurer = Actor(
    char="@",
    color=(210, 210, 210),
    name="Adventurer",
    ai_cls=Neutral,
    equipment=Equipment(),
    fighter=Fighter(hp=30, base_defense=2, base_power=0, recover_rate=0, fov=6, dmg_mod = (1, 4)),
    inventory=Inventory(capacity=20),
    level=Level(level_up_base=20),
)

adventurer_unique = Actor(
    char="@",
    color=(210, 210, 210),
    name="Adventurer",

    ai_cls=Neutral,
    equipment=Equipment(),
    fighter=Fighter(hp=32, base_defense=5, base_power=4, recover_rate=0, fov=0, dmg_mod = (1, 4)),
    inventory=Inventory(capacity=1, items=inv_roulette("Adventurer Unique", 3)),
    level=Level(xp_given=50),
)

rat = Actor(
    char="r",
    color=(80,80,110),
    name="Giant rat",
    ai_cls=SleepingEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=6, 
        #hp=32,
        base_defense=1, 
        base_power=1, 
        recover_rate=0, 
        fov=0, dmg_mod = (1, 2), 
        aggressivity=5, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=7,
        luck=0,
    ),
    inventory=Inventory(capacity=1, items=inv_roulette("Giant rat", 1)),
    level=Level(xp_given=2),
    to_eat_drop=meat,
)

swarm_rat = Actor(
    char="r",
    color=(80,80,110),
    name="Hungry rat",
    ai_cls=random.choice([SleepingEnemy, HostileEnemy]),
    equipment=Equipment(),
    fighter=Fighter(
        hp=4,
        base_defense=1, 
        base_power=1, 
        recover_rate=0, 
        fov=8, 
        dmg_mod = (1, 2), 
        aggressivity=15, 
        stamina=2, 
        max_stamina=2,
        action_time_cost=7,
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=1),
)

goblin = Actor(
    char="g",
    color=(60,89,33),
    name="Goblin",
    ai_cls=random.choice([SleepingEnemy, HostileEnemy, Scout]),
    #ai_cls=Scout,
    equipment=Equipment(),
    fighter=Fighter(
        hp=8, 
        base_defense=2, 
        base_power=3, 
        recover_rate=1, 
        fov=random.randint(6, 8), 
        dmg_mod = (1, 2), 
        aggressivity=5, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=7,
        woke_ai_cls=HostileEnemy
    ),
    inventory=Inventory(capacity=1, items=inv_roulette("Goblin", 1)),
    level=Level(xp_given=3),
)

monkey = Actor(
    char="y",
    color=(110,4,4),
    name="Monkey",
    ai_cls=random.choice([SleepingEnemy, Scout]),
    #ai_cls=Scout,
    equipment=Equipment(),
    fighter=Fighter(
        hp=8, 
        base_defense=2, 
        base_power=2, 
        recover_rate=1, 
        fov=random.randint(6, 10), 
        dmg_mod = (1, 2), 
        aggressivity=3, 
        stamina=5, 
        max_stamina=5,
        action_time_cost=6,
        woke_ai_cls=HostileEnemy
    ),
    inventory=Inventory(capacity=1, items=None),
    level=Level(xp_given=3),
)

orc = Actor(
    char="o",
    color=(63, 127, 63),
    name="Orc",
    ai_cls=random.choice([SleepingEnemy, HostileEnemy, Scout]),
    equipment=Equipment(),
    fighter=Fighter(
        hp=12, 
        base_defense=2, 
        base_power=3, 
        recover_rate=0, 
        fov=random.randint(3,6), 
        dmg_mod = (1, 6), 
        aggressivity=8, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
        woke_ai_cls=HostileEnemy
    ),
    inventory=Inventory(capacity=1, items=inv_roulette("Orc", 1)),
    level=Level(xp_given=5),
)

true_orc = Actor(
    char="o",
    color=(63, 220, 63),
    name="True Orc",
    ai_cls=random.choice([SleepingEnemy, HostileEnemy, Scout]),
    equipment=Equipment(),
    fighter=Fighter(
        hp=32, 
        base_defense=2, 
        base_power=3, 
        recover_rate=0, 
        fov=random.randint(5,8), 
        dmg_mod = (1, 6), 
        aggressivity=15, 
        base_to_hit=1, 
        stamina=4, 
        max_stamina=4,
        woke_ai_cls=HostileEnemy
        ),
    inventory=Inventory(capacity=2, items=inv_roulette("True Orc", 2)),
    level=Level(xp_given=10),
)

troll = Actor(
    char="T",
    color=(0, 127, 0),
    name="Troll",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=38, base_defense=2, base_armor_value=3, base_power=4, recover_rate=5, fov=0, dmg_mod = (1, 8), aggressivity=8, stamina=2, max_stamina=2),
    inventory=Inventory(capacity=1),
    level=Level(xp_given=14),
)

sauron = Actor(
    char="&",
    color=(233,176,96),
    name="Sauron",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=32, base_defense=3, base_power=4, recover_rate=12, fov=2, dmg_mod = (1, 6), aggressivity=8, stamina=5, max_stamina=5),
    inventory=Inventory(capacity=8),
    level=Level(xp_given=25),
)

snake = Actor(
    char="s",
    color=(133,116,66),
    name="Snake",
    ai_cls=SleepingEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=4, 
        base_defense=1, 
        base_power=0, 
        recover_rate=0, 
        fov=1, 
        dmg_mod = (0, 0), # Las serpientes no hacen daño. Pero pueden envenenar.
        aggressivity=1, 
        stamina=5, 
        max_stamina=5,
        woke_ai_cls=SneakeEnemy,
        poisons_on_hit=True,
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=2),
    to_eat_drop=meat,
)

bandit = Actor(
    char="@",
    color=(66,13,77),
    name="bandit",
    ai_cls=HostileEnemyPlus,
    equipment=Equipment(),
    fighter=Fighter(
        hp=32, 
        base_defense=1, 
        base_power=2, 
        recover_rate=1, 
        fov=8, 
        dmg_mod = (1, 4), 
        base_stealth=3, 
        base_to_hit=2,
    ),
    inventory=Inventory(capacity=2, items=inv_roulette("Bandit", 2)),
    level=Level(xp_given=14),
)

sentinel = Actor(
    char="&",
    color=(180,80,110),
    name="Sentinel",
    ai_cls=SentinelEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=12, 
        base_defense=1, 
        base_power=3, 
        recover_rate=12, 
        fov=0, dmg_mod = (1, 4), 
        aggressivity=0, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
    ),
    inventory=Inventory(capacity=1, items=inv_roulette("Giant rat", 1)),
    level=Level(xp_given=2),
    to_eat_drop=meat,
)