from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from collections.abc import Callable

from textual.reactive import var
from textual.widgets import Input
from textual.message import Message
from textual.binding import Binding

# TODO: add a limit for the command log. This limit must be from global settings.


class CommandLine(Input):
    BINDINGS = [
        Binding('ctrl+up', 'history("up")', 'Prev command', show=False),
        Binding('ctrl+down', 'history("down")', 'Next command', show=False),
        Binding('tab', 'complete', 'Auto complete', show=False, priority=True),
    ]

    command_log: var[list[str]] = var([])
    command_log_cursor = var(0)

    @dataclass
    class NewCommand(Message):
        command: str

    @dataclass
    class LineChanged(Message):
        current_value: str

    def __init__(self, placeholder: str, id: str, autocomplete_cb: Callable[[str], tuple[int, str]]) -> None:
        self.autocomplete_cb = autocomplete_cb
        super().__init__(placeholder=placeholder, id=id)

    # EVENTS

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value:
            return

        if event.value not in self.command_log:
            self.command_log.append(event.value)
            self.command_log_cursor = len(self.command_log) - 1
        self.post_message(CommandLine.NewCommand(event.value))
        self.value = ''

    def on_input_changed(self, event: Input.Changed) -> None:
        result = 'go |'

        if event.value:
            result = event.value
            if result.endswith(' '):
                result += '|'

        self.post_message(CommandLine.LineChanged(result))

    # ACTIONS

    def action_history(self, direction: Literal['up', 'down']) -> None:
        if not self.command_log:
            return

        if direction == 'down':
            forecast = self.command_log_cursor - 1
            if forecast < 0:
                forecast = len(self.command_log) - 1
            self.value = self.command_log[forecast]
            self.command_log_cursor = forecast
        else:
            forecast = self.command_log_cursor + 1
            if forecast > len(self.command_log) - 1:
                forecast = 0
            self.value = self.command_log[forecast]
            self.command_log_cursor = forecast

    def action_complete(self) -> None:
        if not self.value:
            return

        if self.cursor_position != len(self.value):
            return

        count, repl = self.autocomplete_cb(self.value)
        if repl != self.value:
            if not repl.endswith(' ') and count == 1:
                repl += ' '
            self.value = repl
            self.cursor_position = len(self.value)
