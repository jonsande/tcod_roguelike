from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from settings import PLAYER_LEVELING_ENABLED

if TYPE_CHECKING:
    from entity import Actor


class Level(BaseComponent):
    parent: Actor

    # Con un valor level_up_factor de '10', el primer nivel cuesta 30pt (level_up_base + 10), 
    # el segundo 40pts (level_up_base + 10x2), el tercero 20+(10x3)=50pts, etc.

    def __init__(
        self,
        current_level: int = 1,
        current_xp: int = 0,
        level_up_base: int = 0,
        #level_up_factor: int = 150
        level_up_factor: int = 10,
        xp_given: int = 0,
    ):
        self.current_level = current_level
        self.current_xp = current_xp
        self.level_up_base = level_up_base
        self.level_up_factor = level_up_factor
        self.xp_given = xp_given

    @property
    def experience_to_next_level(self) -> int:
        x = self.current_level ** 2
        y = self.level_up_factor
        return self.level_up_base + (x * y)

    def _leveling_disabled_for_player(self) -> bool:
        if PLAYER_LEVELING_ENABLED:
            return False

        engine_player = getattr(self.engine, "player", None)
        return engine_player is not None and self.parent is engine_player

    @property
    def requires_level_up(self) -> bool:
        if self._leveling_disabled_for_player():
            return False
        return self.current_xp > self.experience_to_next_level

    def add_xp(self, xp: int) -> None:
        if xp == 0 or self.level_up_base == 0:
            return

        self.current_xp += xp

        # Evita mostrar mensajes de experiencia mientras el leveling del jugador esté desactivado.
        if self._leveling_disabled_for_player():
            return

        self.engine.message_log.add_message(f"You gain {xp} experience points.")

        if self.requires_level_up:
            self.engine.message_log.add_message(
                f"You advance to level {self.current_level + 1}!"
            )

    def increase_level(self) -> None:
        if self._leveling_disabled_for_player():
            return

        self.current_xp -= self.experience_to_next_level

        self.current_level += 1

    def increase_stealth(self, amount: int = 1) -> None:
        self.parent.fighter.base_stealth += amount

        self.engine.message_log.add_message("Your stealth improves!")

        self.increase_level()

    def increase_to_hit(self, amount: int = 1) -> None:
        self.parent.fighter.base_to_hit += amount

        self.engine.message_log.add_message("Your chance to hit improves!")

        self.increase_level()

    def increase_defense(self, amount: int = 1) -> None:
        self.parent.fighter.base_defense += amount

        self.engine.message_log.add_message("Your movements are getting swifter!")

        self.increase_level()

    def increase_stamina(self, amount: int = 1) -> None:
        self.parent.fighter.max_stamina += amount

        self.engine.message_log.add_message("Your stamina improves!")

        self.increase_level()


    # UNUSED
    
    def increase_max_hp(self, amount: int = 20) -> None:
        self.parent.fighter.max_hp += amount
        self.parent.fighter.hp += amount

        self.engine.message_log.add_message("Your health improves!")

        self.increase_level()

    def increase_power(self, amount: int = 1) -> None:
        self.parent.fighter.base_power += amount

        self.engine.message_log.add_message("You feel stronger!")

        self.increase_level()

    
