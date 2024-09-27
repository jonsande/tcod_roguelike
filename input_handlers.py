# Aquí definimos los tipos de eventos asociados a pulsación de teclas ?¿

from __future__ import annotations
from tcod import libtcodpy
import os
from typing import Callable, Optional, Tuple, TYPE_CHECKING
from typing import Callable, Optional, Tuple, TYPE_CHECKING, Union

import tcod
import tcod.event
import actions
from actions import (
    Action,
    BumpAction,
    PickupAction,
    WaitAction,
    ToogleLightAction
)
import color
import exceptions

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item

MOVE_KEYS = {
    # Arrow keys.
    #tcod.event.K_UP: (0, -1),
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
    tcod.event.KeySym.HOME: (-1, -1),
    tcod.event.KeySym.END: (-1, 1),
    tcod.event.KeySym.PAGEUP: (1, -1),
    tcod.event.KeySym.PAGEDOWN: (1, 1),
    # Numpad keys.
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_3: (1, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_9: (1, -1),
    # Vi keys.
    tcod.event.KeySym.h: (-1, 0),
    tcod.event.KeySym.j: (0, 1),
    tcod.event.KeySym.k: (0, -1),
    tcod.event.KeySym.l: (1, 0),
    tcod.event.KeySym.y: (-1, -1),
    tcod.event.KeySym.u: (1, -1),
    tcod.event.KeySym.b: (-1, 1),
    tcod.event.KeySym.n: (1, 1),
}

WAIT_KEYS = {
    tcod.event.KeySym.PERIOD,
    tcod.event.KeySym.KP_5,
    tcod.event.KeySym.CLEAR,
}

CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
}


ActionOrHandler = Union[Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler.
"""

# Variables globales:

# Contador para la mecánica de autoheal (en EventHandler)
counter = 0
satiety_counter = 0

# Contadores para mecánica de efectos temporales:
effect_timer = 0
amount_affected = 0
number_of_turns = None


class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, console: tcod.Console) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()


class PopupMessage(BaseEventHandler):
    """Display a popup text window."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def on_render(self, console: tcod.Console) -> None:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        console.tiles_rgb["fg"] //= 8
        console.tiles_rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=tcod.CENTER,
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent


class EventHandler(BaseEventHandler):

    """We’re creating a class called EventHandler, which is a subclass 
    of tcod’s EventDispatch class. EventDispatch is a class that 
    allows us to send an event to its proper method based on what 
    type of event it is. Let’s take a look at the methods we’re 
    creating for EventHandler to see a few examples of this."""

    def __init__(self, engine: Engine):
        self.engine = engine

    #def handle_events(self, event: tcod.event.Event) -> None:
    #    self.handle_action(self.dispatch(event))

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            # A valid action was performed.
            if not self.engine.player.is_alive:
                # The player was killed sometime during or after the action.
                return GameOverEventHandler(self.engine)
            elif self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)
            return MainGameEventHandler(self.engine)  # Return to the main handler.
        return self

    # Para lo que interesa esto es lo que mueve el turno:
    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.

        Returns True if the action will advance a turn.
        """        

        if action is None:
            return False

        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False  # Skip enemy turn on exceptions.
        
        self.engine.extra_turn_manager()

        # Move THE CLOCK
        self.engine.clock()

        self.engine.restore_time_pts()

        # ¿What time is it?
        now = self.engine.what_time_it_is()
        print(f"\n{color.bcolors.BOLD}{color.bcolors.WARNING}=============== Turn: {now} ==============={color.bcolors.ENDC}\n")

        self.engine.handle_enemy_turns()

        self.engine.update_fov()

        # Autoheal, Hunger, Poison
        self.engine.autohealmonsters()
        self.engine.update_hunger()
        self.engine.update_poison()

        # Fortify indicator
        #self.engine.update_fortify_indicator()

        # Melee indicator
        self.engine.update_melee_indicator()

        # Actualizamos efectos temporales
        self.engine.update_temporal_effects()

        # Restore Energy Points for all actors (Speed System)
        #self.engine.restore_energy_all()

        return True
    

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.tile.x, event.tile.y):
            self.engine.mouse_location = event.tile.x, event.tile.y

    #def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
    #    raise SystemExit()
    
    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)


class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.KeySym.LSHIFT,
            tcod.event.KeySym.RSHIFT,
            tcod.event.KeySym.LCTRL,
            tcod.event.KeySym.RCTRL,
            tcod.event.KeySym.LALT,
            tcod.event.KeySym.RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.

        By default this returns to the main event handler.
        """
        return MainGameEventHandler(self.engine)


class CombatControlHandler(AskUserEventHandler):
    TITLE = "COMBAT CONTROL PANEL"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        
        if self.engine.player.x <= 40:
            x = 44
        else:
            x = 0

        y = 0

        width = 36

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=36,
            title=self.TITLE,
            # Para que el fondo sea transparente o no:
            clear=True,
            fg=(99,238,99),
            bg=(2,45,0),
        )

        #console.print(
        #    x=2, y=2, string="LEVEL:", fg=(99,238,99)
        #)

        monsters_list = []

        for i in self.engine.game_map.actors:
            if self.engine.game_map.visible[i.x, i.y] and i != self.engine.player:               
                monsters_list.append(i)
    
        sorted_monsters_list = sorted(monsters_list, key=lambda e: self.engine.player.distance(e.x, e.y))

        #number_of_monsters = len(monsters_list)
        #print(number_of_monsters)

        counter_mons = 0
        counter_lines = 0
        for i, e in enumerate(sorted_monsters_list):
            counter_mons += 1
            name = e.name.upper()
            distance = int(self.engine.player.distance(e.x, e.y))
            stamina = f"{e.fighter.stamina}"
            defense = f"{e.fighter.defense}"
            armor_value = f"{e.fighter.armor_value}"
            hp = f"{e.fighter.hp}"
            aggravated = f"{e.fighter.aggravated}"
            power = f"{e.fighter.power}+1D{e.fighter.dmg_mod[1]}"

            console.print(
                x=x+1, 
                y=1+i+counter_mons +counter_lines, 
                string=f"{name} ({distance}) \n SP:  DEF:  DMG:      ToHit:  AV:",
            )

            console.print(x + 5, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.stamina}", fg=color.blue)
            console.print(x + 11, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.defense}", fg=color.orange)
            console.print(x + 17, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.power}+1D{e.fighter.dmg_mod[1]}", fg=color.red)
            console.print(x + 29, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.to_hit}", fg=color.orange)
            console.print(x + 34, y + counter_mons + 2 + i + counter_lines, f"{e.fighter.armor_value}", fg=color.orange)
            counter_lines += 1
            #self.engine.player.fighter.armor_value
            #console.print(x=x+1, y=1+i+2, string=f"ESTAMINA: {e.fighter.stamina}")
  


                    
        #console.print(x=x + 2, y=n+1, string=f"{i.name}", fg=(99,238,99))
        #print(f"{monsters_list}")

        """
        if distance <= 1:
            return MeleeAction(self.entity, dx, dy).perform()

        self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()"""


class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Character Information"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        #if self.engine.player.x <= 30:
        #    x = 40
        #else:
        #    x = 0

        x = 1
        y = 1

        #width = len(self.TITLE) + 35
        width = 78

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=35,
            title=self.TITLE,
            # Para que el fondo sea transparente o no:
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(
            x=2, y=3, string="LEVEL: ", 
        )
        console.print(
            x=9, y=3, string=f"{self.engine.player.level.current_level}", fg=color.blue,
        )
        console.print(
            x=12, y=3, string="XP: ", 
        )
        console.print(
            x=16, y=3, string=f"{self.engine.player.level.current_xp}", fg=color.blue,
        )
        console.print(
            x=20,
            y=3,
            string="XP for next Level: ", 
        )
        console.print(
            x=39,
            y=3,
            string=f"{self.engine.player.level.experience_to_next_level}", fg=color.blue,
        )
        console.print(
            x=2, 
            y=5, 
            string="HIT CHANCE: ",
        )
        console.print(
            x=14, 
            y=5, 
            string=f"1D6 + ",
        )
        console.print(
            x=20, 
            y=5, 
            string=f"{self.engine.player.fighter.to_hit}", fg=color.blue
        )
        console.print(
            x=22, 
            y=5, 
            string="(To Hit mod - Armor Value) VS Monster Defense",
        )
        console.print(
            x=2, 
            y=7, 
            string=f"DAMAGE: "
        )
        console.print(
            x=10, 
            y=7, 
            string=f"{self.engine.player.fighter.power} ", fg=color.blue
        )
        console.print(
            x=12, 
            y=7, 
            string=f"(power + weapon dmg) + 1d"
        )
        console.print(
            x=37, 
            y=7, 
            string=f"{self.engine.player.fighter.dmg_mod[1]}", fg=color.blue
        )
        console.print(
            x=38, 
            y=7, 
            string=" (dmg mod) - Monster Armor"
        )
        console.print(
            x=2, 
            y=9, 
            string="DEFENSE (parry): "
        )
        console.print(
            x=19, 
            y=9, 
            string=f"{self.engine.player.fighter.defense}", fg=color.blue
        )
        console.print(
            x=2, 
            y=11, 
            string="STEALTH: "
        )
        console.print(
            x=11, 
            y=11, 
            string=f"{self.engine.player.fighter.stealth}", fg=color.blue,
        )
        console.print(
            x=2, 
            y=13, 
            string="ARMOR VALUE: "
        )
        console.print(
            x=15, 
            y=13, 
            string=f"{self.engine.player.fighter.armor_value}", fg=color.blue,
        )


class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        #if self.engine.player.x <= 30:
        #    x = 40
        #else:
        #    x = 0

        x = 1
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            #width=45,
            width=78,
            height=11,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=1, string="Congratulations! You level up!")
        console.print(x=x + 1, y=2, string="Select an attribute to increase.")

        console.print(
            x=x + 1,
            y=4,
            string=f"a) Base Stealth + 1 (current: {self.engine.player.fighter.stealth})",
        )
        """
        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {self.engine.player.fighter.max_hp})",
        )
        """
        console.print(
            x=x + 1,
            y=5,
            string=f"b) To Hit mod +1 (current {self.engine.player.fighter.to_hit})",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Parry (defense) +1 (current: {self.engine.player.fighter.defense})",
        )
        console.print(
            x=x + 1,
            y=7,
            string=f"d) Max stamina +1 (current: {self.engine.player.fighter.max_stamina})",
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 3:
            if index == 0:
                #player.level.increase_max_hp()
                player.level.increase_stealth()
            elif index == 1:
                player.level.increase_to_hit()
            elif index == 2:
                player.level.increase_defense()
            else:
                player.level.increase_stamina()
                
        else:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)

            return None

        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """
        Don't allow the player to click to exit the menu, like normal.
        """
        return None


class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"

    def on_render(self, console: tcod.Console) -> None:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        #if self.engine.player.x <= 30:
        #    x = 40
        #else:
        #    x = 0

        x = 1
        y = 1

        #width = len(self.TITLE) + 35
        width = 78

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_items_in_inventory > 0:
            
            # Ordenamos el inventario alfabéticamente
            self.engine.player.inventory.items.sort(key=lambda x: x.name)
            # EL SISTEMA DE STACK HAY QUE PROGRAMARLO MÁS O MENOS POR AQUÍ
            # "i" es el índice y "ítem" es el objeto
            for i, item in enumerate(self.engine.player.inventory.items):

                # Esto asigna una tecla a cada entrada
                item_key = chr(ord("a") + i)

                is_equipped = self.engine.player.equipment.item_is_equipped(item)

                item_string = f"({item_key}) {item.name}"

                if is_equipped:
                    item_string = f"{item_string} (E)"
                    
                if item.uses > 1:
                    item_string = f"{item_string} ({item.uses})"

                console.print(x + 1, y + i + 1, item_string)
            
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[Action]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()


class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if item.consumable:
            # Return the action for the selected item.
            return item.consumable.get_action(self.engine.player)
        elif item.equippable:
            return actions.EquipAction(self.engine.player, item)
        else:
            return None

class InventoryExamineHandler(InventoryEventHandler):
    """Handle examine an inventory item."""

    TITLE = "Select an item to examine"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        #return PopupMessage(self, f"{item.info}")
        return PopupMessage(self, f"{item.info}")
        

class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Drop this item."""
        return actions.DropItem(self.engine.player, item)


class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""

    def __init__(self, engine: Engine):
        """Sets the cursor to the player when this handler is constructed."""
        super().__init__(engine)
        player = self.engine.player
        engine.mouse_location = player.x, player.y

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        # Esto renderiza el cursor en la posición indicada
        x, y = self.engine.mouse_location
        console.tiles_rgb["bg"][x, y] = color.white
        console.tiles_rgb["fg"][x, y] = color.black

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1  # Holding modifier keys will speed up key movement.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20

            x, y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Clamp the cursor index to the map size.
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """Left click confirms a selection."""
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""

    def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
        """Return to main handler."""
        return MainGameEventHandler(self.engine)


class ExamineScreenEventHandler(SelectIndexHandler):
    TITLE = "Examine Information"
    
    
#class FireRangedHandler(SelectIndexHandler):
#    TITLE = "Select a target"
        

class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""

    def __init__(
        self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[Action]]
    ):
        super().__init__(engine)

        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))


class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting an area within a given radius. Any entity within the area will be affected."""

    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[Action]],
    ):
        super().__init__(engine)

        self.radius = radius
        self.callback = callback

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)

        x, y = self.engine.mouse_location

        # Draw a rectangle around the targeted area, so the player can see the affected tiles.
        console.draw_frame(
            x=x - self.radius - 1,
            y=y - self.radius - 1,
            width=self.radius ** 2,
            height=self.radius ** 2,
            fg=color.red,
            clear=False,
        )

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))


class MainGameEventHandler(EventHandler):

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:

        """This method will receive key press events, and return either an 
        Action subclass, or None, if no valid key was pressed."""

        # 'action' is the variable that will hold whatever subclass of Action 
        # we end up assigning it to. If no valid key press is found, it will 
        # remain set to None. We’ll return it either way.
        action: Optional[Action]= None

        key = event.sym
        modifier = event.mod

        player = self.engine.player

        # Moverse
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = BumpAction(player, dx, dy)
        # Bajar escaleras
        elif key == tcod.event.KeySym.SPACE:
            return actions.TakeStairsAction(player)
        # Pasar turno
        elif key in WAIT_KEYS:
            action = WaitAction(player)
        # Salir del juego
        elif key == tcod.event.KeySym.ESCAPE:
            raise SystemExit()
        # Ver el historial
        elif key == tcod.event.KeySym.v:
            return HistoryViewer(self.engine)
        # Coger objeto
        elif key == tcod.event.KeySym.g:
            action = PickupAction(player)
        # Activar item del inventario
        elif key == tcod.event.KeySym.a:
            return InventoryActivateHandler(self.engine)
        # Inspeccionar item del inventario
        elif key == tcod.event.KeySym.i:
            return InventoryExamineHandler(self.engine)
        # Soltar objeto
        elif key == tcod.event.KeySym.d:
            return InventoryDropHandler(self.engine)
        # Ver ficha del heroe
        elif key == tcod.event.KeySym.c:
            return CharacterScreenEventHandler(self.engine)
        # Inspeccionar alrededores
        elif key == tcod.event.KeySym.x or key == tcod.event.KeySym.SLASH:
            return LookHandler(self.engine)
        elif key == tcod.event.KeySym.z:
            return ExamineScreenEventHandler(self.engine)
        elif key == tcod.event.KeySym.p:
            return CombatControlHandler(self.engine)
        #elif key == tcod.event.K_f:
        #    return SingleRangedAttackHandler(self.engine)
        elif key == tcod.event.KeySym.o:
            return ToogleLightAction(player)
        # Lanzar item del inventario
        elif key == tcod.event.KeySym.t:
            return None

        return action


class GameOverEventHandler(EventHandler):

    def on_quit(self) -> None:
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuitWithoutSaving()  # Avoid saving a finished game.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.K_ESCAPE:
            self.on_quit()
    

CURSOR_Y_KEYS = {
    # tcod.event.K_UP: -1,
    # tcod.event.K_DOWN: 1,
    # tcod.event.K_PAGEUP: -10,
    # tcod.event.K_PAGEDOWN: 10,
    tcod.event.KeySym.UP: -1,
    tcod.event.KeySym.DOWN: 1,
    tcod.event.KeySym.PAGEUP: -10,
    tcod.event.KeySym.PAGEDOWN: 10,
}


class HistoryViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length - 1

    def on_render(self, console: tcod.console.Console) -> None:
        super().on_render(console)  # Draw the main state as the background.

        log_console = tcod.console.Console(console.width - 6, console.height - 6)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Message history├", alignment=libtcodpy.CENTER
        )

        # Render the message log using the cursor parameter.
        self.engine.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, 3, 3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
        # Fancy conditional movement to make it feel right.
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                # Only move from the top to the bottom when you're on the edge.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                # Same with bottom to top movement.
                self.cursor = 0
            else:
                # Otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0  # Move directly to the top message.
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self.log_length - 1  # Move directly to the last message.
        else:  # Any other key moves back to the main game state.
            return MainGameEventHandler(self.engine)
        return None
        