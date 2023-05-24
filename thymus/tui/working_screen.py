from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Optional
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
from rich.text import Text
from rich.syntax import Syntax

from ..contexts import JunosContext
from ..lexers import JunosLexer
from .extended_textlog import ExtendedTextLog
from .extended_input import ExtendedInput


if TYPE_CHECKING:
    from ..app_settings import SettingsResponse
    from ..contexts import Context, ContextResponse

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
    context: var['Optional[Context]'] = var(None)
    draw_data: var['Optional[ContextResponse]'] = var(None)

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

    def __draw(self, status: str, value: 'Iterable[str]', multiplier: int = 1) -> None:
        control = self.query_one('#ws-main-out', TextLog)
        theme = self.app.settings.theme
        code_width = self.app.settings.code_width
        if not control:
            return
        height = control.size.height
        for line in islice(value, height * multiplier):
            if not line:
                continue
            if line[-1] == '\n':
                line = line[:-1]
            if status == 'success':
                control.write(
                    Syntax(line, lexer=JunosLexer(), theme=theme, code_width=code_width),
                    scroll_end=False
                )
            else:
                control.write(Text(line, style='red'), scroll_end=False)
        status_bar = self.query_one('#ws-status-bar')
        if not status_bar:
            return
        bottom_state = 'Spaces: {SPACES}  Lines: {LINES}  Theme: {THEME}  {ENCODING}  {FILENAME}'.format(
            SPACES=self.context.spaces,
            LINES=len(self.context.content),
            THEME=theme.upper(),
            ENCODING=self.context.encoding.upper(),
            FILENAME=self.filename
        )
        if context_name := self.context.name:
            bottom_state = f'Context: {context_name}  ' + bottom_state
        status_bar.update(bottom_state)

    def draw(self, data: 'Optional[ContextResponse]' = None) -> None:
        multiplier: int = 1
        if data:
            # renew the self.draw_data
            if data.value:
                multiplier = 2
                control = self.query_one('#ws-main-out', TextLog)
                control.clear()
                control.scroll_home(animate=False)
                self.draw_data = data
            else:
                # nothing to draw
                return
        else:
            if not self.draw_data or not self.draw_data.value:
                # nothing to draw again
                return
        self.__draw(self.draw_data.status, self.draw_data.value, multiplier)

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
