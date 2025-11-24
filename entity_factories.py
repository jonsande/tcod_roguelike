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
    OldManAI,
)
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter, Door, BreakableWallFighter, NaturalWeapon
from components.inventory import Inventory
from components.level import Level
from entity import Actor, Item, Book, Decoration, Obstacle, Entity, Chest
import random
import numpy as np
import tile_types
import loot_tables
from equipment_types import EquipmentType
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
    PROFICIENCY_LEVELS,
)

# OBSTACLES:

door = Obstacle(

    char='+',
    color=(93,59,0),
    name="Door",
    ai_cls=Dummy,
    fighter=Door(hp=random.randint(60,80), base_defense=0, strength=0, recover_rate=0, fov=0, base_armor_value=3),
    #obstacle=Door(hp=random.randint(15,35), base_defense=0, strength=0, recover_rate=0, fov=0, base_armor_value=3),
    level=Level(xp_given=1),
    inventory=Inventory(capacity=0),
    equipment=Equipment(),
)

chest = Chest(
    char="ε",
    open_char="ε",
    color=(82, 58, 39),
    #color=(255, 255, 255),
    #char="φ",
    #open_char="φ",
    #color=(32, 38, 19),
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
banana = Item(
    char=")",
    color=(255, 255, 0),
    name="Banana",
    id_name = "Banana",
    consumable=consumable.FoodConsumable(amount=5)
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
descend_scroll = Item(
    char="~",
    color=(166, 0, 255),
    name=scroll_name_roulette(),
    id_name="Descend scroll",
    consumable=consumable.DescendScrollConsumable(),
)
loot_tables.register_loot_item("descend_scroll", descend_scroll)
teleport_scroll = Item(
    char="~",
    color=(0, 255, 255),
    name=scroll_name_roulette(),
    id_name="Teleport scroll",
    consumable=consumable.TeleportScrollConsumable(),
)
loot_tables.register_loot_item("teleport_scroll", teleport_scroll)
prodigious_memory_scroll = Item(
    char="~",
    color=(120, 200, 255),
    name=scroll_name_roulette(),
    id_name="Prodigious memory scroll",
    consumable=consumable.ProdigiousMemoryConsumable(),
)
loot_tables.register_loot_item("prodigious_memory_scroll", prodigious_memory_scroll)

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

note_name_options = [
    "Note #1",
    "Singed paper",
    "Damaged parchment",
    "Scorched scroll",
]

def note_name_generator():
    global note_name_options
    if note_name_options:
        roulette = random.randint(0, len(note_name_options) - 1)
        winner = note_name_options[roulette]
        note_name_options.remove(winner)
        return winner

RING_APPEARANCE_POOL = [
    "Tarnished copper ring",
    "Braided silver ring",
    "Heavy iron band",
    "Ivory-inlaid ring",
    "Azure gemmed ring",
    "Etched obsidian band",
    "Thin brass ring",
    "Speckled stone ring",
    "Twisted gold ring",
    "Polished steel ring",
]
ring_appearance_options = RING_APPEARANCE_POOL.copy()

def ring_appearance_roulette():
    global ring_appearance_options
    if not ring_appearance_options:
        ring_appearance_options = RING_APPEARANCE_POOL.copy()
    roulette = random.randint(0, len(ring_appearance_options) - 1)
    return ring_appearance_options.pop(roulette)


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
        'strength',
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
    consumable=consumable.IncreaseFOVConsumable(amount=2),
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
    #fighter=Fighter(hp=10, base_defense=1, strength=0, recover_rate=0, fov=0),
    fighter=Door(hp=15, base_defense=0, strength=0, recover_rate=0, fov=0, base_armor_value=1, fire_resistance=-4),
    inventory=Inventory(capacity=1),
    level=Level(xp_given=0),
)


def _build_campfire_actor(*, eternal: bool = False) -> Actor:
    fighter = Fighter(
        hp=random.randint(CAMPFIRE_MIN_HP, CAMPFIRE_MAX_HP),
        base_defense=0,
        strength=0,
        recover_rate=0,
        fov=3,
    )
    if eternal:
        fighter.never_extinguish = True
    return Actor(
        char="x",
        color=(255,170,0),
        name="Campfire",
        ai_cls=Dummy,
        equipment=Equipment(),
        fighter=fighter,
        inventory=Inventory(capacity=0),
        level=Level(xp_given=5),
    )


campfire = _build_campfire_actor()
eternal_campfire = _build_campfire_actor(eternal=True)

#campfire = Entity(char="x", color=(218,52,99), name="Campfire", blocks_movement=False)


old_man = Actor(
    char="@",
    color=(150, 150, 150),
    # name="El viejo",
    name="The old man",
    ai_cls=OldManAI,
    equipment=Equipment(),
    fighter=Fighter(
        hp=40,
        base_defense=0,
        strength=0,
        recover_rate=1,
        fov=2,
    ),
    inventory=Inventory(capacity=1),
    level=Level(xp_given=0),
)
old_man.id_name = "The old man"

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
    throwable=True,
    info="A sharp, double-edged blade forged for swift. Ideal for close-quarters combat and silent strikes. Can be thrown at enemies for a quick attack.\nDamage bonus: 3.\nStealth bonus: 1.\nTo-hit bonus: 1.\nWeight: 1 lb.\nRarity: Common."
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
eternal_campfire.on_spawn = _setup_campfire_spawn

def _equip_first_item_of_type(entity: Actor, equipment_type: EquipmentType) -> None:
    """Equip the first item of the requested type found in the entity's inventory."""
    for item in entity.inventory.items:
        if (
            hasattr(item, 'equippable')
            and item.equippable
            and item.equippable.equipment_type == equipment_type
        ):
            entity.equipment.toggle_equip(item, add_message=False)
            break


def _setup_adventurer_equipment(entity: Actor) -> None:
    """Automatically equip a weapon and armor if the adventurer has them in inventory."""
    if not hasattr(entity, 'inventory') or not hasattr(entity, 'equipment'):
        return
    _equip_first_item_of_type(entity, EquipmentType.WEAPON)
    _equip_first_item_of_type(entity, EquipmentType.ARMOR)

def _setup_creature_equipment(entity: Actor) -> None:
    #import ipdb;ipdb.set_trace()
    """Automatically equip a weapon and armor if the creature has them in inventory."""
    #print(f"# DEBUG: _setup_creature_equipment called for {entity.name}")
    if not hasattr(entity, 'inventory') or not hasattr(entity, 'equipment'):
        #print("# DEBUG: Entity missing inventory or equipment")
        return
    _equip_first_item_of_type(entity, EquipmentType.WEAPON)
    _equip_first_item_of_type(entity, EquipmentType.ARMOR)

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

# RINGS

plain_ring = Item(
    char="=",
    color=(205, 127, 50),
    name=ring_appearance_roulette(),
    id_name="Plain ring",
    equippable=equippable.PlainRing(),
)
loot_tables.register_loot_item("plain_ring", plain_ring)

accuracy_ring = Item(
    char="=",
    color=(173, 216, 230),
    name=ring_appearance_roulette(),
    id_name="Ring of Accuracy",
    equippable=equippable.AccuracyRing(),
    info="This precise band sharpens the instincts of any fighter who wears it.",
)
loot_tables.register_loot_item("accuracy_ring", accuracy_ring)

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

# NOTES, BOOKS, NON MAGIC SCROLLS
note_wizard_1 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note Wizard #1",
    info="Hq ho ervtfh hqfdqwdgr, ho qhqñ rhugrlgr, Wlppb, kxíd gh orv jerolqv ulvxhqrv txh or dfhfkedq frq vxv wudpsdv. Gh uhshqwh, xq pdjr dqfldqr dsduhflr hq xqd qxeh gh kxpr sxusxud. '¡Ghwhqhgv, fuhdwxudv gh od vrpeud!', uxlr, odqfdqgr xq khfklyr txh wudqvirupr odv wudpsdv hq ioruhv. Orv jerolqv kxbhurq fkilldqgr, b hq pdjr wrpr od pdqr gh Wlppb: 'Yhq, shtxhqñ, ho krjdu wh hvshud'.")

class BreakableWallFactory:
    """Factory that generates individualized breakable walls when spawning."""

    def __init__(self):
        self.loot_table = BREAKABLE_WALL_LOOT_TABLE

    def spawn(self, gamemap, x: int, y: int):
        char, color = self._resolve_graphics(gamemap, x, y)
        fighter = BreakableWallFighter(
            hp=self._roll_hp(),
            base_defense=0,
            strength=0,
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
        base_defense=1,
        strength=1,
        recover_rate=1, 
        fov=6,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
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
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
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
    fighter=Fighter(
        hp=32, 
        base_defense=3,
        base_to_hit=0,
        strength=1, 
        recover_rate=0, 
        fov=6, 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        base_stealth=1, 
        satiety=28,
        stamina=3, 
        max_stamina=3,
        poison_resistance=2,
        luck=1,
        critical_chance=1,
        super_memory=False,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
    ),
    inventory=Inventory(capacity=20, items=loot_tables.build_monster_inventory("Adventurer", amount=4)),
    level=Level(level_up_base=20),
)

adventurer.on_spawn = _setup_adventurer_equipment

# adventurer_unique = Actor(
#     char="@",
#     color=(210, 210, 210),
#     name="Adventurer",

#     ai_cls=Neutral,
#     equipment=Equipment(),
#     fighter=Fighter(hp=32, base_defense=5, strength=4, recover_rate=0, fov=0, weapon_proficiency = (1, 4)),
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
        base_defense=3,
        strength=1,
        recover_rate=0,
        fov=0,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=5,
        stamina=3,
        max_stamina=3,
        action_time_cost=7,
        luck=0,
        natural_weapon=NaturalWeapon(name="Rat claws", min_dmg=1, max_dmg=3),
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
        base_defense=2,
        strength=1,
        recover_rate=0,
        fov=8,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=15,
        stamina=2,
        max_stamina=2,
        action_time_cost=7,
        natural_weapon=NaturalWeapon(name="Rat claws", min_dmg=1, max_dmg=3),
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=1),
)

cave_bat = Actor(
    char="b",
    color=(94, 94, 150),
    name="Cave bat",
    ai_cls=SneakeEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=3,
        base_defense=1,
        strength=0,
        recover_rate=0,
        fov=8,
        weapon_proficiency=PROFICIENCY_LEVELS["Beginner"],
        base_stealth=4,
        aggressivity=6,
        stamina=2,
        max_stamina=2,
        action_time_cost=4,
        woke_ai_cls=HostileEnemy,
        natural_weapon=NaturalWeapon(name="Needle fangs", min_dmg=0, max_dmg=2),
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=1),
)

def _randomize_goblin_stats(entity: Actor) -> None:
    entity.fighter.hp = random.randint(7, 10)
    entity.fighter.base_defense = random.randint(2, 3)
    # etc.

def _goblin_on_spawn(entity: Actor) -> None:
    """Configure goblins when they spawn so the engine can pickle the factory."""
    _setup_creature_equipment(entity)
    _randomize_goblin_stats(entity)

goblin = Actor(
    char="g",
    color=(60,89,33),
    name="Goblin",
    ai_cls=random.choice([SleepingEnemy, HostileEnemy, Scout]),
    #ai_cls=Scout,
    equipment=Equipment(),
    fighter=Fighter(
        hp=8,
        base_defense=3,
        base_to_hit=0,
        strength=1,
        recover_rate=1,
        fov=random.randint(4, 6),
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=4,
        stamina=random.randint(2,4),
        max_stamina=3,
        poison_resistance=6,
        action_time_cost=7,
        woke_ai_cls=HostileEnemy,
        natural_weapon=NaturalWeapon(name="Goblin claws", min_dmg=1, max_dmg=4, dmg_bonus=0),
    ),
    #inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Goblin", 1)),
    #inventory=Inventory(capacity=3, items=loot_tables.build_monster_inventory("Goblin", 3)),
    #inventory=Inventory(capacity=1, items=[dagger]),
    inventory=Inventory(capacity=3, items=loot_tables.build_monster_inventory("Goblin", amount=1)),
    level=Level(xp_given=3),
)
#goblin.on_spawn = _setup_creature_equipment
goblin.on_spawn = _goblin_on_spawn

monkey = Actor(
    char="y",
    color=(110,4,4),
    name="Monkey",
    ai_cls=random.choice([SleepingEnemy, Scout]),
    #ai_cls=Scout,
    equipment=Equipment(),
    fighter=Fighter(
        hp=8, 
        base_defense=5, 
        strength=1, 
        recover_rate=1, 
        fov=random.randint(3, 6), 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=2, 
        stamina=5, 
        max_stamina=5,
        action_time_cost=6,
        woke_ai_cls=HostileEnemy,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
    ),
    inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Monkey", amount=1)),
    level=Level(xp_given=3),
)
monkey.on_spawn = _setup_creature_equipment

orc = Actor(
    char="o",
    color=(63, 127, 63),
    name="Orc",
    ai_cls=random.choice([SleepingEnemy, HostileEnemy, Scout]),
    equipment=Equipment(),
    fighter=Fighter(
        hp=12, 
        base_defense=4, 
        base_to_hit=1,
        strength=2, 
        recover_rate=0, 
        fov=random.randint(2,4), 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=8, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
        woke_ai_cls=HostileEnemy,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
    ),
    inventory=Inventory(capacity=2, items=loot_tables.build_monster_inventory("Orc", 2)),
    level=Level(xp_given=5),
)
orc.on_spawn = _setup_creature_equipment

true_orc = Actor(
    char="o",
    color=(63, 220, 63),
    name="True Orc",
    ai_cls=random.choice([SleepingEnemy, HostileEnemy, Scout]),
    equipment=Equipment(),
    fighter=Fighter(
        hp=32, 
        base_defense=4, 
        strength=3, 
        recover_rate=0, 
        fov=random.randint(3,6), 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=15, 
        base_to_hit=1, 
        stamina=4, 
        max_stamina=4,
        woke_ai_cls=HostileEnemy,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=1)
        ),
    inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("True Orc", 1)),
    level=Level(xp_given=10),
)
true_orc.on_spawn = _setup_creature_equipment

skeleton = Actor(
    char="k",
    color=(180, 180, 180),
    name="Skeleton",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=16,
        base_defense=4,
        base_to_hit=1,
        base_armor_value=2,
        strength=1,
        recover_rate=0,
        fov=4,
        weapon_proficiency=PROFICIENCY_LEVELS["Apprentice"],
        aggressivity=5,
        stamina=8,
        max_stamina=8,
        action_time_cost=12,
        natural_weapon=NaturalWeapon(name="Bone blade", min_dmg=1, max_dmg=5),
    ),
    inventory=Inventory(capacity=2, items=loot_tables.build_monster_inventory("Skeleton", amount=2)),
    level=Level(xp_given=8),
)
skeleton.on_spawn = _setup_creature_equipment

troll = Actor(
    char="T",
    color=(0, 127, 0),
    name="Troll",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=38, 
        base_defense=2, 
        base_armor_value=5,
        strength=4, 
        recover_rate=5, 
        fov=0, 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=8, 
        stamina=2, 
        max_stamina=2,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=1)
    ),
    inventory=Inventory(capacity=1),
    level=Level(xp_given=14),
)
troll.on_spawn = _setup_creature_equipment

sauron = Actor(
    char="&",
    color=(233,176,96),
    name="Sauron",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=32, 
        base_defense=3, 
        strength=4, 
        recover_rate=12, 
        fov=2, 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=8, 
        stamina=5, 
        max_stamina=5,
    ),
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
        base_defense=3, 
        strength=0, # Las serpientes no hacen daño. Pero pueden envenenar.
        recover_rate=0, 
        fov=1, 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=1, 
        stamina=5, 
        max_stamina=5,
        woke_ai_cls=SneakeEnemy,
        poisons_on_hit=True,
        natural_weapon=NaturalWeapon(name="Bite", min_dmg=0, max_dmg=1, dmg_bonus=0)
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
        base_defense=5, 
        strength=2, 
        recover_rate=1, 
        fov=8, 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        base_stealth=3, 
        base_to_hit=2,
        natural_weapon=NaturalWeapon(name="Cheater fist", min_dmg=1, max_dmg=2, dmg_bonus=1)
    ),
    inventory=Inventory(capacity=5, items=loot_tables.build_monster_inventory("Bandit", 5)),
    level=Level(xp_given=14),
)
bandit.on_spawn = _setup_creature_equipment

cultist = Actor(
    char="c",
    color=(160, 0, 160),
    name="Cultist",
    ai_cls=HostileEnemyPlus,
    equipment=Equipment(),
    fighter=Fighter(
        hp=18,
        base_defense=3,
        base_to_hit=1,
        strength=2,
        recover_rate=1,
        fov=9,
        weapon_proficiency=PROFICIENCY_LEVELS["Apprentice"],
        base_stealth=2,
        aggressivity=8,
        stamina=4,
        max_stamina=4,
        action_time_cost=7,
        natural_weapon=NaturalWeapon(name="Ceremonial dagger", min_dmg=1, max_dmg=4, dmg_bonus=1),
    ),
    inventory=Inventory(capacity=3, items=loot_tables.build_monster_inventory("Cultist", amount=2)),
    level=Level(xp_given=12),
)
cultist.on_spawn = _setup_creature_equipment

sentinel = Actor(
    char="&",
    color=(180,80,110),
    name="Sentinel",
    ai_cls=SentinelEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=12, 
        base_defense=1, 
        strength=3, 
        recover_rate=12, 
        fov=0,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=0, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
    ),
    inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Sentinel", 1)),
    level=Level(xp_given=2),
    to_eat_drop=meat,
)

def monster_roulette(choices=[orc, goblin, snake]):

    max_choices = len(choices)
    winner = random.randint(0,max_choices - 1)
    for i in range(0, max_choices):
        if i == winner:
            return choices[i]
