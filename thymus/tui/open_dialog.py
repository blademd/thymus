from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from textual.screen import ModalScreen
from textual.reactive import var
from textual.containers import (
    Horizontal,
    Vertical,
)
from textual.widgets import (
    Button,
    Input,
    ListView,
    ListItem,
    Label,
    Static,
)
from textual.widgets._directory_tree import DirectoryTree

from .working_screen.working_screen import WorkingScreen
from .modals.error_modal import ErrorScreen


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from ..tuier import TThymus


class OpenDialog(ModalScreen):
    BINDINGS = [
        ('escape', 'app.pop_screen', 'Pop screen')
    ]
    current_path: var[Path] = var(Path.cwd())

    def open_file(self, filename: str) -> None:
        if not filename:
            return
        screen_name = str(uuid4())
        nos_switch = self.query_one('#od-nos-switch', ListView)
        encoding_switch = self.query_one('#od-encoding-switch', ListView)
        selected_nos = nos_switch.highlighted_child.children[0].name
        selected_encoding = encoding_switch.highlighted_child.children[0].name
        control = self.query_one('#od-error-caption', Static)
        control.update('')
        self.app: TThymus
        self.app.logger.debug(f'Opening the file: {filename}.')
        try:
            self.app.install_screen(
                screen=WorkingScreen(
                    filename=filename,
                    nos_type=selected_nos,
                    encoding=selected_encoding,
                    name=screen_name
                ),
                name=screen_name
            )
        except Exception as err:
            self.app.uninstall_screen(screen_name)
            if len(err.args) == 2 and err.args[1] == 'logged':
                self.app.push_screen(ErrorScreen(err.args[0]))
            elif len(err.args):
                err_msg = f'Error has occurred during the opening of the "{filename}": {err}'
                self.app.logger.error(err_msg)
                self.app.push_screen(ErrorScreen(err_msg))
        else:
            self.app.pop_screen()  # pops itself
            if len(self.app.screen_stack) == 1:
                self.app.push_screen(screen_name)
            else:
                self.app.switch_screen(screen_name)
            if screen_name not in self.app.working_screens:
                self.app.working_screens.append(screen_name)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id='od-left-block'):
                yield Static('Select platform:')
                with ListView(id='od-nos-switch'):
                    yield ListItem(Label('Juniper JunOS', name='junos'))
                    yield ListItem(Label('Cisco IOS', name='ios'))
                    yield ListItem(Label('Arista EOS', name='eos'))
                yield Static('Select encoding:')
                with ListView(id='od-encoding-switch'):
                    yield ListItem(Label('UTF-8-SIG', name='utf-8-sig'))
                    yield ListItem(Label('UTF-8', name='utf-8'))
                    yield ListItem(Label('CP1251', name='cp1251'))
            with Vertical(id='od-right-block'):
                with Horizontal(id='od-top-container'):
                    yield Button('UP', id='od-up-button', variant='primary')
                    yield Button('OPEN', id='od-open-button', variant='primary')
                    yield Button('REFRESH', id='od-refresh-button', variant='primary')
                    yield Static(id='od-error-caption')
                yield DirectoryTree(path=str(self.current_path.cwd()), id='od-directory-tree')
                yield Input(placeholder='filename...', id='od-main-in')

    def on_show(self) -> None:
        self.query_one(DirectoryTree).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        tree = self.query_one(DirectoryTree)
        if event.button.id == 'od-open-button':
            filename = self.query_one(Input).value
            self.open_file(filename)
        elif event.button.id == 'od-up-button':
            self.current_path = self.current_path.parent
            tree.path = self.current_path
        elif event.button.id == 'od-refresh-button':
            tree.reload()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.input.value
        self.open_file(value)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        input = self.query_one(Input)
        input.focus()
        input.value = str(event.path)
