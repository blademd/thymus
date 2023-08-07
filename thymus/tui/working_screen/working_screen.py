from __future__ import annotations

from typing import TYPE_CHECKING
from itertools import islice
from collections import deque

from textual.screen import Screen
from textual.reactive import var
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
)
from textual.widgets import (
    Input,
    RichLog,
)
from rich.text import Text
from rich.syntax import Syntax

from ...contexts import (
    JunOSContext,
    IOSContext,
    EOSContext,
    NXOSContext,
)
from .extended_textlog import ExtendedTextLog
from .extended_input import ExtendedInput
from .status_bar import StatusBar
from .path_bar import PathBar
from .left_sidebar import LeftSidebar
from ..modals.quit_modal import QuitScreen


if TYPE_CHECKING:
    from typing import Optional

    from textual.app import ComposeResult

    from ...tuier import TThymus
    from ...contexts import Context
    from ...responses import Response


PLATFORMS: dict[str, Context] = {
    'junos': JunOSContext,
    'ios': IOSContext,
    'eos': EOSContext,
    'nxos': NXOSContext,
}


class WorkingScreen(Screen):
    app: TThymus

    BINDINGS = [
        ('ctrl+b', 'toggle_sidebar', 'Toggle sidebar'),
        ('escape', 'request_quit', 'Quit'),
        ('n', 'draw', 'Next screen'),
    ]
    filename: var[str] = var('')
    nos_type: var[str] = var('')
    encoding: var[str] = var('')
    context: var[Context] = var(None)
    draw_data: var[Optional[Response]] = var(None)

    def __init__(
        self,
        nos_type: str,
        encoding: str,
        filename: str = '',
        content: list[str] = [],
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        if nos_type not in PLATFORMS:
            err_msg = f'Unsupported platform: {nos_type}.'
            self.app.logger.error(err_msg)
            raise Exception(err_msg, 'logged')
        self.nos_type = nos_type
        self.encoding = encoding
        if filename:
            self.filename = filename
            try:
                content = open(filename, encoding=encoding, errors='replace').readlines()
            except FileNotFoundError:
                err_msg = f'Cannot open the file "{filename}", it does not exist. Platform: {nos_type}.'
                self.app.logger.error(err_msg)
                raise Exception(err_msg, 'logged')
        else:
            self.filename = self.screen.name
        if not content:
            err_msg = f'File "{self.filename}" is empty. Platform: {nos_type}.'
            self.app.logger.error(err_msg)
            raise Exception(err_msg, 'logged')
        self.context = PLATFORMS[nos_type](
            name='',
            content=content,
            encoding=encoding,
            settings=getattr(self.app.settings, nos_type),
            logger=self.app.logger
        )
        self.app.logger.info(f'File "{self.filename}" for the platform "{nos_type}" was opened.')

    def compose(self) -> ComposeResult:
        with Horizontal(id='ws-right-field'):
            with Container(id='ws-left-sidebar'):
                yield LeftSidebar(id='ws-sections-list')
            with Vertical():
                with Container(id='ws-main-out-container'):
                    yield ExtendedTextLog(id='ws-main-out')
                with Vertical(id='ws-right-bottom-controls'):
                    yield PathBar('#', id='ws-path-line')
                    yield ExtendedInput(placeholder='>', id='ws-main-in')
        yield StatusBar(f'Current filename: {self.filename}', id='ws-status-bar')

    def on_show(self) -> None:
        self.query_one('#ws-main-in', Input).focus()

    def __draw(self, multiplier: int = 1) -> None:
        control = self.query_one('#ws-main-out', RichLog)
        theme = self.app.settings.globals['theme']
        height = control.size.height
        width = control.size.width - 2
        color = control.styles.background.rich_color.name
        try:
            for line in islice(self.draw_data.value, height * multiplier):
                if not line:
                    continue
                line = line.rstrip()
                if self.draw_data.rtype == 'data':
                    code_width = max(len(line) + 1, width)
                    syntax = Syntax(
                        code=line,
                        lexer=self.context.lexer(),
                        theme=theme,
                        code_width=code_width,
                        background_color=color
                    )
                    control.write(syntax, scroll_end=False)
                else:
                    color = 'green' if self.draw_data.is_ok else 'red'
                    control.write(Text(line, style=color), scroll_end=False)
        except Exception as err:
            control.write(Text(f'Error: {err}', style='red'), scroll_end=False)
            self.app.logger.debug(f'"{err}" for "{self.nos_type}" [{self.filename}].')
            self.draw_data = None
        status_bar = self.query_one('#ws-status-bar', StatusBar)
        status_bar.update_bar()

    def draw(self, data: Optional[Response] = None) -> None:
        multiplier: int = 1
        if data:
            multiplier = 2
            control = self.query_one('#ws-main-out', RichLog)
            control.clear()
            control.scroll_home(animate=False)
            self.draw_data = data
        if not self.draw_data:
            return
        self.__draw(multiplier)

    def action_request_quit(self) -> None:
        self.app.logger.debug(f'Exit was requested: {self.filename}.')
        self.app.push_screen(QuitScreen(self))

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one('#ws-left-sidebar')
        if sidebar.styles.display == 'block':
            sidebar.styles.display = 'none'
        else:
            sidebar.styles.display = 'block'

    def action_draw(self) -> None:
        self.draw()
