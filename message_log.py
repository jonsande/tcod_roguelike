import re
import textwrap
from typing import Dict, Iterable, List, Optional, Reversible, Tuple

import tcod

import color
import settings


class Message:
    def __init__(self, text: str, fg: Tuple[int, int, int]):
        self.plain_text = text
        self.fg = fg
        self.count = 1

    @property
    def full_text(self) -> str:
        """The full text of this message, including the count if necessary."""
        if self.count > 1:
            return f"{self.plain_text} (x{self.count})"
        return self.plain_text


class MessageLog:
    def __init__(self) -> None:
        self.messages: List[Message] = []

    def add_message(
        self, text: str, fg: Tuple[int, int, int] = color.white, *, stack: bool = True,
    ) -> None:
        """Add a message to this log.
        `text` is the message text, `fg` is the text color.
        If `stack` is True then the message can stack with a previous message
        of the same text.
        """
        if stack and self.messages and text == self.messages[-1].plain_text:
            self.messages[-1].count += 1
            message = self.messages[-1]
        else:
            message = Message(text, fg)
            self.messages.append(message)

        if getattr(settings, "LOG_ECHO_TO_STDOUT", False):
            try:
                print(message.full_text)
            except Exception:
                # No bloquees el juego si stdout falla por alguna razón.
                pass

    def render(
        #self, console: tcod.Console, x: int, y: int, width: int, height: int,   # DEPRECATED
        self,
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        name_colors: Optional[Dict[str, Tuple[int, int, int]]] = None,
    ) -> None:
        """Render this log over the given area.
        `x`, `y`, `width`, `height` is the rectangular region to render onto
        the `console`.
        """
        self.render_messages(
            console,
            x,
            y,
            width,
            height,
            self.messages,
            name_colors=name_colors or {},
        )

    @staticmethod
    def wrap(string: str, width: int) -> Iterable[str]:
        """Return a wrapped text message."""
        for line in string.splitlines():  # Handle newlines in messages.
            yield from textwrap.wrap(
                line, width, expand_tabs=True,
            )

    @classmethod       
    def render_messages(
        cls,
        #console: tcod.Console,  # DEPRECATED
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        height: int,
        messages: Reversible[Message],
        *,
        name_colors: Dict[str, Tuple[int, int, int]],
    ) -> None:
        """Render the messages provided.
        The `messages` are rendered starting at the last message and working
        backwards.
        """
        y_offset = height - 1

        for message in reversed(messages):
            for line in reversed(list(cls.wrap(message.full_text, width))):
                cls._print_with_highlights(
                    console=console,
                    x=x,
                    y=y + y_offset,
                    line=line,
                    base_color=message.fg,
                    name_colors=name_colors,
                )
                y_offset -= 1
                if y_offset < 0:
                    return  # No more space to print messages.

    @staticmethod
    def _print_with_highlights(
        console: tcod.console.Console,
        x: int,
        y: int,
        line: str,
        base_color: Tuple[int, int, int],
        name_colors: Dict[str, Tuple[int, int, int]],
    ) -> None:
        """
        Print a line, applying per-name colors when those names appear.
        """
        if not name_colors:
            console.print(x=x, y=y, string=line, fg=base_color)
            return

        # Collect non-overlapping highlight spans ordered by appearance.
        spans: list[tuple[int, int, Tuple[int, int, int]]] = []
        for name, fg in name_colors.items():
            if not name:
                continue
            # Use word boundaries to avoid partial matches inside other words.
            pattern = rf"\b{re.escape(name)}\b"
            for match in re.finditer(pattern, line):
                spans.append((match.start(), match.end(), fg))

        if not spans:
            console.print(x=x, y=y, string=line, fg=base_color)
            return

        spans.sort(key=lambda span: (span[0], -(span[1] - span[0])))

        cursor = x
        consumed = 0
        for start, end, fg in spans:
            if start < consumed:
                continue  # Skip overlaps, earlier/longer match already handled.
            if start > consumed:
                segment = line[consumed:start]
                console.print(x=cursor, y=y, string=segment, fg=base_color)
                cursor += len(segment)
            segment = line[start:end]
            console.print(x=cursor, y=y, string=segment, fg=fg)
            cursor += len(segment)
            consumed = end

        if consumed < len(line):
            console.print(x=cursor, y=y, string=line[consumed:], fg=base_color)
