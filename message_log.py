import re
import textwrap
from typing import Dict, Iterable, List, Optional, Reversible, Tuple

import tcod

import color
import settings


class Message:
    def __init__(
        self,
        text: str,
        fg: Tuple[int, int, int],
        *,
        prefix: str = "",
        prefix_fg: Optional[Tuple[int, int, int]] = None,
        prefix_colors: Optional[List[Tuple[int, int, int]]] = None,
    ):
        self.plain_text = text
        self.fg = fg
        self.prefix = prefix
        self.prefix_fg = prefix_fg
        self.prefix_colors = prefix_colors
        self.count = 1

    @property
    def full_text(self) -> str:
        """The full text of this message, including the count if necessary."""
        text = self.plain_text
        if self.count > 1:
            text = f"{text} (x{self.count})"
        if self.prefix:
            return f"{self.prefix} {text}"
        return text


class MessageLog:
    def __init__(self) -> None:
        self.messages: List[Message] = []
        self._turn_marker_pending = False
        self._turn_marker_text = "[*]"
        self._turn_marker_color = color.turn_marker

    def mark_turn_start(self) -> None:
        """Arm the next log message with a turn-start marker."""
        self._turn_marker_pending = True

    def add_message(
        self, text: str, fg: Tuple[int, int, int] = color.white, *, stack: bool = True,
    ) -> None:
        """Add a message to this log.
        `text` is the message text, `fg` is the text color.
        If `stack` is True then the message can stack with a previous message
        of the same text.
        """
        pending_marker = self._turn_marker_pending
        if pending_marker:
            stack = False

        if stack and self.messages and text == self.messages[-1].plain_text:
            self.messages[-1].count += 1
            message = self.messages[-1]
        else:
            message = Message(
                text,
                fg,
                prefix=self._turn_marker_text if pending_marker else "",
                prefix_colors=(
                    [color.white, self._turn_marker_color, color.white]
                    if pending_marker
                    else None
                ),
            )
            self.messages.append(message)

        if pending_marker:
            self._turn_marker_pending = False

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
                if message.prefix and line.startswith(message.prefix):
                    cursor = x
                    prefix = message.prefix
                    prefix_colors = message.prefix_colors
                    if prefix_colors and len(prefix_colors) == len(prefix):
                        segment_start = 0
                        current_color = prefix_colors[0]
                        for i, fg in enumerate(prefix_colors[1:], start=1):
                            if fg != current_color:
                                console.print(
                                    x=cursor,
                                    y=y + y_offset,
                                    string=prefix[segment_start:i],
                                    fg=current_color,
                                )
                                cursor += i - segment_start
                                segment_start = i
                                current_color = fg
                        console.print(
                            x=cursor,
                            y=y + y_offset,
                            string=prefix[segment_start:],
                            fg=current_color,
                        )
                        cursor += len(prefix) - segment_start
                    else:
                        console.print(
                            x=cursor,
                            y=y + y_offset,
                            string=prefix,
                            fg=message.prefix_fg or message.fg,
                        )
                        cursor += len(prefix)

                    remaining = line[len(prefix):]
                    if remaining.startswith(" "):
                        console.print(
                            x=cursor,
                            y=y + y_offset,
                            string=" ",
                            fg=message.fg,
                        )
                        cursor += 1
                        remaining = remaining[1:]
                    if remaining:
                        cls._print_with_highlights(
                            console=console,
                            x=cursor,
                            y=y + y_offset,
                            line=remaining,
                            base_color=message.fg,
                            name_colors=name_colors,
                        )
                else:
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
