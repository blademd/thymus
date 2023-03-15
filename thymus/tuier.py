from __future__ import annotations

from textual.app import App
from textual.widgets import (
    Footer,
    Static,
    TextLog,
    ListView,
)
from textual.containers import Horizontal
from textual.reactive import var

from typing import TYPE_CHECKING

from . import __version__ as appver
from .tui import OpenDialog


if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.screen import Screen


class MExtendedListView(ListView):
    def action_select_cursor(self) -> None:
        if selected := self.highlighted_child:
            if value := selected.children[0].name:
                self.app.push_screen(value)
        return super().action_select_cursor()

class TThymus(App):
    CSS_PATH = 'tui/styles/main.css'
    SCREENS = {
        'open_file': OpenDialog()
    }
    BINDINGS = [
        ('ctrl+o', 'push_screen(\'open_file\')', 'Open file'),
        ('ctrl+d', 'dark_mode', 'Toggle dark mode'),
        ('ctrl+s', 'main_screen', 'Switch to main'),
    ]
    default_screen: var['Screen | None'] = var(None)

    def compose(self) -> 'ComposeResult':
        yield Footer()
        yield Static(f'Thymus ver. {appver}', id='main-welcome-out')
        yield Horizontal(
            TextLog(id='main-app-log'),
            MExtendedListView(id='main-screens-section'),
            id='main-middle-container'
        )

    def on_compose(self) -> None:
        self.default_screen = self.screen

    def action_main_screen(self) -> None:
        if self.default_screen:
            self.push_screen(self.default_screen)

    def action_dark_mode(self) -> None:
        self.dark = not self.dark

    async def action_pop_screen(self) -> None:
        if self.default_screen:
            self.default_screen.query_one('#main-screens-section', ListView).focus()
        return await super().action_pop_screen()
