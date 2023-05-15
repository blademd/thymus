from __future__ import annotations

from textual.screen import Screen
from textual.reactive import Reactive
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
    TextLog,
)
from textual.widgets._directory_tree import DirectoryTree, DirEntry

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from .working_screen import WorkingScreen


if TYPE_CHECKING:
    from textual.app import ComposeResult


class ODExtendedInput(Input):
    async def action_submit(self) -> None:
        self.screen.open_file(self.value)
        return await super().action_submit()

class OpenDialog(Screen):
    BINDINGS = [
        ('escape', 'app.pop_screen', 'Pop screen')
    ]
    current_path: Reactive[Path] = Reactive(Path.cwd())

    def compose(self) -> 'ComposeResult':
        yield Horizontal(
            Vertical(
                Static('Select NOS:'),
                ListView(
                    ListItem(Label('Juniper JunOS', name='junos')),
                    id='od-nos-switch'
                ),
                Static('Select encoding:'),
                ListView(
                    ListItem(Label('UTF-8-SIG', name='utf-8-sig')),
                    ListItem(Label('UTF-8', name='utf-8')),
                    ListItem(Label('CP1251', name='cp1251')),
                    id='od-encoding-switch'
                ),
                id='od-left-block'
            ),
            Vertical(
                Horizontal(
                    Button('UP', id='od-up-button', variant='primary'),
                    Button('OPEN', id='od-open-button', variant='primary'),
                    Static(id='od-error-caption'),
                    id='od-top-container'
                ),
                DirectoryTree(path=str(self.current_path.absolute()), id='od-directory-tree'),
                Input(placeholder='filename...', id='od-main-in'),
                id='od-right-block'
            ),
        )
        # yield Vertical(
        #     Horizontal(
        #         Button('UP', id='od-up-button', variant='primary'),
        #         Button('OPEN', id='od-open-button', variant='primary'),
        #         ListView(
        #             ListItem(Label('Juniper JunOS', name='junos')),
        #             # ListItem(Label('Arista EOS', name='eos')),
        #             # ListItem(Label('Cisco IOS', name='ios')),
        #             id='od-nos-switch'
        #         ),
        #         ListView(
        #             ListItem(Label('UTF-8-SIG', name='utf-8-sig')),
        #             ListItem(Label('UTF-8', name='utf-8')),
        #             ListItem(Label('CP1251', name='cp1251')),
        #             id='od-encoding-switch'
        #         ),
        #         Static(id='od-error-caption'),
        #         id='od-top-container'
        #     ),
        #     DirectoryTree(path=str(self.current_path.absolute()), id='od-directory-tree'),
        #     ODExtendedInput(placeholder='filename...', id='od-main-in')
        # )

    def on_ready(self) -> None:
        self.query_one(DirectoryTree).focus()

    def on_show(self) -> None:
        # TODO: update DirTree here
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'od-open-button':
            filename = self.query_one(Input).value
            self.open_file(filename)
        elif event.button.id == 'od-up-button':
            self.current_path = self.current_path.parent

    def open_file(self, filename: str) -> None:
        if not filename:
            return
        screen_name = str(uuid4())
        nos_switch = self.query_one('#od-nos-switch', ListView)
        encoding_switch = self.query_one('#od-encoding-switch', ListView)
        selected_nos = nos_switch.highlighted_child.children[0].name
        selected_encoding = encoding_switch.highlighted_child.children[0].name
        control = self.query_one('#od-error-caption', Static)
        if selected_nos != 'junos':
            control.update('Temporary unsupported NOS!')
            return
        control.update('')
        self.app.pop_screen()
        try:
            self.app.install_screen(
                WorkingScreen(
                    filename=filename,
                    nos_type=selected_nos,
                    encoding=selected_encoding,
                    name=screen_name
                ),
                screen_name
            )
        except Exception as err:
            if self.app.default_screen:
                control = self.app.default_screen.query_one('#main-app-log', TextLog)
                control.write(f'Error has occurred: {err}')
            self.app.uninstall_screen(screen_name)
        else:
            self.app.push_screen(screen_name)
            if self.app.default_screen:
                control = self.app.default_screen.query_one('#main-screens-section', ListView)
                control.append(ListItem(Label(filename, name=screen_name)))

    def watch_current_path(self, value: Path) -> None:
        tree = self.query_one(DirectoryTree)
        label = tree.process_label(str(value.absolute()))
        data = DirEntry(value.absolute(), True)
        new_node = tree._add_node(None, label, data)
        tree.root = new_node
        tree._load_directory(new_node)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        input = self.query_one(Input)
        input.focus()
        input.value = str(event.path)
