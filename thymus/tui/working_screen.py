from __future__ import annotations

import sys

from typing import TYPE_CHECKING
from itertools import islice


from textual.screen import Screen
from textual.reactive import var
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
)
from textual.widgets import (
    ListView,
    Input,
    TextLog,
    Static,
)

from ..contexts import JunosContext
from .extended_textlog import ExtendedTextLog
from .extended_input import ExtendedInput


if TYPE_CHECKING:
    from ..contexts import Context

    from textual.app import ComposeResult

    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Iterable
    else:
        from typing import Iterable


class WorkingScreen(Screen):
    BINDINGS = [
        ('ctrl+b', 'toggle_sidebar', 'Toggle sidebar'),
    ]
    filename: var[str] = var('')
    nos_type: var[str] = var('')
    encoding: var[str] = var('')
    context: var['Context | None'] = var(None)
    draw_data: var['Iterable[str]'] = var([])

    def __init__(self, filename: str, nos_type: str, encoding: str, *args, **kwags) -> None:
        super().__init__(*args, **kwags)
        self.filename = filename
        self.nos_type = nos_type
        self.encoding = encoding
        self.pre_process_nos()

    def compose(self) -> 'ComposeResult':
        yield Horizontal(
            Container(
                ListView(id='ws-sections-list'),
                id='ws-left-sidebar'
            ),
            Vertical(
                Container(
                    ExtendedTextLog(id='ws-main-out'),
                    id='ws-main-out-container'
                ),
                Vertical(
                    Static('#', id='ws-path-line'),
                    ExtendedInput(placeholder='>', id='ws-main-in'),
                    id='ws-right-bottom-controls'
                ),
                id='ws-right-field'
            )
        )
        yield Static(f'Current filename: {self.filename}', id='ws-status-bar')

    def on_show(self) -> None:
        self.query_one('#ws-main-in', Input).focus()

    def pre_process_nos(self) -> None:
        content: list[str] = []
        try:
            with open(self.filename, encoding=self.encoding, errors='replace') as f:
                content = f.readlines()
        except FileNotFoundError:
            raise Exception(f'File {self.filename} does not exist.')
        if not content:
            raise Exception(f'File {self.filename} is empty.')
        if self.nos_type == 'junos':
            self.context = JunosContext('', content, self.encoding)
        else:
            raise Exception(f'Unsupported NOS {self.nos_type}.')

    def draw(self, out: 'Iterable[str]' = []) -> None:
        control = self.query_one('#ws-main-out', TextLog)
        height = control.size.height
        if out:
            control.clear()
            control.scroll_home(animate=False)
            self.draw_data = out
        if not self.draw_data:
            return
        multiplier = 2 if out else 1
        for line in islice(self.draw_data, height * multiplier):
            if not line:
                continue
            if line[-1] == '\n':
                line = line[:-1]
            control.write(line, scroll_end=False)
        status_bar = self.query_one('#ws-status-bar')
        status = 'Spaces: {SPACES}  Lines: {LINES}  {ENCODING}  {FILENAME}'.format(
            SPACES=self.context.spaces,
            LINES=len(self.context.content),
            ENCODING=self.context.encoding.upper(),
            FILENAME=self.filename
        )
        if context_name := self.context.name:
            status = f'Context: {context_name}  ' + status
        status_bar.update(status)

    def update_path(self) -> None:
        control = self.query_one('#ws-path-line', Static)
        data = control.renderable
        current_path = self.context.prompt
        if data != current_path:
            current_path += '#'
            control.update(current_path.replace(self.context.delimiter, '>'))

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one('#ws-left-sidebar')
        if sidebar.styles.display == 'block':
            sidebar.styles.display = 'none'
        else:
            sidebar.styles.display = 'block'
