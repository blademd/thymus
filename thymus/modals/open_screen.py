from __future__ import annotations

from typing import Literal
from pathlib import Path
from dataclasses import dataclass
from collections.abc import Iterable

from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Static,
    ListItem,
    ListView,
    Label,
    Tabs,
    Button,
    DirectoryTree,
    Input,
    RadioSet,
    RadioButton,
)
from textual.validation import Number, Length

from thymus.settings import AppSettings, Platform


@dataclass
class OpenScreenNetworkData:
    host: str
    port: int
    username: str
    password: str
    passphrase: str
    secret: str
    protocol: Literal['ssh', 'telnet']


@dataclass
class OpenScreenResult:
    source: Literal['local', 'remote']
    target: str | OpenScreenNetworkData
    platform: Platform
    encoding: str


class ExtendedListView(ListView):
    def get_highlighted_child_value(self) -> str:
        if not self.highlighted_child or not self.highlighted_child.children:
            return ''

        if value := self.highlighted_child.children[0].name:
            return value

        return ''


class ExtendedDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [x for x in paths if not x.name.endswith('.history')]


class OpenScreen(ModalScreen[OpenScreenResult]):
    BINDINGS = [
        ('escape', 'dismiss', 'Exit'),
        ('p', "focus('platform')", 'Platform'),
        ('e', "focus('encoding')", 'Encoding'),
        ('t', "focus('tree')", 'Tree'),
        ('l', "focus('prev_tab')", ' File tab'),
        ('r', "focus('next_tab')", 'Network tab'),
    ]

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()

        self.path = Path.cwd()

        if default_path := settings['default_folder'].value:
            path = Path(default_path).expanduser()

            if path.exists() and path.is_dir():
                self.path = path

        self.platforms = settings.platforms
        self.last_platform: str = settings['last_opened_platform'].value

    # COMPOSE

    def compose_platforms(self) -> ComposeResult:
        yield Static('Select platform:')

        with ExtendedListView(id='open-screen-switches-platform'):
            if self.last_platform:
                if self.last_platform in self.platforms:
                    platform = self.platforms[self.last_platform]
                    yield ListItem(Label(platform['short_name'].value, name=self.last_platform))

                    for name, platform in self.platforms.items():
                        if name == self.last_platform:
                            continue

                        yield ListItem(Label(platform['short_name'].value, name=name))
                else:
                    for name, platform in self.platforms.items():
                        yield ListItem(Label(platform['short_name'].value, name=name))
            else:
                for name, platform in self.platforms.items():
                    yield ListItem(Label(platform['short_name'].value, name=name))

    def compose(self) -> ComposeResult:
        with Horizontal(id='open-screen-main-block'):
            with Vertical(id='open-screen-left-block'):
                yield from self.compose_platforms()

                yield Static('Select encoding:')

                with ExtendedListView(id='open-screen-switches-encoding'):
                    yield ListItem(Label('UTF-8-SIG', name='utf-8-sig'))
                    yield ListItem(Label('UTF-8', name='utf-8'))
                    yield ListItem(Label('CP1251', name='cp1251'))

            with Vertical(id='open-screen-right-block'):
                yield Tabs('File', 'Network', id='open-screen-tabs-main')

                # LEFT TAB
                with Vertical(id='open-screen-tabs-main-1'):
                    with Horizontal(id='open-screen-tabs-main-1-middle-block'):
                        yield Button(label='Up', id='open-screen-buttons-up')
                        yield Button(label='Open', id='open-screen-buttons-open')
                        yield Button(label='Refresh', id='open-screen-buttons-refresh')

                    with VerticalScroll():
                        yield ExtendedDirectoryTree(path=str(self.path), id='open-screen-trees-file')

                    yield Input(placeholder='Enter a path here...', id='open-screen-inputs-path')

                # RIGHT TAB
                with Vertical(id='open-screen-tabs-main-2', classes='disabled'):
                    yield Static('Retreieve data from a remote machine:', id='open-screen-caption')

                    with Horizontal(classes='open-screen-hor-container'):
                        yield Static('Host:', classes='open-screen-labels')
                        yield Input(
                            id='open-screen-inputs-host',
                            classes='open-screen-inputs',
                            validators=[Length(minimum=1, maximum=256)],
                        )

                    with Horizontal(classes='open-screen-hor-container'):
                        yield Static('Port:', classes='open-screen-labels')
                        yield Input(
                            value='22',
                            id='open-screen-inputs-port',
                            classes='open-screen-inputs',
                            validators=[Number(minimum=1, maximum=65535)],
                        )

                    with Horizontal(classes='open-screen-hor-container'):
                        yield Static('Username:', classes='open-screen-labels')
                        yield Input(
                            id='open-screen-inputs-username',
                            classes='open-screen-inputs',
                            validators=[Length(minimum=1, maximum=256)],
                        )

                    with Horizontal(classes='open-screen-hor-container'):
                        yield Static('Password:', id='open-screen-statics-password', classes='open-screen-labels')
                        yield Input(
                            password=True,
                            id='open-screen-inputs-password',
                            classes='open-screen-inputs',
                            validators=[Length(minimum=1, maximum=256)],
                        )

                    with Horizontal(classes='open-screen-hor-container'):
                        yield Static('Secret:', classes='open-screen-labels')
                        yield Input(
                            password=True,
                            id='open-screen-inputs-secret',
                            classes='open-screen-inputs',
                            validators=[Length(minimum=1, maximum=256)],
                        )

                    with Horizontal(classes='open-screen-hor-container'):
                        with RadioSet(id='open-screen-radio-sets-protocol'):
                            yield RadioButton('SSH', value=True)
                            yield RadioButton('Telnet')

                        with RadioSet(id='open-screen-radio-sets-auth-type'):
                            yield RadioButton('Password or Agent auth', value=True)
                            yield RadioButton('Search for keys')

                    with Horizontal(id='open-screen-hor-container-w-buttons', classes='open-screen-hor-container'):
                        yield Button('OPEN', id='open-screen-buttons-connect')

    # EVENTS

    def on_show(self) -> None:
        self.query_one(ExtendedDirectoryTree).focus()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        tab_one = self.query_one('#open-screen-tabs-main-1')
        tab_two = self.query_one('#open-screen-tabs-main-2')

        if event.tab.label_text == 'Network':
            self.query_one('#open-screen-inputs-host', Input).focus()
            tab_one.styles.display = 'none'
            tab_two.styles.display = 'block'
        else:
            self.query_one(ExtendedDirectoryTree).focus()
            tab_one.styles.display = 'block'
            tab_two.styles.display = 'none'

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        control = self.query_one('#open-screen-inputs-path', Input)
        control.value = str(event.path)
        control.focus()

    @on(RadioSet.Changed, '#open-screen-radio-sets-protocol')
    def on_proto_type_changed(self, event: RadioSet.Changed) -> None:
        control = self.query_one('#open-screen-inputs-port', Input)

        if event.radio_set.pressed_index == 0:
            if not control.value or control.value == '23' or not control.value.isdigit():
                control.value = '22'
        else:
            if not control.value or control.value == '22' or not control.value.isdigit():
                control.value = '23'

    @on(RadioSet.Changed, '#open-screen-radio-sets-auth-type')
    def on_ssh_auth_type_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.pressed_index == 1:
            self.query_one('#open-screen-statics-password', Static).update('Passphrase')
        else:
            self.query_one('#open-screen-statics-password', Static).update('Password')

    @on(Input.Submitted, '#open-screen-inputs-path')
    def on_input_submitted_path(self) -> None:
        self.query_one('#open-screen-trees-file', ExtendedDirectoryTree).focus()
        self.post_message(Button.Pressed(self.query_one('#open-screen-buttons-open', Button)))

    @on(Button.Pressed, '#open-screen-buttons-up')
    def on_button_pressed_up(self) -> None:
        self.path = self.path.parent
        self.query_one('#open-screen-trees-file', ExtendedDirectoryTree).path = self.path

    @on(Button.Pressed, '#open-screen-buttons-open')
    def on_button_pressed_open(self) -> None:
        if target := self.query_one('#open-screen-inputs-path', Input).value:
            platforms = self.query_one('#open-screen-switches-platform', ExtendedListView)
            encodings = self.query_one('#open-screen-switches-encoding', ExtendedListView)

            platform_name = platforms.get_highlighted_child_value()
            encoding = encodings.get_highlighted_child_value()

            result = OpenScreenResult(
                source='local',
                target=target,
                platform=self.platforms[platform_name],
                encoding=encoding,
            )
            self.dismiss(result)
        else:
            self.notify('Path is not specified.', severity='error')

    @on(Button.Pressed, '#open-screen-buttons-refresh')
    def on_button_pressed_refresh(self) -> None:
        self.query_one('#open-screen-trees-file', ExtendedDirectoryTree).reload()

    @on(Button.Pressed, '#open-screen-buttons-connect')
    def on_button_pressed_connect(self) -> None:
        is_telnet = bool(self.query_one('#open-screen-radio-sets-protocol', RadioSet).pressed_index)
        is_key_based = bool(self.query_one('#open-screen-radio-sets-auth-type', RadioSet).pressed_index)

        password_or_phrase = self.query_one('#open-screen-inputs-password', Input).value
        platforms = self.query_one('#open-screen-switches-platform', ExtendedListView)
        encodings = self.query_one('#open-screen-switches-encoding', ExtendedListView)

        connect_data = {
            'host': self.query_one('#open-screen-inputs-host', Input).value,
            'port': int(self.query_one('#open-screen-inputs-port', Input).value),
            'username': self.query_one('#open-screen-inputs-username', Input).value,
            'password': '' if is_key_based else password_or_phrase,
            'passphrase': password_or_phrase if is_key_based else '',
            'secret': self.query_one('#open-screen-inputs-secret', Input).value,
            'protocol': 'telnet' if is_telnet else 'ssh',
        }

        platform_name = platforms.get_highlighted_child_value()
        encoding = encodings.get_highlighted_child_value()

        result = OpenScreenResult(
            source='remote',
            target=OpenScreenNetworkData(**connect_data),  # type: ignore
            platform=self.platforms[platform_name],
            encoding=encoding,
        )
        self.dismiss(result)

    # ACTIONS

    def action_focus(self, target: str) -> None:
        if target == 'platform':
            self.query_one('#open-screen-switches-platform').focus()
        elif target == 'encoding':
            self.query_one('#open-screen-switches-encoding').focus()
        elif target == 'tree':
            control = self.query_one('#open-screen-tabs-main', Tabs)

            if control.active_tab and control.active_tab.label_text == 'File':
                self.query_one('#open-screen-trees-file').focus()
        elif target == 'next_tab':
            control = self.query_one('#open-screen-tabs-main', Tabs)
            control.action_next_tab()
        elif target == 'prev_tab':
            control = self.query_one('#open-screen-tabs-main', Tabs)
            control.action_previous_tab()
