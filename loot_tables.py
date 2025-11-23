from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from entity import Item

# SISTEMA DE DROPS
# - Cada criatura define su inventario inicial mediante MONSTER_LOOT_TABLES.
# - Si su inventario tiene capacidad > 0, al morir deja caer todos los
#   objetos que transportaba.
# - Pero CUIDADO!! Algunas criaturas tienen el contenido de su inventario
#   definido de la siguiente forma: inventory=Inventory(capacity=20, 
#   items=loot_tables.build_monster_inventory("Adventurer", amount=3)). Ahí
#   se establece que los ítems de su inventario van a ser escogidos por
#   la función build_monster_inventory(). Esto quiere decir que no necesariamente
#   se dropearan todos los intems definidos en el MONSTER_LOOT_TABLES para
#   esa criatura. Pero es fácil hacer que se dropeen todos:
#   loot_tables.build_monster_inventory escoge aleatoriamente objetos de la lista 
#   MONSTER_LOOT_TABLES pero sin duplicados. Ahora bien, si el "amount" (atributo
#   del build_monster_inventory establecido en su Inventory) excede el número de opciones disponibles simplemente devuelve 
#   todas las opciones en un orden aleatorio.
# - Si se quiere estableces su inventario manualmente, se puede hacer así:
#   inventory=Inventory(capacity=2, items=[short_sword, leather_armor])
# - Además, puede tener configurado un “drop especial” independiente:
#   SPECIAL_DROP_TABLES define la probabilidad total de que ocurra y la
#   batería de objetos candidatos (con pesos individuales). Si el lanzamiento
#   acierta, se instancia uno de esos objetos y se suma al botín.


# Mapping between creature names and the loot keys they can roll from.
# Sólo para las criaturas que usan build_monster_inventory().
MONSTER_LOOT_TABLES: Dict[str, Sequence[str]] = {
    "Adventurer": ("short_sword", "leather_armor", "stamina_potion"),
    "Giant rat": ("meat",),
    "Monkey": ("banana", "dagger", "strength_potion", "increase_max_stamina", "life_potion", "infra_vision_potion", "antidote", "health_potion", "poison_potion", "power_potion", "stamina_potion", "temporal_infra_vision_potion", "blindness_potion","confusion_potion", "paralysis_potion", "petrification_potion", "precission_potion"),
    "Goblin": ("meat", "dagger"),
    "Orc": ("short_sword", "power_potion", "leather_armor", "poison_potion"),
    "True Orc": ("long_sword", "spear", "short_sword", "leather_armor", "chain_mail"),
    "Bandit": ("short_sword", "precission_potion", "stamina_potion", "poison_potion", "dagger"),
    "Sentinel": (),
    "Cave bat": (),
    "Skeleton": ("short_sword", "leather_armor", "health_potion"),
    "Cultist": ("dagger", "poison_potion", "confusion_scroll"),
}

# Configurable tables for special drops outside the creature inventory.
# chance: probability (0-1) of rolling a special drop.
# items: sequence of (item_key, weight) entries used when the chance succeeds.
# NOTA: El peso del (item_key, weight) es un peso relativo, no una probabilidad 
# absoluta.
# Ejemplo: en ("health_potion", 1) el 1 indica “un peso”. Si la tabla tiene 
# ("health_potion", 1) y ("power_potion", 3), entonces, cuando toque drop especial, 
# health_potion saldrá 1 de cada 4 veces y power_potion 3 de cada 4 
# (porque 1/(1+3) y 3/(1+3)).
SPECIAL_DROP_TABLES: Dict[str, Dict[str, object]] = {
    "Adventurer": {
        "chance": 0.75,
        "items": (
            ("triple_ration", 3),
            ("antidote", 3),
            ("health_potion", 3),
            ("power_potion", 3),
            ("temporal_infra_vision_potion", 3),
            ("confusion_scroll", 3), 
            ("confusion_potion", 3),
            ("poison_potion", 3),
            ("temporal_infra_vision_potion", 3),
            ("blindness_potion", 3), 
            ("poison_potion", 3),
            ("increase_max_stamina", 1),
            ("strength_potion", 1),
            ("life_potion", 1),
            ("infra_vision_potion", 1),
        ),
    },
    "Giant rat": {
        "chance": 0.15,
        "items": (
            ("triple_ration", 1),
        ),
    },
    "Goblin": {
        "chance": 0.20,
        "items": (
            ("sand_bag", 1),
            ("poison_potion", 1),
            ("health_potion", 1),
        ),
    },
    "Orc": {
        "chance": 0.15,
        "items": (
            # ("chain_mail", 1),
            ("spear", 1),
            ("power_potion", 1),
            ("health_potion", 1),
            ("confusion_scroll", 1), 
            ("poison_potion", 1),
        ),
    },
    "True Orc": {
        "chance": 0.15,
        "items": (
            ("short_sword_plus", 2),
            # ("chain_mail", 1),
            ("dagger_plus", 2),
        ),
    },
    "Bandit": {
        "chance": 0.25,
        "items": (
            ("spear_plus", 1),
            ("dagger_plus", 1),
        ),
    },
}

DEFAULT_FALLBACK_ITEM_KEY = "meat"

_ITEM_REGISTRY: Dict[str, Item] = {}
_fallback_item: Optional[Item] = None


def register_loot_item(key: str, item: Item, *, fallback: Optional[bool] = None) -> None:
    """Register an item prototype that can be referenced by loot tables."""
    global _fallback_item
    _ITEM_REGISTRY[key] = item
    should_set_fallback = fallback
    if should_set_fallback is None:
        should_set_fallback = key == DEFAULT_FALLBACK_ITEM_KEY
    if should_set_fallback:
        _fallback_item = item


def register_loot_items(mapping: Mapping[str, Item], *, fallback_key: Optional[str] = None) -> None:
    """Register multiple loot items at once."""
    for key, item in mapping.items():
        register_loot_item(key, item, fallback=(fallback_key == key if fallback_key else None))


def build_monster_inventory(monster_type: str, amount: int) -> List[Item]:
    """Return a randomized list of items for the requested creature."""
    if amount <= 0:
        return []
    keys = MONSTER_LOOT_TABLES.get(monster_type)
    if not keys:
        return []
    seen_keys = set()
    available_items = []
    for key in keys:
        if key in seen_keys:
            continue
        item = _ITEM_REGISTRY.get(key)
        if item:
            available_items.append(item)
            seen_keys.add(key)
    if not available_items:
        return []
    picks = min(amount, len(available_items))
    if picks <= 0:
        return []
    return random.sample(available_items, picks)


def roll_special_drop(monster_type: str) -> Optional[Item]:
    """Return an optional extra loot item configured for the given creature."""
    config = SPECIAL_DROP_TABLES.get(monster_type)
    if not config:
        return None
    chance = float(config.get("chance", 0))
    chance = max(0.0, min(1.0, chance))
    if chance <= 0 or random.random() > chance:
        return None
    entries: Sequence[Tuple[str, float]] = config.get("items", ())
    weighted_entries = [
        (key, float(weight))
        for key, weight in entries
        if weight > 0 and _ITEM_REGISTRY.get(key)
    ]
    if not weighted_entries:
        return None
    total_weight = sum(weight for _, weight in weighted_entries)
    if total_weight <= 0:
        return None
    pick = random.uniform(0, total_weight)
    cumulative = 0.0
    for key, weight in weighted_entries:
        cumulative += weight
        if pick <= cumulative:
            return _ITEM_REGISTRY[key]
    return None
