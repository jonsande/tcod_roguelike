# Aquí generamos los modelos de entidades que existen en el juego

from typing import List
from i18n import _

from components.ai import (
    HostileEnemy,
    HostileEnemyV2,
    HostileEnemyV3,
    ScoutV3,
    #Neutral,
    Dummy,
    ConfusedEnemy,
    HostileEnemyPlus,
    SneakeEnemy,
    SleepingEnemy,
    SentinelEnemy,
    SlimeAI,
    AdventurerAI,
    OldManAI,
    WardenAI,
    MimicSleepAI,
)
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter, Door, BreakableWallFighter, NaturalWeapon
from components.inventory import Inventory
from components.level import Level
from entity import (
    Actor,
    Item,
    Book,
    GeneratedBook,
    ApothecaryBook,
    SilenceBook,
    Decoration,
    Obstacle,
    Entity,
    Chest,
    TableContainer,
    BookShelfContainer,
)
from render_order import RenderOrder
import random
import numpy as np
import tile_types
import loot_tables
import bookgen
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
    MIMIC_CHEST_CHANCE,
)

KEY_COLORS = ("black", "red", "white", "gray")

# OBSTACLES:

door = Obstacle(

    char='+',
    color=(93,59,0),
    name="Door",
    ai_cls=Dummy,
    fighter=Door(
        hp=random.randint(60, 80),
        base_defense=0,
        strength=0,
        recover_rate=50,
        recover_amount=0,
        fov=0,
        base_armor_value=3,
    ),
    #obstacle=Door(hp=random.randint(15,35), base_defense=0, strength=0, recover_rate=0, fov=0, base_armor_value=3),
    level=Level(xp_given=1),
    inventory=Inventory(capacity=0),
    equipment=Equipment(),
    render_order=RenderOrder.DOOR,
)

# Keys
black_key = Item(
    char="?",
    color=(30, 30, 30),
    name="Black key",
    id_name="black_key",
)
red_key = Item(
    char="?",
    color=(200, 30, 30),
    name="Red key",
    id_name="red_key",
)
white_key = Item(
    char="?",
    color=(230, 230, 230),
    name="White key",
    id_name="white_key",
)
gray_key = Item(
    char="?",
    color=(170, 170, 170),
    name="Gray key",
    id_name="gray_key",
)
square_key = Item(
    char="?",
    color=(190, 170, 90),
    name="Square key",
    id_name="square_key",
)
blue_key = Item(
    char="?",
    color=(60, 120, 220),
    name="Blue key",
    id_name="blue_key",
)
chest = Chest(
    char="ε",
    open_char="ε",
    #color=(255, 228, 0), # Amarillo guay
    color=(56, 19, 7), # Marrón oscuro
    #color=(82, 58, 39), # Marrón más claro
    #color=(255, 255, 255),
    #char="φ",
    #open_char="φ",
    #color=(32, 38, 19),
    name="Chest",
    inventory=Inventory(capacity=12, items=[]),
)


def maybe_turn_chest_into_mimic(chest_entity: Chest):
    """Replace a chest with a sleeping mimic, transferring its contents."""
    if not chest_entity or not getattr(chest_entity, "gamemap", None):
        return None
    if getattr(chest_entity, "is_unique_room_chest", False):
        return None
    chance = max(0.0, min(1.0, MIMIC_CHEST_CHANCE))
    if chance <= 0 or random.random() > chance:
        return None

    gamemap = chest_entity.gamemap
    if getattr(gamemap, "is_town", False):
        return None
    mimic_entity = mimic.spawn(gamemap, chest_entity.x, chest_entity.y)
    mimic_entity.char = chest_entity.char
    mimic_entity.color = chest_entity.color
    items = list(getattr(chest_entity.inventory, "items", []))
    chest_entity.inventory.items = []
    if len(items) > mimic_entity.inventory.capacity:
        mimic_entity.inventory.capacity = len(items)
    for item in items:
        item.parent = mimic_entity.inventory
        mimic_entity.inventory.items.append(item)
    gamemap.entities.remove(chest_entity)
    return mimic_entity


def fill_chest_with_items(chest_entity: Chest, items: List[Item]) -> None:
    """Replace the contents of a chest with the provided items."""
    chest_entity.inventory.items = []
    for item in items:
        chest_entity.add_item(item)


def fill_container_with_items(container: Chest, items: List[Item]) -> None:
    """Replace the contents of a chest-like container with the provided items."""
    container.inventory.items = []
    for item in items:
        container.add_item(item)


def fill_table_with_items(table_entity: TableContainer, items: List[Item]) -> None:
    """Backward-compatible wrapper to fill tables with items."""
    fill_container_with_items(table_entity, items)


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
_BONE_SHAPE_DESCRIPTIONS = [
    "Los huesos son largos y arqueados, con bordes pulidos por el roce de la arena.",
    "Ves falanges gruesas y astilladas que forman un abanico irregular.",
    "Reconoces vertebras aplastadas y espinas finas cubiertas de polvo gris.",
    "Las piezas estan ennegrecidas y secas, quebradizas como vidrio viejo.",
    "Hay costillas finas trenzadas entre si, como si algo las hubiese enrollado.",
    "Un fémur queda incrustado en placas rotas; parecen de un caparazon.",
    "Se distinguen discos de cartilago endurecido, perforados en el centro.",
    "Hay algo extraño en estos huesos.",
    "Aún hay carne pegada en los huesos.",
]
_BONE_CREATURE_GUESSES = [
    "No reconoces el tipo de criatura a la que pertenecen",
    "Podrian haber pertenecido a un goblin cazador por la forma de las articulaciones.",
    "La amplitud de la caja toracica sugiere a un aventurero humano.",
    "Todo apunta a una bestia reptiliana con huesos huecos pero flexibles.",
    "Quizas sean restos de un orco joven. Se aprecian claramente unos huecos de colmillos.",
    "Dirias que son de un ogro escuálido; las epifisis apenas estan selladas.",
    "Los segmentos alargados evocan a un lagarto gigante acostumbrado a trepar.",
    "El patron de crecimiento indica criatura subterranea de vida corta.",
]
_BONE_DEATH_SIGNS = [
    "Parece que hubieran intentado quemar una parte.",
    "No hay signos visibles de la causa de la muerte",
    "Se aprecian marcas de mordiscos profundos, como si algo hambriento lo hubiese despedazado.",
    "Las fracturas rectas revelan golpes de arma contundente repetidos.",
    "Las mellas oxidadas apuntan a filos toscos, tal vez cuchillas goblin.",
    "Hay manchas verdosas y nervaduras quemadas, señal de un veneno corrosivo.",
    "Una grieta limpia atraviesa el craneo; parece obra de un virote pesado.",
    "La médula esta seca y cristalizada, como si hubiese sido drenada por magia.",
    "El hueso tiene surcos paralelos, señal de haber sido arrastrado por la corriente.",
    "Algunas piezas han sido roidas con paciencia, dejando bordes lisos y brillantes.",
]


def _generate_bone_description() -> str:
    shape = random.choice(_BONE_SHAPE_DESCRIPTIONS)
    creature = random.choice(_BONE_CREATURE_GUESSES)
    cause = random.choice(_BONE_DEATH_SIGNS)
    return f"{shape} {creature} {cause}"


bones = Item(
    char="%",
    color=(219, 210, 190),
    name="Bones",
    id_name="Bones",
    stackable=False,
    info="Fragmentos de hueso cubiertos de polvo.",
    dynamic_info_factory=_generate_bone_description,
)
loot_tables.register_loot_item("bones", bones)

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
    uses=4,
    max_uses=4,
    stackable=False,
    info="A small pouch of gritty sand. Activate to pick a target within 2 tiles; a valid throw blinds the creature for 2 turns. Blinded foes see almost nothing and suffer -4 to hit and -4 defense. Holds 4 handfuls and disappears when empty. Cannot stack.",
    consumable=consumable.BlindConsumable(number_of_turns=2),
)
loot_tables.register_loot_item("sand_bag", sand_bag)

confusion_scroll_name = scroll_name_roulette()
confusion_scroll = Item(
    char="~",
    color=color_roulette(),
    name=confusion_scroll_name,
    id_name = "Confusion scroll",
    info=f"A {confusion_scroll_name}.",
    id_info="Twists a creature's mind, leaving it confused for several turns.",
    consumable=consumable.TargetedConfusionConsumable(number_of_turns=10),
)
loot_tables.register_loot_item("confusion_scroll", confusion_scroll)

paralisis_scroll_name = scroll_name_roulette()
paralisis_scroll = Item(
    char="~",
    color=color_roulette(),
    name=paralisis_scroll_name,
    id_name = "Paralisis scroll",
    info=f"A {paralisis_scroll_name}.",
    id_info="Locks a target in place, paralyzing it for a short time.",
    consumable=consumable.ParalisisConsumable(number_of_turns=10),
)

lightning_scroll_name = scroll_name_roulette()
lightning_scroll = Item(
    char="~",
    color=color_roulette(),
    name=lightning_scroll_name,
    id_name = "Lightning scroll",
    info=f"A {lightning_scroll_name}.",
    id_info="Calls a lightning bolt to smite the nearest foe for heavy damage.",
    consumable=consumable.LightningDamageConsumable(),
)

fireball_scroll_name = scroll_name_roulette()
fireball_scroll = Item(
    char="~",
    color=color_roulette(),
    name=fireball_scroll_name,
    id_name = "Fireball scroll",
    info=f"A {fireball_scroll_name}.",
    id_info="Detonates a fireball with a small radius at a chosen spot.",
    consumable=consumable.FireballDamageConsumable(damage=12, radius=2),
)
descend_scroll_name = scroll_name_roulette()
descend_scroll = Item(
    char="~",
    color=(166, 0, 255),
    name=descend_scroll_name,
    id_name="Descend scroll",
    info=f"A {descend_scroll_name}.",
    id_info="Opens a rune-lined vortex that drops you to the next floor.",
    consumable=consumable.DescendScrollConsumable(),
)
loot_tables.register_loot_item("descend_scroll", descend_scroll)
teleport_scroll_name = scroll_name_roulette()
teleport_scroll = Item(
    char="~",
    color=(0, 255, 255),
    name=teleport_scroll_name,
    id_name="Teleport scroll",
    info=f"A {teleport_scroll_name}.",
    id_info="Warps you to a random free tile on this floor.",
    consumable=consumable.TeleportScrollConsumable(),
)
loot_tables.register_loot_item("teleport_scroll", teleport_scroll)
prodigious_memory_scroll_name = scroll_name_roulette()
prodigious_memory_scroll = Item(
    char="~",
    color=(120, 200, 255),
    name=prodigious_memory_scroll_name,
    id_name="Prodigious memory scroll",
    info=f"A {prodigious_memory_scroll_name}.",
    id_info="Brands the dungeon's layout into your mind permanently.",
    consumable=consumable.ProdigiousMemoryConsumable(),
)
loot_tables.register_loot_item("prodigious_memory_scroll", prodigious_memory_scroll)
identify_scroll_name = scroll_name_roulette()
identify_scroll = Item(
    char="~",
    color=color_roulette(),
    name=identify_scroll_name,
    id_name="Identify scroll",
    info=f"A {identify_scroll_name}.",
    id_info="Reveals the true nature of an item you carry.",
    consumable=consumable.IdentificationScrollConsumable(),
)
loot_tables.register_loot_item("identify_scroll", identify_scroll)
remove_curse_scroll_name = scroll_name_roulette()
remove_curse_scroll = Item(
    char="~",
    color=(180, 120, 255),
    name=remove_curse_scroll_name,
    id_name="Remove curse scroll",
    info=f"A {remove_curse_scroll_name}.",
    id_info="Breaks the curse on a chosen equippable item.",
    consumable=consumable.RemoveCurseConsumable(),
)
loot_tables.register_loot_item("remove_curse_scroll", remove_curse_scroll)

# Breakable wall loot table (scrolls and similar findings hidden in walls)
BREAKABLE_WALL_LOOT_TABLE = [
    confusion_scroll,
    paralisis_scroll,
    lightning_scroll,
    fireball_scroll,
    identify_scroll,
    remove_curse_scroll,
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
    "Blue Note",
    "Singed paper",
    "Damaged parchment",
    "Scorched scroll",
    "Crumpled paper",
    "Wet paper",
    "Battered book",
    "Smelly paper",
    "Strange note",
    "Manuscript",
    "Torn Letter",
    "Faded Journal Page",
    "Dust-covered Tome",
    "Fragmented Scroll",
    "Oil-stained Note",
    "Blood-spattered Parchment",
    "Cracked Leather Notebook",
    "Old Expedition Log",
    "Unfinished Manuscript",
    "Ink-blotted Paper",
    "Charcoal-marked Draft",
    "Frayed Message Slip",
    "Weathered Diary Scrap",
    "Rune-etched Paper",
    "Tattered Codex Leaf",
    "Ragged Field Report",
    "Cryptic Handwriting Sample",
    "Warped Parchment Roll",
    "Mold-specked Memo",
    "Secretive Correspondence",
    "Illegible Scribbles",
    "Traveler’s Note",
    "Curled-edge Scroll",
    "Old Archive Page",
    "Loose Binding Sheet",
    "Strange Symbol Sheet",
    "Unsealed Letter",
    "Merchant’s Ledger Fragment",
    "Scholar’s Margin Notes",
    "Broken-seal Document",
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
    "Runed crimson ring",
    "Mossy jade ring",
    "Star-etched bronze ring",
    "Dark glass ring",
    "Opaline swirl ring",
    "Woven bone ring",
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
    name=(health_potion_name := potion_name_roulette()),
    id_name = "Health potion",
    info=f"A {health_potion_name}.",
    id_info="Restores a decent amount of health and clears any lingering confusion.",
    consumable=consumable.HealingConsumable(amount=random.randint(6, 12) + 4),
    throwable=True,
)
loot_tables.register_loot_item("health_potion", health_potion)

strength_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(strength_potion_name := potion_name_roulette()),
    id_name = "Strength potion",
    info=f"A {strength_potion_name}.",
    id_info="Permanently bolsters your strength.",
    consumable=consumable.StrenghtConsumable(amount=1),
    throwable=True,
)

poison_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(poison_potion_name := potion_name_roulette()),
    id_name = "Poison potion",
    info=f"A {poison_potion_name}.",
    id_info="Unknown use poisons the drinker; once identified it can coat your weapon to poison enemies.",
    #consumable=consumable.PoisonConsumable(amount=1, counter=random.randint(6,10)),
    consumable=consumable.PoisonConsumable(amount=1, counter=15),
    throwable=True,
)
loot_tables.register_loot_item("poison_potion", poison_potion)

antidote = Item(
    char="!",
    color=(200, 200, 200),
    name=(antidote_name := potion_name_roulette()),
    id_name = "Antidote",
    info=f"A {antidote_name}.",
    id_info="Neutralizes poison or otherwise has no effect.",
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
    name=(power_potion_name := potion_name_roulette()),
    id_name = "Power brew",
    info=f"A {power_potion_name}.",
    id_info="Temporarily surges your strength for several turns.",
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
    name=(precission_potion_name := potion_name_roulette()),
    id_name = "Amphetamine brew",
    info=f"A {precission_potion_name}.",
    id_info="Heightens focus, granting a temporary boost to accuracy.",
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
    name=(stamina_potion_name := potion_name_roulette()),
    id_name = "Restore stamina Potion",
    info=f"A {stamina_potion_name}.",
    id_info="Restores your stamina to full.",
    consumable=consumable.RestoreStaminaConsumable(),
    throwable=True,
)
loot_tables.register_loot_item("stamina_potion", stamina_potion)
increase_max_stamina = Item(
    char="!",
    color=(200, 200, 200),
    name=(increase_max_stamina_name := potion_name_roulette()),
    id_name = "Potion of Lasting Vigor",
    info=f"A {increase_max_stamina_name}.",
    id_info="Permanently increases your maximum stamina.",
    consumable=consumable.IncreaseMaxStaminaConsumable(amount=1),
    throwable=True,
)
life_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(life_potion_name := potion_name_roulette()),
    id_name = "Life potion",
    info=f"A {life_potion_name}.",
    id_info="Permanently increases your maximum HP and heals you fully.",
    consumable=consumable.IncreaseMaxHPConsumable(amount=8),
    throwable=True,
)

infra_vision_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(infra_vision_potion_name := potion_name_roulette()),
    id_name="Potion of True Sight",
    info=f"A {infra_vision_potion_name}.",
    id_info="Permanently sharpens your vision, widening your field of view.",
    consumable=consumable.IncreaseFOVConsumable(amount=2),
    throwable=True,
)

temporal_infra_vision_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(temporal_infra_vision_potion_name := potion_name_roulette()),
    id_name="Potion of Flash Sight",
    info=f"A {temporal_infra_vision_potion_name}.",
    id_info="Temporarily expands your field of view dramatically.",
    consumable=consumable.TemporalFOVConsumable(min_turns=12, max_turns=32, amount=6),
    throwable=True,
)
blindness_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(blindness_potion_name := potion_name_roulette()),
    id_name="Potion of Blinding Darkness",
    info=f"A {blindness_potion_name}.",
    id_info="Blinds the drinker, drastically shrinking sight.",
    consumable=consumable.BlindnessConsumable(amount=-32),
    throwable=True,
)

confusion_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(confusion_potion_name := potion_name_roulette()),
    id_name = "Confusion potion",
    info=f"A {confusion_potion_name}.",
    id_info="Leaves the drinker confused for a while.",
    consumable=consumable.ConfusionConsumable(random.randint(12, 32)),
    throwable=True,
)
paralysis_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(paralysis_potion_name := potion_name_roulette()),
    id_name = "Paralysis potion",
    info=f"A {paralysis_potion_name}.",
    id_info="Paralyzes the drinker for several turns.",
    consumable=consumable.ParalysisConsumable(min_turns=12, max_turns=32),
    throwable=True,
)
petrification_potion = Item(
    char="!",
    color=(200, 200, 200),
    name=(petrification_potion_name := potion_name_roulette()),
    id_name="Petrification potion",
    info=f"A {petrification_potion_name}.",
    id_info="Turns the drinker to stone, freezing them in place indefinitely.",
    consumable=consumable.PetrifyConsumable(),
    throwable=True,
)

POTION_ITEMS = [
    health_potion,
    strength_potion,
    poison_potion,
    antidote,
    power_potion,
    precission_potion,
    stamina_potion,
    increase_max_stamina,
    life_potion,
    infra_vision_potion,
    temporal_infra_vision_potion,
    blindness_potion,
    confusion_potion,
    paralysis_potion,
    petrification_potion,
]


def identify_all_potions() -> None:
    for potion in POTION_ITEMS:
        if not getattr(potion, "identified", False):
            potion.identify()

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

# Container version used in procedural generation (non-attackable).
table = TableContainer(
    char="#",
    open_char="#",
    color=(100, 100, 100),
    name="Table",
    inventory=Inventory(capacity=6, items=[]),
)

# Bookshelf container with its own loot configuration.
bookshelf = BookShelfContainer(
    char="π",
    open_char="π",
    color=(120, 90, 60),
    name="Bookshelf",
    inventory=Inventory(capacity=6, items=[]),
)


def _build_campfire_actor(*, eternal: bool = False) -> Actor:
    fighter = Fighter(
        hp=random.randint(CAMPFIRE_MIN_HP, CAMPFIRE_MAX_HP),
        base_defense=0,
        strength=0,
        recover_rate=50,
        recover_amount=0,
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
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=40,
        base_defense=0,
        strength=0,
        recover_rate=50,
        recover_amount=1,
        fov=2,
    ),
    inventory=Inventory(capacity=1),
    level=Level(xp_given=0),
    faction="human",
)
old_man.id_name = "The old man"

prisioner = Actor(
    char="@",
    color=(180, 180, 180),
    name="Prisioner",
    ai_cls=Dummy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=20,
        base_defense=0,
        strength=0,
        recover_rate=50,
        recover_amount=0,
        fov=2,
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=0),
)
prisioner.id_name = "prisioner"

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
    id_name="Dagger",
    info="A sharp, double-edged blade forged for swift. Ideal for close-quarters combat and silent strikes. Can be thrown at enemies for a quick attack."
)
loot_tables.register_loot_item("dagger", dagger)

dagger_plus = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Dagger",
    id_name="Dagger (good)",
    equippable=equippable.DaggerPlus(),
    info="A finely balanced dagger with a keener edge and guard."
)
loot_tables.register_loot_item("dagger_plus", dagger_plus)

#sword = Item(char="/", color=(0, 191, 255), name="Sword", equippable=equippable.Sword())

short_sword = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Short Sword",
    id_name="Short Sword",
    equippable=equippable.ShortSword(),
    info="A compact blade favored by scouts and skirmishers."
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
    if getattr(entity.equipment, "has_head_slot", False):
        _equip_first_item_of_type(entity, EquipmentType.HEADARMOR)
    if getattr(entity.equipment, "has_cloak_slot", False):
        _equip_first_item_of_type(entity, EquipmentType.CLOAK)

def _setup_creature_equipment(entity: Actor) -> None:
    #import ipdb;ipdb.set_trace()
    """Automatically equip a weapon and armor if the creature has them in inventory."""
    #print(f"# DEBUG: _setup_creature_equipment called for {entity.name}")
    if not hasattr(entity, 'inventory') or not hasattr(entity, 'equipment'):
        #print("# DEBUG: Entity missing inventory or equipment")
        return
    _equip_first_item_of_type(entity, EquipmentType.WEAPON)
    _equip_first_item_of_type(entity, EquipmentType.ARMOR)
    if getattr(entity.equipment, "has_head_slot", False):
        _equip_first_item_of_type(entity, EquipmentType.HEADARMOR)
    if getattr(entity.equipment, "has_cloak_slot", False):
        _equip_first_item_of_type(entity, EquipmentType.CLOAK)

short_sword_plus = Item(
    char="/", 
    color=(0, 191, 155), 
    name="Short Sword",
    id_name="Short Sword (good)",
    equippable=equippable.ShortSwordPlus(),
    info="A short sword with superior temper and bite."
)
loot_tables.register_loot_item("short_sword_plus", short_sword_plus)

long_sword = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Long Sword",
    id_name="Long Sword",
    equippable=equippable.LongSword(),
    info="A versatile blade with reach enough to keep foes at bay."
)

long_sword_plus = Item(
    char="/", 
    color=(0, 191, 155), 
    name="Long Sword",
    id_name="Long Sword (good)",
    equippable=equippable.LongSwordPlus(),
    info="A masterwork long sword with a razor-straight edge."
)

spear = Item(
    char="/", 
    color=(0, 191, 255), 
    name="Spear",
    id_name="Spear",
    equippable=equippable.Spear(),
    throwable=True,
    info="A sturdy haft tipped with iron; easy to thrust or throw."
)
loot_tables.register_loot_item("spear", spear)

spear_plus = Item(
    char="/", 
    color=(0, 191, 155), 
    name="Spear",
    id_name="Spear (good)",
    equippable=equippable.SpearPlus(),
    throwable=True,
    info="A well-balanced spear with a hardened point."
)
loot_tables.register_loot_item("spear_plus", spear_plus)

arrow = Item(
    char=")",
    color=(188, 170, 110),
    name="Arrow",
    id_name="Arrow",
    throwable=True,
    projectile_dice=(1, 4),
    projectile_bonus=2,
    projectile_type="arrow",
    projectile_destroy_chance_on_hit=0.5,
    bundle_range=(2, 6),
    info="A straight arrow with a sharp iron tip. Damage: 1d4+2.",
)
loot_tables.register_loot_item("arrow", arrow)

long_bow = Item(
    char="{",
    color=(150, 110, 70),
    name="Long bow",
    id_name="Long bow",
    equippable=equippable.LongBow(),
    stackable=False,
    info="A tall bow with great draw strength. Needs arrows and must be equipped to fire up to 8 tiles away. Ranged: +1 to hit, adds your Strength to damage. Melee: unwieldy (-3 to hit, 0 damage).",
)
loot_tables.register_loot_item("long_bow", long_bow)

tunneling_staff = Item(
    char="|",
    color=(170, 120, 60),
    name="Tunneling staff",
    id_name="Tunneling staff",
    equippable=equippable.TunnelingStaff(),
    stackable=False,
    info="A rune-scarred staff that can bore through stone. Equip it in your weapon slot; while equipped, activate it to select a visible wall or breakable barrier and open a passage.",
)
loot_tables.register_loot_item("tunneling_staff", tunneling_staff)

small_shield = Item(
    char="(",
    color=(160, 160, 160),
    name="Small shield",
    id_name="Small shield",
    equippable=equippable.SmallShield(),
    info="A light buckler that turns aside glancing blows.",
)
loot_tables.register_loot_item("small_shield", small_shield)

medium_shield = Item(
    char="(",
    color=(120, 120, 120),
    name="Medium shield",
    id_name="Medium shield",
    equippable=equippable.MediumShield(),
    info="A balanced shield that protects well but hampers aim.",
)
loot_tables.register_loot_item("medium_shield", medium_shield)

large_shield = Item(
    char="(",
    color=(90, 90, 90),
    name="Large shield",
    id_name="Large shield",
    equippable=equippable.LargeShield(),
    info="A heavy shield that offers strong protection at a cost to accuracy.",
)
loot_tables.register_loot_item("large_shield", large_shield)

leather_armor = Item(
    char="[",
    color=(139, 69, 19),
    name="Leather armor",
    id_name="Leather armor",
    equippable=equippable.LeatherArmor(),
    info="Layered hide that cushions blows without total freedom of movement.",
)
loot_tables.register_loot_item("leather_armor", leather_armor)

chain_mail = Item(
    char="[", 
    color=(139, 69, 19), 
    name="Chain Mail",
    id_name="Chain mail",
    equippable=equippable.ChainMail(),
    info="Interlocking rings of steel that weigh heavy but stop blades.",
)
loot_tables.register_loot_item("chain_mail", chain_mail)

leather_cap = Item(
    char="]",
    color=(160, 82, 45),
    name="Leather cap",
    id_name="Leather cap",
    equippable=equippable.LeatherCap(),
    info="A supple cap that shields the skull without getting in the way.",
)
loot_tables.register_loot_item("leather_cap", leather_cap)

scout_hood = Item(
    char="]",
    color=(34, 139, 34),
    name="Scout hood",
    id_name="Scout hood",
    equippable=equippable.ScoutHood(),
    info="A light hood favored by quick scouts. Improves aim and stealth.",
)
loot_tables.register_loot_item("scout_hood", scout_hood)

iron_helmet = Item(
    char="]",
    color=(190, 190, 190),
    name="Iron helmet",
    id_name="Iron helmet",
    equippable=equippable.IronHelmet(),
    info="Forged iron helm that protects the head at the expense of comfort.",
)
loot_tables.register_loot_item("iron_helmet", iron_helmet)

orcish_war_helm = Item(
    char="]",
    color=(139, 0, 0),
    name="Orcish war helm",
    id_name="Orcish war helm",
    equippable=equippable.OrcishWarHelm(),
    info="Spiked helm used by warbands. Heavy but empowering.",
)
loot_tables.register_loot_item("orcish_war_helm", orcish_war_helm)

cloak = Item(
    char="}",
    color=(120, 80, 40),
    name="Cloak",
    id_name="Cloak",
    equippable=equippable.Cloak(),
    info="A sturdy travel cloak that softens footfalls.",
)
loot_tables.register_loot_item("cloak", cloak)

# RINGS

plain_ring = Item(
    char="=",
    color=(205, 127, 50),
    name=ring_appearance_roulette(),
    id_name="Plain ring",
    equippable=equippable.PlainRing(),
    info="I don't feel anything special about this ring",
    id_info="An unadorned band; perhaps it will resonate with subtle power.",
)
loot_tables.register_loot_item("plain_ring", plain_ring)

accuracy_ring = Item(
    char="=",
    color=(173, 216, 230),
    name=ring_appearance_roulette(),
    id_name="Ring of Accuracy",
    equippable=equippable.AccuracyRing(),
    info="There's something strange about this ring",
    id_info="This precise band sharpens the instincts of any fighter who wears it.",
)
loot_tables.register_loot_item("accuracy_ring", accuracy_ring)

strength_ring = Item(
    char="=",
    color=(178, 34, 34),
    name=ring_appearance_roulette(),
    id_name="Ring of Strength",
    equippable=equippable.StrengthRing(),
    info="There's something strange about this ring",
    id_info="A heavy band that lends its wearer raw brawn.",
)
loot_tables.register_loot_item("strength_ring", strength_ring)

farsight_ring = Item(
    char="=",
    color=(135, 206, 235),
    name=ring_appearance_roulette(),
    id_name="Ring of Far Sight",
    equippable=equippable.FarSightRing(),
    info="There's something strange about this ring",
    id_info="A bright band that widens the horizon of your vision.",
)
loot_tables.register_loot_item("farsight_ring", farsight_ring)

vigor_ring = Item(
    char="=",
    color=(50, 205, 50),
    name=ring_appearance_roulette(),
    id_name="Ring of Vigor",
    equippable=equippable.VigorRing(),
    info="There's something strange about this ring",
    id_info="A band warm to the touch that bolsters lasting stamina.",
)
loot_tables.register_loot_item("vigor_ring", vigor_ring)

antidote_ring = Item(
    char="=",
    color=(60, 179, 113),
    name=ring_appearance_roulette(),
    id_name="Ring of Antivenom",
    equippable=equippable.AntidoteRing(),
    info="There's something strange about this ring",
    id_info="Its surface is cool and clean, warding off toxins.",
)
loot_tables.register_loot_item("antidote_ring", antidote_ring)

memory_ring = Item(
    char="=",
    color=(218, 165, 32),
    name=ring_appearance_roulette(),
    id_name="Ring of Memory",
    equippable=equippable.MemoryRing(),
    info="There's something strange about this ring",
    id_info="A slender loop etched with sigils that refuse to be forgotten.",
)
loot_tables.register_loot_item("memory_ring", memory_ring)

recovery_ring = Item(
    char="=",
    color=(176, 196, 222),
    name=ring_appearance_roulette(),
    id_name="Ring of Recovery",
    equippable=equippable.RecoveryRing(),
    info="There's something strange about this ring",
    id_info="A cool band that quickens the pace of healing.",
)
loot_tables.register_loot_item("recovery_ring", recovery_ring)

guard_ring = Item(
    char="=",
    color=(169, 169, 169),
    name=ring_appearance_roulette(),
    id_name="Ring of Guarding",
    equippable=equippable.GuardRing(),
    info="There's something strange about this ring",
    id_info="A thick ring set with a shard of mail, lending steady defense.",
)
loot_tables.register_loot_item("guard_ring", guard_ring)

fortune_ring = Item(
    char="=",
    color=(255, 215, 0),
    name=ring_appearance_roulette(),
    id_name="Ring of Fortune",
    equippable=equippable.FortuneRing(),
    info="There's something strange about this ring",
    id_info="Its inner edge hums faintly, tilting fate in your favor.",
)
loot_tables.register_loot_item("fortune_ring", fortune_ring)

cursed_weakness_ring = Item(
    char="=",
    color=(128, 0, 0),
    name=ring_appearance_roulette(),
    id_name="Cursed Ring of Weakness",
    equippable=equippable.CursedWeaknessRing(),
    info="There's something strange about this ring",
    id_info="This ring saps your might and refuses to be removed.",
)
loot_tables.register_loot_item("cursed_weakness_ring", cursed_weakness_ring)

cursed_myopia_ring = Item(
    char="=",
    color=(72, 61, 139),
    name=ring_appearance_roulette(),
    id_name="Cursed Ring of Myopia",
    equippable=equippable.CursedMyopiaRing(),
    info="There's something strange about this ring",
    id_info="Wearing it narrows your world to a few paces—and it clings to you.",
)
loot_tables.register_loot_item("cursed_myopia_ring", cursed_myopia_ring)

cursed_fatigue_ring = Item(
    char="=",
    color=(85, 107, 47),
    name=ring_appearance_roulette(),
    id_name="Cursed Ring of Fatigue",
    equippable=equippable.CursedFatigueRing(),
    info="There's something strange about this ring",
    id_info="A dull band that drains your stamina and binds itself to you.",
)
loot_tables.register_loot_item("cursed_fatigue_ring", cursed_fatigue_ring)

cursed_lethargy_ring = Item(
    char="=",
    color=(112, 128, 144),
    name=ring_appearance_roulette(),
    id_name="Cursed Ring of Lethargy",
    equippable=equippable.CursedLethargyRing(),
    info="There's something strange about this ring",
    id_info="Its chill slows recovery, and it will not let go.",
)
loot_tables.register_loot_item("cursed_lethargy_ring", cursed_lethargy_ring)

cursed_vulnerability_ring = Item(
    char="=",
    color=(105, 105, 105),
    name=ring_appearance_roulette(),
    id_name="Cursed Ring of Vulnerability",
    equippable=equippable.CursedVulnerabilityRing(),
    info="There's something strange about this ring",
    id_info="You feel exposed—and trapped—as soon as you wear it.",
)
loot_tables.register_loot_item("cursed_vulnerability_ring", cursed_vulnerability_ring)

cursed_misfortune_ring = Item(
    char="=",
    color=(123, 104, 238),
    name=ring_appearance_roulette(),
    id_name="Cursed Ring of Misfortune",
    equippable=equippable.CursedMisfortuneRing(),
    info="There's something strange about this ring",
    id_info="Luck withers under its touch, and it clings like a shackle.",
)
loot_tables.register_loot_item("cursed_misfortune_ring", cursed_misfortune_ring)

# ARTIFACTS

the_artifact = Item(
    char="*", 
    color=(139, 69, 19), 
    name="The Artifact",
    id_name="The Artifact",
)

grial = Item(
    char="y", 
    color=(139, 69, 19), 
    name="Grial",
    id_name="The Grial",
    equippable=equippable.Grial(),
    info="A sacred chalice that shields its bearer with unseen grace.",
)

goblin_tooth_amulet = Item(
    char='"', 
    color=(139, 69, 19), 
    name="Tooth necklace",
    id_name="Xzy, the goblin tooth amulet",
    equippable=equippable.GoblinAmulet(),
    info="A necklace strung with goblin teeth—fetid, eerie, and oddly potent.",
)

# NOTES, BOOKS, NON MAGIC SCROLLS

# DYNAMIC BOOKS
generated_book = GeneratedBook(
    char="~",
    color=(200, 180, 120),
    title_fn=bookgen.random_book_title,
    content_fn=bookgen.random_book_fragment,
    id_name="Book",
)
generated_book._spawn_key = "generated_book"
loot_tables.register_loot_item("generated_book", generated_book)

# STATIC BOOKS
def _build_static_book(key: str) -> Book:
    title, content = bookgen.get_static_book_payload(key)
    return Book(
        char="~",
        color=(210, 200, 170),
        name=title,
        id_name=title,
        info=content,
        stackable=False,
    )

forgotten_canticle = _build_static_book("forgotten_canticle")
forgotten_canticle._spawn_key = "forgotten_canticle"
loot_tables.register_loot_item("forgotten_canticle", forgotten_canticle)

architect_notes = _build_static_book("architect_notes")
architect_notes._spawn_key = "architect_notes"
loot_tables.register_loot_item("architect_notes", architect_notes)

red_tower_mails = _build_static_book("red_tower_mails")
red_tower_mails._spawn_key = "red_tower_mails"
loot_tables.register_loot_item("red_tower_mails", red_tower_mails)

corridor_chronicles = _build_static_book("corridor_chronicles")
corridor_chronicles._spawn_key = "corridor_chronicles"
loot_tables.register_loot_item("corridor_chronicles", corridor_chronicles)

fungi_book = _build_static_book("fungi_book")
fungi_book._spawn_key = "fungi_book"
loot_tables.register_loot_item("fungi_book", fungi_book)

living_stoone_theory = _build_static_book("living_stoone_theory")
living_stoone_theory._spawn_key = "living_stoone_theory"
loot_tables.register_loot_item("living_stoone_theory", living_stoone_theory)

nine_lanterns_codex = _build_static_book("nine_lanterns_codex")
nine_lanterns_codex._spawn_key = "nine_lanterns_codex"
loot_tables.register_loot_item("nine_lanterns_codex", nine_lanterns_codex)

coal_stories = _build_static_book("coal_stories")
coal_stories._spawn_key = "coal_stories"
loot_tables.register_loot_item("coal_stories", coal_stories)

crack_finder_book = _build_static_book("crack_finder_book")
crack_finder_book._spawn_key = "crack_finder_book"
loot_tables.register_loot_item("crack_finder_book", crack_finder_book)

lower_cavern_bestiary = _build_static_book("lower_cavern_bestiary")
lower_cavern_bestiary._spawn_key = "lower_cavern_bestiary"
loot_tables.register_loot_item("lower_cavern_bestiary", crack_finder_book)

sixteen_rings = _build_static_book("sixteen_rings")
sixteen_rings._spawn_key = "sixteen_rings"
loot_tables.register_loot_item("sixteen_rings", sixteen_rings)

wanderers_diary = _build_static_book("wanderers_diary")
wanderers_diary._spawn_key = "wanderers_diary"
loot_tables.register_loot_item("wanderers_diary", wanderers_diary)

tired_librarian_notes = _build_static_book("tired_librarian_notes")
tired_librarian_notes._spawn_key = "tired_librarian_notes"
loot_tables.register_loot_item("tired_librarian_notes", tired_librarian_notes)

# MAGIC BOOKS
apothecary_book = ApothecaryBook(
    char="~",
    color=(210, 200, 170),
    name="Apothecary's Book",
    id_name="Apothecary's Book",
    info=(
        "Un libro que permite identificar hierbas y distintas pócimas, tónicos y "
        "medicinas creadas con ellas."
    ),
    stackable=False,
)
apothecary_book._spawn_key = "apothecary_book"
loot_tables.register_loot_item("apothecary_book", apothecary_book)

silence_book = SilenceBook(
    char="~",
    color=(210, 200, 170),
    name="Códice del Silencio",
    id_name="Códice del Silencio",
    info=(
        "Un libro envuelto en harapos. Sus páginas describen el arte "
        "de silenciar el mundo a través de palabras."
    ),
    stackable=False,
)
silence_book._spawn_key = "silence_book"
loot_tables.register_loot_item("silence_book", silence_book)

# Notas inútiles o pistas falsas
note_wizard_1 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note Wizard #1",
    info="Hq ho ervtfh hqfdqwdgr, ho qhqñ rhugrlgr, Wlppb, kxíd gh orv jerolqv ulvxhqrv txh or dfhfkedq frq vxv wudpsdv. Gh uhshqwh, xq pdjr dqfldqr dsduhflr hq xqd qxeh gh kxpr sxusxud. '¡Ghwhqhgv, fuhdwxudv gh od vrpeud!', uxlr, odqfdqgr xq khfklyr txh wudqvirupr odv wudpsdv hq ioruhv. Orv jerolqv kxbhurq fkilldqgr, b hq pdjr wrpr od pdqr gh Wlppb: 'Yhq, shtxhqñ, ho krjdu wh hvshud'."
    )

# Notas útiles
# TODO: el número identificativo del id_name hay que relativizarlo. Que sea aleatorio en cada partida.
library_clue_1 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note about a library #1",
    info="Busco el pasillo y el lugar correcto desde hace semanas. Estoy desesperando. Todas las pistas acaban llevándome a un mismo lugar, pero allí no hay nada. Algo se me escapa."
    )
library_clue_2 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note about a library #2",
    info="...abandono este libro de notas en el escritorio de la entrada. Espero que los apuntes que he ido haciendo en él puedan servirle a alguien algún día."
    )
library_clue_3 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note about a library #3",
    info="He perdido toda esperanza. No puedo continuar, y tampoco escapar. Estoy condenado."
    )
library_clue_4 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note about a library #4",
    info="Sé que aparece en cierto momento del día. He descubierto que ese duende o demonio o lo que sea aparece por los pasillos del 8a de forma regular. Debería encontrar un modo de medir el tiempo."
    )
library_clue_5 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note about a library #5",
    info="Ese ser despreciable se siente atraído por algo que hay en las estanterías de ese pasillo. No sé lo que es."
    )
library_clue_6 = Book(
    char="~",
    color=(230,230,230),
    name=note_name_generator(), 
    id_name="Note about a library #6",
    info="He revisado todos los libros del pasillo 8a. Nada."
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

mimic = Actor(
    char=chest.char,
    color=chest.color,
    name="Chest",
    ai_cls=MimicSleepAI,
    equipment=Equipment(),
    fighter=Fighter(
        hp=16,
        base_defense=3,
        strength=1,
        recover_rate=50,
        recover_amount=1,
        fov=1,
        foh=5,
        weapon_proficiency=PROFICIENCY_LEVELS["Novice"],
        aggressivity=0,
        stamina=3,
        max_stamina=3,
        action_time_cost=12,
        natural_weapon=NaturalWeapon(name="Bite", min_dmg=1, max_dmg=10),
    ),
    inventory=Inventory(capacity=12),
    level=Level(xp_given=12),
)
mimic.id_name = "Mimic"

player = Actor(
    char="@",
    color=(255, 255, 255),
    name="Player",
    ai_cls=HostileEnemyV3, # Si usamos Dummy disparará los sonidos de un Dummy. Su IA, por lo demás, se ignora.
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=player_hp,
        base_defense=1,
        strength=1,
        recover_rate=50,
        recover_amount=1,
        fov=2,
        foh=8,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        base_stealth=3, 
        base_to_hit=0,
        luck=1,
        critical_chance=1,
        satiety=player_satiety,
        action_time_cost=10,
        stamina=3,
        max_stamina=player_max_stamina,
        poison_resistance=1,
        super_memory=False,
        lamp_on=False,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=0, max_dmg=2, dmg_bonus=0),
        can_open_doors=True,
    ),
    inventory=Inventory(capacity=35),
    level=Level(level_up_base=20), # Default: 200
    faction="human",
)

adventurer = Actor(
    char="@",
    color=ADVENTURER_COLOR,
    name="Adventurer",
    ai_cls=AdventurerAI,
    #ai_cls=Neutral, # Con esta IA van directos a las escaleras de bajada.
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=32, 
        base_defense=3,
        base_to_hit=0,
        strength=1, 
        recover_rate=50,
        recover_amount=0,
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
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
    ),
    inventory=Inventory(capacity=20, loot_table_key="Adventurer", loot_amount=4),
    level=Level(level_up_base=20),
    faction="human",
)

adventurer.on_spawn = _setup_adventurer_equipment

# adventurer_unique = Actor(
#     char="@",
#     color=(210, 210, 210),
#     name="Adventurer",

#     ai_cls=Neutral,
#     equipment=Equipment(),
#     fighter=Fighter(hp=32, base_defense=5, strength=4, recover_rate=0, fov=0, weapon_proficiency = (1, 4)),
#     inventory=Inventory(capacity=1, loot_table_key="Adventurer Unique", loot_amount=3),
#     level=Level(xp_given=50),
# )

rat = Actor(
    char="r",
    color=(60,60,90),
    name="Giant rat",
    ai_cls=SleepingEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=6,
        #hp=32,
        base_defense=3,
        strength=0,
        recover_rate=50,
        recover_amount=0,
        fov=4,
        foh=3,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=5,
        stamina=3,
        max_stamina=3,
        action_time_cost=7,
        luck=0,
        woke_ai_cls=HostileEnemyV3,
        natural_weapon=NaturalWeapon(name="Rat claws", min_dmg=1, max_dmg=3),
    ),
    inventory=Inventory(capacity=1, loot_table_key="Giant rat", loot_amount=1),
    level=Level(xp_given=2),
    to_eat_drop=meat,
)

swarm_rat = Actor(
    char="r",
    color=(60,60,90),
    name="Hungry rat",
    ai_cls=random.choice([SleepingEnemy, HostileEnemyV3]),
    equipment=Equipment(),
    fighter=Fighter(
        hp=4,
        base_defense=2,
        strength=0,
        recover_rate=50,
        recover_amount=0,
        fov=6,
        foh=3,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=15,
        stamina=2,
        max_stamina=2,
        action_time_cost=7,
        woke_ai_cls=HostileEnemyV3,
        natural_weapon=NaturalWeapon(name="Rat claws", min_dmg=1, max_dmg=3),
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=1),
)

slime = Actor(
    char="S",
    color=(144, 163, 0),
    #color=(50, 160, 80),
    name="Slime",
    ai_cls=SlimeAI,
    equipment=Equipment(),
    fighter=Fighter(
        hp=9,
        base_defense=0,
        strength=0,
        recover_rate=1,
        recover_amount=4,
        fov=1,
        foh=0,
        weapon_proficiency=PROFICIENCY_LEVELS["Novice"],
        aggressivity=0,
        stamina=1,
        max_stamina=1,
        action_time_cost=30,
        is_slime=True,
        can_split=True,
        slime_generation=0,
        can_pass_closed_doors=False,
        can_open_doors=True,
    ),
    inventory=Inventory(capacity=4),
    level=Level(xp_given=1),
    faction="slime"
)

cave_bat = Actor(
    char="b",
    color=(94, 94, 150),
    name="Cave bat",
    ai_cls=SleepingEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=3,
        base_defense=5,
        strength=0,
        recover_rate=50,
        recover_amount=0,
        fov=0,
        foh=7,
        weapon_proficiency=PROFICIENCY_LEVELS["Beginner"],
        base_stealth=4,
        aggressivity=1,
        stamina=2,
        max_stamina=2,
        action_time_cost=3,
        woke_ai_cls=HostileEnemyV3,
        natural_weapon=NaturalWeapon(name="Needle fangs", min_dmg=0, max_dmg=2),
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=1),
)
cave_bat.is_flying = True
cave_bat.fighter.is_flying = True

# TODO: poisonous_cave_bat
# TODO: vampire_bat

quasit = Actor(
    char="q",
    color=(80, 140, 70),
    name="Quasit",
    ai_cls=SleepingEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        hp=7,
        base_defense=4,
        strength=0,
        recover_rate=50,
        recover_amount=0,
        fov=6,
        foh=6,
        perception=4,
        weapon_proficiency=PROFICIENCY_LEVELS["Novice"],
        base_stealth=4,
        aggressivity=6,
        stamina=4,
        max_stamina=4,
        action_time_cost=6,
        poison_resistance=4,
        woke_ai_cls=HostileEnemyV3,
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Claws", min_dmg=1, max_dmg=3, dmg_bonus=1),
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=4),
)
quasit.is_flying = True
quasit.fighter.is_flying = True

def _randomize_goblin_stats(entity: Actor) -> None:
    entity.fighter.max_hp = random.randint(7, 10)
    entity.fighter.hp = entity.fighter.max_hp
    entity.fighter.base_defense = random.randint(2, 3)
    entity.ai_cls = random.choice([SleepingEnemy, HostileEnemyV3, ScoutV3])
    entity.fighter.woke_ai_cls = HostileEnemyV3
    # etc.

def _goblin_on_spawn(entity: Actor) -> None:
    """Configure goblins when they spawn so the engine can pickle the factory."""
    _setup_creature_equipment(entity)
    _randomize_goblin_stats(entity)

goblin = Actor(
    char="g",
    color=(60,89,33),
    name="Goblin",
    #ai_cls=random.choice([SleepingEnemy, HostileEnemyV3, ScoutV3]),
    ai_cls=SleepingEnemy,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=8,
        base_defense=2,
        base_to_hit=0,
        strength=0,
        recover_rate=50,
        recover_amount=1,
        fov=5,
        foh=6,
        perception=3,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=4,
        stamina=random.randint(2,4),
        max_stamina=3,
        poison_resistance=6,
        action_time_cost=7,
        woke_ai_cls=HostileEnemyV3,
        #woke_ai_cls=random.choice([HostileEnemyV3, ScoutV3]),
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Goblin claws", min_dmg=1, max_dmg=4, dmg_bonus=0),
    ),
    #inventory=Inventory(capacity=1, items=loot_tables.build_monster_inventory("Goblin", 1)),
    #inventory=Inventory(capacity=3, items=loot_tables.build_monster_inventory("Goblin", 3)),
    #inventory=Inventory(capacity=1, items=[dagger]),
    inventory=Inventory(capacity=3, loot_table_key="Goblin", loot_amount=2),
    level=Level(xp_given=3),
)
#goblin.on_spawn = _setup_creature_equipment
goblin.on_spawn = _goblin_on_spawn


def _randomize_grey_goblin_stats(entity: Actor) -> None:
    entity.fighter.max_hp = random.randint(8, 10)
    entity.fighter.hp = entity.fighter.max_hp
    entity.fighter.base_defense = random.randint(3, 4)
    entity.ai_cls = random.choice([SleepingEnemy, HostileEnemyV3, ScoutV3])
    entity.fighter.woke_ai_cls = HostileEnemyV3
    # etc.

def _grey_goblin_on_spawn(entity: Actor) -> None:
    """Configure grey goblins when they spawn so the engine can pickle the factory."""
    _setup_creature_equipment(entity)
    _randomize_grey_goblin_stats(entity)

grey_goblin = Actor(
    char="g",
    color=(95,117,91),
    name="Grey goblin",
    ai_cls=random.choice([SleepingEnemy, HostileEnemyV2, ScoutV3]),
    #ai_cls=HostileEnemyV3,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=8,
        base_defense=3,
        base_to_hit=1,
        strength=1,
        recover_rate=50,
        recover_amount=1,
        fov=6,
        foh=7,
        perception=4,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=7,
        max_stamina=3,
        poison_resistance=6,
        action_time_cost=7,
        #woke_ai_cls=HostileEnemyV2,
        woke_ai_cls=HostileEnemyV3,
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Goblin claws", min_dmg=1, max_dmg=4, dmg_bonus=1),
    ),
    inventory=Inventory(capacity=3, loot_table_key="Grey goblin", loot_amount=1),
    level=Level(xp_given=3),
)
grey_goblin.on_spawn = _grey_goblin_on_spawn

monkey = Actor(
    char="y",
    color=(110,4,4),
    name="Monkey",
    #ai_cls=random.choice([SleepingEnemy, Scout]),
    ai_cls=HostileEnemyV3,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=8, 
        base_defense=3, 
        strength=0, 
        recover_rate=50,
        recover_amount=1,
        fov=3,
        foh=6, 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=2, 
        stamina=5, 
        max_stamina=5,
        action_time_cost=6,
        #woke_ai_cls=HostileEnemy,
        woke_ai_cls=HostileEnemyV3,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
    ),
    inventory=Inventory(capacity=1, loot_table_key="Monkey", loot_amount=1),
    level=Level(xp_given=3),
)
monkey.on_spawn = _setup_creature_equipment

orc = Actor(
    char="o",
    color=(63, 127, 63),
    name="Orc",
    ai_cls=random.choice([SleepingEnemy, HostileEnemyV3, ScoutV3]),
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=12, 
        base_defense=3, 
        base_to_hit=1,
        strength=2, 
        recover_rate=50,
        recover_amount=0,
        fov=5,
        foh=4,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=8, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
        woke_ai_cls=HostileEnemyV3,
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
    ),
    inventory=Inventory(capacity=3, loot_table_key="Orc", loot_amount=4),
    level=Level(xp_given=5),
)
orc.on_spawn = _setup_creature_equipment

orc_servant = Actor(
    char="o",
    color=(205, 251, 43),
    name="Orc servant",
    ai_cls=random.choice([SleepingEnemy, HostileEnemyV3]),
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=12, 
        base_defense=3, 
        base_to_hit=1,
        strength=1, 
        recover_rate=50,
        recover_amount=0,
        fov=5,
        foh=5,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=2, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
        woke_ai_cls=HostileEnemyV3,
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=0)
    ),
    inventory=Inventory(capacity=3, loot_table_key="Orc servant", loot_amount=4),
    level=Level(xp_given=5),
)
orc_servant.on_spawn = _setup_creature_equipment

true_orc = Actor(
    char="o",
    color=(63, 220, 63),
    name="True Orc",
    ai_cls=random.choice([SleepingEnemy, HostileEnemyV3]),
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=32, 
        base_defense=3, 
        strength=3, 
        recover_rate=50,
        recover_amount=0,
        fov=5,
        foh=4,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=15, 
        base_to_hit=1, 
        stamina=4, 
        max_stamina=4,
        woke_ai_cls=HostileEnemyV3,
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Fist", min_dmg=1, max_dmg=2, dmg_bonus=1)
        ),
    inventory=Inventory(capacity=3, loot_table_key="True Orc", loot_amount=4),
    level=Level(xp_given=10),
)
true_orc.on_spawn = _setup_creature_equipment

skeleton = Actor(
    char="k",
    color=(180, 180, 180),
    name="Skeleton",
    ai_cls=HostileEnemyV3,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=16,
        base_defense=4,
        base_to_hit=1,
        base_armor_value=2,
        strength=1,
        recover_rate=50,
        recover_amount=0,
        fov=4,
        foh=1,
        perception=2,
        weapon_proficiency=PROFICIENCY_LEVELS["Apprentice"],
        aggressivity=5,
        stamina=8,
        max_stamina=8,
        action_time_cost=12,
        natural_weapon=NaturalWeapon(name="Bone blade", min_dmg=1, max_dmg=5),
    ),
    inventory=Inventory(capacity=2, loot_table_key="Skeleton", loot_amount=2),
    level=Level(xp_given=8),
)
skeleton.on_spawn = _setup_creature_equipment

warden = Actor(
    char="W",
    color=(92, 110, 168),
    name="Warden",
    ai_cls=WardenAI,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=22,
        base_defense=5,
        base_to_hit=2,
        base_armor_value=2,
        strength=3,
        recover_rate=45,
        recover_amount=1,
        fov=7,
        foh=5,
        perception=5,
        weapon_proficiency=PROFICIENCY_LEVELS["Apprentice"],
        aggressivity=9,
        stamina=4,
        max_stamina=4,
        action_time_cost=9,
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Steel fist", min_dmg=1, max_dmg=3, dmg_bonus=1),
    ),
    inventory=Inventory(capacity=4, loot_table_key="Warden", loot_amount=2),
    level=Level(xp_given=12),
)
warden.on_spawn = _setup_creature_equipment

troll = Actor(
    char="T",
    color=(0, 127, 0),
    name="Troll",
    ai_cls=HostileEnemyV3,
    equipment=Equipment(),
    fighter=Fighter(
        hp=38, 
        base_defense=2, 
        base_armor_value=5,
        strength=4, 
        recover_rate=50,
        recover_amount=5,
        fov=1,
        foh=2,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=8,
        action_time_cost=14, 
        stamina=2, 
        max_stamina=2,
        can_open_doors=True,
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
    ai_cls=HostileEnemyV3,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=32, 
        base_defense=3, 
        strength=4, 
        recover_rate=50,
        recover_amount=12, 
        fov=6,
        foh=8,
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
        recover_rate=50,
        recover_amount=0, 
        fov=1, 
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"],
        aggressivity=1, 
        stamina=5, 
        max_stamina=5,
        woke_ai_cls=SneakeEnemy,
        poisons_on_hit=True,
        poisonous=8,
        natural_weapon=NaturalWeapon(name="Bite", min_dmg=0, max_dmg=0, dmg_bonus=0)
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
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=32, 
        base_defense=5, 
        strength=2, 
        recover_rate=50,
        recover_amount=1, 
        fov=8,
        foh=6,
        perception=4,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        base_stealth=3, 
        base_to_hit=2,
        can_open_doors=True,
        natural_weapon=NaturalWeapon(name="Cheater fist", min_dmg=1, max_dmg=2, dmg_bonus=1)
    ),
    inventory=Inventory(capacity=5, loot_table_key="Bandit", loot_amount=5),
    level=Level(xp_given=14),
)
bandit.on_spawn = _setup_creature_equipment

cultist = Actor(
    char="c",
    color=(160, 0, 160),
    name="Cultist",
    ai_cls=HostileEnemyPlus,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=18,
        base_defense=3,
        base_to_hit=1,
        strength=2,
        recover_rate=50,
        recover_amount=1,
        fov=9,
        weapon_proficiency=PROFICIENCY_LEVELS["Apprentice"],
        base_stealth=2,
        aggressivity=8,
        stamina=4,
        max_stamina=4,
        action_time_cost=7,
        natural_weapon=NaturalWeapon(name="Ceremonial dagger", min_dmg=1, max_dmg=4, dmg_bonus=1),
    ),
    inventory=Inventory(capacity=3, loot_table_key="Cultist", loot_amount=2),
    level=Level(xp_given=12),
)
cultist.on_spawn = _setup_creature_equipment

sentinel = Actor(
    char="&",
    color=(180,80,110),
    name="Sentinel",
    ai_cls=SentinelEnemy,
    equipment=Equipment(has_head_slot=True, has_cloak_slot=True),
    fighter=Fighter(
        hp=24, 
        base_defense=1, 
        strength=1, 
        recover_rate=50,
        recover_amount=6, 
        fov=0,
        weapon_proficiency = PROFICIENCY_LEVELS["Novice"], 
        aggressivity=0, 
        stamina=3, 
        max_stamina=3,
        action_time_cost=10,
    ),
    inventory=Inventory(capacity=1, loot_table_key="Sentinel", loot_amount=2),
    level=Level(xp_given=2),
    to_eat_drop=meat,
)
sentinel.on_spawn = _setup_creature_equipment

def monster_roulette(choices=[orc, goblin, snake]):

    max_choices = len(choices)
    winner = random.randint(0,max_choices - 1)
    for i in range(0, max_choices):
        if i == winner:
            return choices[i]
