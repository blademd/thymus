from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from textual import work
from textual.screen import ModalScreen
from textual.reactive import var
from textual.validation import Number, Length
from textual.worker import get_current_worker
from textual.containers import (
    Horizontal,
    Vertical,
    VerticalScroll,
)
from textual.widgets import (
    Button,
    Input,
    ListView,
    ListItem,
    Label,
    Static,
    Tabs,
    RadioSet,
    RadioButton,
    DirectoryTree,
    LoadingIndicator,
)

from .working_screen.working_screen import WorkingScreen
from .modals.error_modal import ErrorScreen
from .net_loader import NetLoader


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from ..tuier import TThymus


class OpenDialog(ModalScreen):
    app: TThymus

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Pop screen'),
        ('p', 'focus(\'platform\')', 'Platform'),
        ('e', 'focus(\'encoding\')', 'Encoding'),
        ('t', 'focus(\'tree\')', 'Tree'),
        ('l', 'focus(\'prev_tab\')', ' File tab'),
        ('r', 'focus(\'next_tab\')', 'Network tab'),
    ]
    current_path: var[Path] = var(Path.cwd())
    lock: var[bool] = var(False)

    def __open(self, filename: str = '', content: list[str] = []) -> None:
        screen_name = str(uuid4())
        nos_switch = self.query_one('#od-nos-switch', ListView)
        encoding_switch = self.query_one('#od-encoding-switch', ListView)
        selected_nos = nos_switch.highlighted_child.children[0].name
        selected_encoding = encoding_switch.highlighted_child.children[0].name
        try:
            self.app.install_screen(
                screen=WorkingScreen(
                    filename=filename,
                    content=content,
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
                if filename:
                    err_msg = f'Error has occurred during the opening of the "{filename}": {err}'
                else:
                    err_msg = f'Error has occurred during the opening from the network: {err}'
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

    def open_from_file(self, filename: str) -> None:
        if filename:
            self.app.logger.debug(f'Opening the file: {filename}.')
            self.__open(filename=filename)

    def modal_callback(self, err_msg: str) -> None:
        # The temporary workaround for https://github.com/Textualize/textual/issues/3064
        self.app.push_screen(ErrorScreen(err_msg))

    def freeze_callback(self, is_freeze: bool) -> None:
        # The temporary workaround for https://github.com/Textualize/textual/issues/3064
        self.query_one('#od-main-container', Horizontal).disabled = is_freeze

    @work(exclusive=True, thread=True)
    def open_from_network(self) -> None:
        if self.lock:
            return
        self.lock = True
        worker = get_current_worker()
        platform_ctrl = self.query_one('#od-nos-switch', ListView)
        hostname_ctrl = self.query_one('#od-nt-host-in', Input)
        port_ctrl = self.query_one('#od-nt-port-in', Input)
        username_ctrl = self.query_one('#od-nt-username-in', Input)
        password_ctrl = self.query_one('#od-nt-password-in', Input)
        switch_ctrl = self.query_one('#od-net-switch', RadioSet)
        if not worker.is_cancelled:
            self.app.call_from_thread(self.freeze_callback, True)
        try:
            selected_nos = platform_ctrl.highlighted_child.children[0].name
            loader = NetLoader(
                host=hostname_ctrl.value,
                port=int(port_ctrl.value),
                username=username_ctrl.value,
                password=password_ctrl.value,
                proto=switch_ctrl.pressed_index,
                platform=selected_nos
            )
            if not worker.is_cancelled:
                self.app.logger.debug(f'Opening from a remote host: {hostname_ctrl.value}:{port_ctrl.value}.')
                self.app.call_from_thread(self.__open, content=loader.data)
        except Exception as err:
            err_msg = f'Error has occurred during the opening from the network: {err}'
            if not worker.is_cancelled:
                self.app.logger.error(err_msg)
                self.app.call_from_thread(self.modal_callback, err_msg)
        if not worker.is_cancelled:
            self.app.call_from_thread(self.freeze_callback, False)
        self.lock = False

    def compose(self) -> ComposeResult:
        with Horizontal(id='od-main-container'):
            with Vertical(id='od-left-block'):
                yield Static('Select platform:')
                with ListView(id='od-nos-switch'):
                    yield ListItem(Label('Juniper JunOS', name='junos'))
                    yield ListItem(Label('Cisco IOS', name='ios'))
                    yield ListItem(Label('Cisco NX-OS', name='nxos'))
                    yield ListItem(Label('Arista EOS', name='eos'))
                yield Static('Select encoding:')
                with ListView(id='od-encoding-switch'):
                    yield ListItem(Label('UTF-8-SIG', name='utf-8-sig'))
                    yield ListItem(Label('UTF-8', name='utf-8'))
                    yield ListItem(Label('CP1251', name='cp1251'))
            with Vertical(id='od-right-block'):
                yield Tabs('From file', 'From network', id='od-tabs')
                # LEFT TAB
                with Vertical(id='od-tab-one'):
                    with Horizontal(id='od-right-middle-block'):
                        yield Button('UP', id='od-up-button', variant='primary')
                        yield Button('OPEN', id='od-open-button', variant='primary')
                        yield Button('REFRESH', id='od-refresh-button', variant='primary')
                    with VerticalScroll():
                        yield DirectoryTree(path=str(self.current_path.cwd()), id='od-directory-tree')
                    yield Input(placeholder='Filename', id='od-main-in')
                # RIGHT TAB
                with Vertical(id='od-tab-two', classes='od-disabled'):
                    yield Static('Download config from a remote machine & open it:', id='od-cap')
                    with Horizontal(classes='od-hor-con'):
                        yield Static('Host:', id='od-label-host', classes='od-labels')
                        yield Input(
                            id='od-nt-host-in',
                            classes='od-inputs',
                            validators=[
                                Length(minimum=1, maximum=256),
                            ]
                        )
                    with Horizontal(classes='od-hor-con'):
                        yield Static('Port:', id='od-label-port', classes='od-labels')
                        yield Input(
                            value='22',
                            id='od-nt-port-in',
                            classes='od-inputs',
                            validators=[
                                Number(minimum=1, maximum=65535),
                            ]
                        )
                    with Horizontal(classes='od-hor-con'):
                        yield Static('Username:', id='od-label-username', classes='od-labels')
                        yield Input(
                            id='od-nt-username-in',
                            classes='od-inputs',
                            validators=[
                                Length(minimum=1, maximum=256),
                            ]
                        )
                    with Horizontal(classes='od-hor-con'):
                        yield Static('Password:', id='od-label-password', classes='od-labels')
                        yield Input(
                            password=True,
                            id='od-nt-password-in',
                            classes='od-inputs',
                            validators=[
                                Length(minimum=1, maximum=256),
                            ]
                        )
                    with Horizontal(classes='od-hor-con'):
                        with RadioSet(id='od-net-switch'):
                            yield RadioButton('SSH', value=True)
                            yield RadioButton('Telnet')
                    with Horizontal(id='od-hor-con-butns', classes='od-hor-con'):
                        yield Button('OPEN', id='od-connect-button', variant='primary')
                        yield LoadingIndicator(id='od-nt-loading', classes='od-disabled')

    def on_show(self) -> None:
        self.query_one(DirectoryTree).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        tree = self.query_one(DirectoryTree)
        if event.button.id == 'od-open-button':
            filename = self.query_one('#od-main-in', Input).value
            self.open_from_file(filename)
        elif event.button.id == 'od-up-button':
            self.current_path = self.current_path.parent
            tree.path = self.current_path
        elif event.button.id == 'od-refresh-button':
            tree.reload()
        elif event.button.id == 'od-connect-button':
            self.open_from_network()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'od-main-in':
            value = event.input.value
            self.open_from_file(value)
        else:
            self.open_from_network()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        input = self.query_one('#od-main-in', Input)
        input.focus()
        input.value = str(event.path)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        flag = True if event.tab.label_text == 'From network' else False
        tab_one = self.query_one('#od-tab-one')
        tab_two = self.query_one('#od-tab-two')
        tab_one.styles.display = 'none' if flag else 'block'
        tab_two.styles.display = 'block' if flag else 'none'
        if flag:
            self.query_one('#od-nt-host-in', Input).focus()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        control = self.query_one('#od-nt-port-in', Input)
        if event.radio_set.pressed_index == 0:
            if not control.value or control.value == '23' or not control.value.isdigit():
                control.value = '22'
        else:
            if not control.value or control.value == '22' or not control.value.isdigit():
                control.value = '23'

    def action_focus(self, target: str) -> None:
        if target == 'platform':
            self.query_one('#od-nos-switch').focus()
        elif target == 'encoding':
            self.query_one('#od-encoding-switch').focus()
        elif target == 'tree':
            control = self.query_one('#od-tabs', Tabs)
            if control.active_tab and control.active_tab.label_text == 'From file':
                self.query_one('#od-directory-tree').focus()
        elif target == 'next_tab':
            control = self.query_one('#od-tabs', Tabs)
            control.action_next_tab()
        elif target == 'prev_tab':
            control = self.query_one('#od-tabs', Tabs)
            control.action_previous_tab()
