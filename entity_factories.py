# Aquí generamos los modelos de entidades que existen en el juego

from typing import List

from components.ai import (
    HostileEnemy,
    Neutral,
    Dummy,
    ConfusedEnemy,
    HostileEnemyPlus,
    SneakeEnemy,
    SleepingEnemy,
    Scout,
    SentinelEnemy,
    AdventurerAI,
)
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter, Door, BreakableWallFighter
from components.inventory import Inventory
from components.level import Level
from entity import Actor, Item, Decoration, Obstacle, Entity, Chest
import random
import numpy as np
import tile_types
import loot_tables
from settings import (
    GOD_MODE,
    GOD_MODE_STEALTH,
    BREAKABLE_WALL_HP_RANGE,
    BREAKABLE_WALL_CACHE_CHANCE,
    BREAKABLE_WALL_LOOT_CHANCE,
    CAMPFIRE_MIN_HP,
    CAMPFIRE_MAX_HP,
    CAMPFIRE_CACHE_ITEM_CHANCE,
    CAMPFIRE_CACHE_ITEM_IDS,
    ADVENTURER_COLOR,
    ADVENTURER_CORPSE_CHAR,
    ADVENTURER_CORPSE_COLOR,
    ADVENTURER_CORPSE_NAME,
)

# OBSTACLES:

door = Obstacle(

    char='+',
    color=(93,59,0),
    name="Door",
    ai_cls=Dummy,
    fighter=Door(hp=random.randint(60,80), base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=3),
    #obstacle=Door(hp=random.randint(15,35), base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=3),
    level=Level(xp_given=1),
    inventory=Inventory(capacity=0),
    equipment=Equipment(),
)

chest = Chest(
    char="C",
    open_char="c",
    color=(184, 134, 11),
    name="Chest",
    inventory=Inventory(capacity=12, items=[]),
)


def fill_chest_with_items(chest_entity: Chest, items: List[Item]) -> None:
    """Replace the contents of a chest with the provided items."""
    chest_entity.inventory.items = []
    for item in items:
        chest_entity.add_item(item)


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
loot_tables.register_loot_item("meat", meat)
triple_ration = Item(
    char="%",
    color=(153,97,0),
    name="Triple ration",
    id_name = "Triple ration",
    consumable=consumable.FoodConsumable(amount=15)
)
loot_tables.register_loot_item("triple_ration", triple_ration)
poisoned_triple_ration = Item(
    char="%",
    color=(153,97,0),
    name="Triple ration",
    id_name = "Poisoned triple ration",
    consumable=consumable.FoodConsumable(amount=-8)
)

# SCROLLS

SCROLL_NAME_POOL = [
    "Scroll named AXME ZU TIKA",
    "Scroll named ZAKALOM ERMIS",
    "Scroll named PROQUIUM PARIS",
    "Scroll named ELAM EBOW",
    "Scroll named OPHAR IXES",
    "Scroll named LORUM SED",
    "Scroll named VAS ORT FLAM",
    "Scroll named HEC LAPIDA",
    "Scroll named QERTU VIAL",
    "Scroll named NEMESIS ORA",
    "Scroll named TAVU SIRION",
    "Scroll named KILAM NESIR",
    "Scroll named ARKA MODR",
    "Scroll named INU KALAN",
    "Scroll named VEXI MUR",
    "Scroll named OBLON RIYU",
]
scroll_options = SCROLL_NAME_POOL.copy()

def scroll_name_roulette():

    global scroll_options
    if not scroll_options:
        scroll_options = SCROLL_NAME_POOL.copy()
    roulette = random.randint(0, len(scroll_options) - 1)
    winner = scroll_options.pop(roulette)
    return winner

sand_bag = Item(
    char="(",
    color=(210,210,110),
    name="Sand bag",
    id_name = "Sand bag",
    uses=3,
    consumable=consumable.BlindConsumable(number_of_turns=2),
)
loot_tables.register_loot_item("sand_bag", sand_bag)

confusion_scroll = Item(
    char="~",
    color=color_roulette(),
    name=scroll_name_roulette(),
    id_name = "Confusion scroll",
    consumable=consumable.TargetedConfusionConsumable(number_of_turns=10),
)
loot_tables.register_loot_item("confusion_scroll", confusion_scroll)

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
    consumable=consumable.LightningDamageConsumable(),
)

fireball_scroll = Item(
    char="~",
    color=color_roulette(),
    name=scroll_name_roulette(),
    id_name = "Fireball scroll",
    consumable=consumable.FireballDamageConsumable(damage=12, radius=2),
)

# Breakable wall loot table (scrolls and similar findings hidden in walls)
BREAKABLE_WALL_LOOT_TABLE = [
    confusion_scroll,
    paralisis_scroll,
    lightning_scroll,
    fireball_scroll,
]

# POTIONS:
potion_name_options = [
    "Suspicious purple brew",
    "Smoky potion", 
    "Muddy water potion", 
    "Deep purple potion", 
    "Milky potion", 
    "Magenta potion",
    "Dark potion",
    "Grey potion",
    "Bloody potion",
    "Red potion",
    "Stinky potion",
    "Viscous sludge potion",
    "Glowing gold elixir",
    "Murky green potion",
    "Fizzy orange brew",
    "Clearwater solution",
    "Shimmering silver liquid",
    "Iridescent azure draught",
    "Pungent sulphur philter",
    "Bubbling teal tonic",
    "Ashen dust suspension",
    "Sweet floral infusion",
]

def potion_name_roulette():
    global potion_name_options
    if potion_name_options:
        roulette = random.randint(0, len(potion_name_options) - 1)
        winner = potion_name_options[roulette]
        potion_name_options.remove(winner)
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
    throwable=True,
)
loot_tables.register_loot_item("health_potion", health_potion)

strength_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Strength potion",
    consumable=consumable.StrenghtConsumable(amount=1),
    throwable=True,
)

poison_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Poison potion",
    #consumable=consumable.PoisonConsumable(amount=1, counter=random.randint(6,10)),
    consumable=consumable.PoisonConsumable(amount=1, counter=8),
    throwable=True,
)
loot_tables.register_loot_item("poison_potion", poison_potion)

antidote = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Antidote",
    consumable=consumable.AntidoteConsumable(),
    throwable=True,
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
    consumable=consumable.TemporalEffectConsumable(
        20,
        5,
        'base_power',
    ),
    throwable=True,
)
loot_tables.register_loot_item("power_potion", power_potion)
precission_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Amphetamine brew",
    consumable=consumable.TemporalEffectConsumable(
        20,
        5,
        'base_to_hit',
    ),
    throwable=True,
)
loot_tables.register_loot_item("precission_potion", precission_potion)
stamina_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Restore stamina Potion",
    consumable=consumable.RestoreStaminaConsumable(),
    throwable=True,
)
loot_tables.register_loot_item("stamina_potion", stamina_potion)
increase_max_stamina = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Potion of Lasting Vigor",
    consumable=consumable.IncreaseMaxStaminaConsumable(amount=1),
    throwable=True,
)
life_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Life potion",
    consumable=consumable.IncreaseMaxHPConsumable(amount=8),
    throwable=True,
)

infra_vision_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name="Potion of True Sight",
    consumable=consumable.IncreaseFOVConsumable(amount=1),
    throwable=True,
)

temporal_infra_vision_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name="Potion of Flash Sight",
    consumable=consumable.TemporalFOVConsumable(min_turns=12, max_turns=32, amount=6),
    throwable=True,
)
blindness_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name="Potion of Blinding Darkness",
    consumable=consumable.BlindnessConsumable(amount=-32),
    throwable=True,
)

confusion_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Confusion potion",
    consumable=consumable.ConfusionConsumable(random.randint(12, 32)),
    throwable=True,
)
paralysis_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name = "Paralysis potion",
    consumable=consumable.ParalysisConsumable(min_turns=12, max_turns=32),
    throwable=True,
)
petrification_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=potion_name_roulette(),
    id_name="Petrification potion",
    consumable=consumable.PetrifyConsumable(),
    throwable=True,
)

# DECORATION

debris_a = Decoration(
    char='"', # ∞
    #color=(207, 63, 255),
    color=(35, 25, 35),
    name="Debris",
)

breakable_wall_rubble = Decoration(
    char=debris_a.char,
    color=debris_a.color,
    name="You see a pile of rubble",
)

adventurer_corpse = Entity(
    char=ADVENTURER_CORPSE_CHAR,
    color=ADVENTURER_CORPSE_COLOR,
    name=ADVENTURER_CORPSE_NAME,
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
    fighter=Door(hp=15, base_defense=0, base_power=0, recover_rate=0, fov=0, base_armor_value=1, fire_resistance=-4),
    inventory=Inventory(capacity=1),
    level=Level(xp_given=0),
)

campfire = Actor(
    char="x",
    color=(255,170,0),
    name="Campfire",
    ai_cls=Dummy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=random.randint(CAMPFIRE_MIN_HP, CAMPFIRE_MAX_HP),
        base_defense=0,
        base_power=0,
        recover_rate=0,
        fov=3,
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=5),
)

#campfire = Entity(char="x", color=(218,52,99), name="Campfire", blocks_movement=False)


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
loot_tables.register_loot_item("dagger", dagger)

dagger_plus = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Dagger",
    id_name="Dagger (good)",
    equippable=equippable.DaggerPlus()
)
loot_tables.register_loot_item("dagger_plus", dagger_plus)

#sword = Item(char="/", color=(0, 191, 255), name="Sword", equippable=equippable.Sword())

short_sword = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Short Sword",
    id_name="Short Sword",
    equippable=equippable.ShortSword()
)
loot_tables.register_loot_item("short_sword", short_sword)

# Campfire extras
_CAMPFIRE_NEIGHBOR_OFFSETS = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
]


def _setup_campfire_spawn(entity: Actor) -> None:
    _randomize_campfire_hp(entity)
    _maybe_spawn_campfire_cache(entity)


def _randomize_campfire_hp(entity: Actor) -> None:
    fighter = getattr(entity, "fighter", None)
    if not fighter:
        return
    new_hp = random.randint(CAMPFIRE_MIN_HP, CAMPFIRE_MAX_HP)
    fighter.max_hp = new_hp
    fighter.hp = new_hp


def _maybe_spawn_campfire_cache(entity: Actor) -> None:
    if random.random() >= CAMPFIRE_CACHE_ITEM_CHANCE:
        return
    cache_items = _get_campfire_cache_items()
    if not cache_items:
        return
    gamemap = entity.gamemap
    offsets = list(_CAMPFIRE_NEIGHBOR_OFFSETS)
    random.shuffle(offsets)
    loot_proto = random.choice(cache_items)
    for dx, dy in offsets:
        x, y = entity.x + dx, entity.y + dy
        if not gamemap.in_bounds(x, y):
            continue
        if not gamemap.tiles["walkable"][x, y]:
            continue
        if gamemap.get_blocking_entity_at_location(x, y):
            continue
        if any(item.x == x and item.y == y for item in gamemap.items):
            continue
        loot_proto.spawn(gamemap, x, y)
        break


def _get_campfire_cache_items():
    resolved = []
    for name in CAMPFIRE_CACHE_ITEM_IDS:
        proto = globals().get(name)
        if proto:
            resolved.append(proto)
    return resolved


campfire.on_spawn = _setup_campfire_spawn

short_sword_plus = Item(
    char="/", 
    color=(0, 191, 155), 
    name="Short Sword",
    id_name="Short Sword (good)",
    equippable=equippable.ShortSwordPlus()
)
loot_tables.register_loot_item("short_sword_plus", short_sword_plus)

long_sword = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Long Sword",
    id_name="Long Sword",
    equippable=equippable.LongSword()
)

long_sword_plus = Item(
    char="/", 
    color=(0, 191, 155), 
    name="Long Sword",
    id_name="Long Sword (good)",
    equippable=equippable.LongSwordPlus()
)

spear = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Spear",
    id_name="Spear",
    equippable=equippable.Spear(),
    throwable=True
)
loot_tables.register_loot_item("spear", spear)

spear_plus = Item(
    char="/", 
    color=(0, 191, 155), 
    name="Spear",
    id_name="Spear (good)",
    equippable=equippable.SpearPlus(),
    throwable=True
)
loot_tables.register_loot_item("spear_plus", spear_plus)

leather_armor = Item(
    char="[",
    color=(139, 69, 19),
    name="Leather armor",
    id_name="Leather armor",
    equippable=equippable.LeatherArmor(),
    info=f"Stealth penalty: 1"
)
loot_tables.register_loot_item("leather_armor", leather_armor)

chain_mail = Item(
    char="[", 
    color=(139, 69, 19), 
    name="Chain Mail",
    id_name="Chain mail",
    equippable=equippable.ChainMail()
)
loot_tables.register_loot_item("chain_mail", chain_mail)

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

class BreakableWallFactory:
    """Factory that generates individualized breakable walls when spawning."""

    def __init__(self):
        self.loot_table = BREAKABLE_WALL_LOOT_TABLE

    def spawn(self, gamemap, x: int, y: int):
        char, color = self._resolve_graphics(gamemap, x, y)
        fighter = BreakableWallFighter(
            hp=self._roll_hp(),
            base_defense=0,
            base_power=0,
            recover_rate=0,
            base_armor_value=0,
            loot_drop_chance=BREAKABLE_WALL_LOOT_CHANCE,
        )
        inventory = self._build_inventory()
        obstacle = Obstacle(
            char=char,
            color=color,
            name="Suspicious wall",
            ai_cls=Dummy,
            fighter=fighter,
            level=Level(xp_given=2),
            inventory=inventory,
            equipment=Equipment(),
        )
        obstacle.spawn_coord = (x, y)
        obstacle.place(x, y, gamemap)
        return obstacle

    def _roll_hp(self) -> int:
        minimum, maximum = BREAKABLE_WALL_HP_RANGE
        return random.randint(minimum, maximum)

    def _build_inventory(self) -> Inventory:
        stash = []
        if random.random() <= BREAKABLE_WALL_CACHE_CHANCE:
            stash.append(random.choice(self.loot_table))
        capacity = len(stash)
        return Inventory(capacity=capacity, items=list(stash))

    def _resolve_graphics(self, gamemap, x: int, y: int):
        try:
            tile = gamemap.tiles[x, y]
            char_code = int(tile["light"]["ch"])
            fg = tuple(int(c) for c in tile["light"]["fg"])
        except Exception:
            char_code = int(tile_types.breakable_wall["light"]["ch"])
            fg = tuple(int(c) for c in tile_types.breakable_wall["light"]["fg"])
        return chr(char_code), fg


breakable_wall = BreakableWallFactory()

# CREATURES

player_hp = 999 if GOD_MODE else 32
player_max_stamina = 999 if GOD_MODE else 3
player_satiety = 999 if GOD_MODE else 28
player_stealth = 100 if GOD_MODE_STEALTH else 1

player = Actor(
    char="@",
    color=(255, 255, 255),
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=player_hp,
        base_defense=0, 
        base_power=0,
        recover_rate=1, 
        fov=6,
        dmg_mod = (1, 4), 
        base_stealth=1, 
        base_to_hit=0,
        luck=1,
        critical_chance=1,
        satiety=player_satiety,
        stamina=3, 
        max_stamina=player_max_stamina,
        poison_resistance=1,
        super_memory=False,
        lamp_on=True,
    ),
    inventory=Inventory(capacity=20),
    level=Level(level_up_base=20), # Default: 200
)

adventurer = Actor(
    char="@", 
    color=ADVENTURER_COLOR,
    name="Adventurer",
    ai_cls=AdventurerAI,
    #ai_cls=Neutral, # Con esta IA van directos a las escaleras de bajada.
    equipment=Equipment(),
    fighter=Fighter(hp=30, base_defense=2, base_power=0, recover_rate=0, fov=6, dmg_mod = (1, 4)),
    inventory=Inventory(capacity=20, items=loot_tables.build_monster_inventory("Adventurer", amount=4)),
    level=Level(level_up_base=20),
)

# adventurer_unique = Actor(
#     char="@",
#     color=(210, 210, 210),
#     name="Adventurer",

#     ai_cls=Neutral,
#     equipment=Equipment(),
#     fighter=Fighter(hp=32, base_defense=5, base_power=4, recover_rate=0, fov=0, dmg_mod = (1, 4)),
#     inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Adventurer Unique", 3)),
#     level=Level(xp_given=50),
# )

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
    inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Giant rat", amount=1)),
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
        hp=random.randint(7,10), 
        base_defense=2,
        base_power=3, 
        recover_rate=1, 
        fov=random.randint(4, 6), 
        dmg_mod = (1, 2), 
        aggressivity=5, 
        stamina=random.randint(2,4),
        max_stamina=3,
        poison_resistance=6,
        action_time_cost=7,
        woke_ai_cls=HostileEnemy
    ),
    inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Goblin", 1)),
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
        fov=random.randint(3, 6), 
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
        fov=random.randint(2,4), 
        dmg_mod = (1, 6), 
        aggressivity=8, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
        woke_ai_cls=HostileEnemy
    ),
    inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Orc", 1)),
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
        fov=random.randint(3,6), 
        dmg_mod = (1, 6), 
        aggressivity=15, 
        base_to_hit=1, 
        stamina=4, 
        max_stamina=4,
        woke_ai_cls=HostileEnemy
        ),
    inventory=Inventory(capacity=2, items=loot_tables.build_monster_inventory("True Orc", 2)),
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
    inventory=Inventory(capacity=2, items=loot_tables.build_monster_inventory("Bandit", 2)),
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
    inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Giant rat", 1)),
    level=Level(xp_given=2),
    to_eat_drop=meat,
)

def monster_roulette(choices=[orc, goblin, snake]):

    max_choices = len(choices)
    winner = random.randint(0,max_choices - 1)
    for i in range(0, max_choices):
        if i == winner:
            return choices[i]
