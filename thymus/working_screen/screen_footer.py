from __future__ import annotations

from typing import Literal

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label
from textual.containers import Horizontal
from textual.reactive import var


class ScreenFooter(Widget):
    mode: var[Literal['view', 'edit']] = var('view')
    path = var('')
    virtual_path = var('')
    platform_name = var('')
    encoding = var('')
    source: var[Literal['local', 'remote']] = var('local')
    delimiter = var('')
    current_context = var(0)
    spaces = var(0)
    theme = var('')
    context_name = var('')

    def compose(self) -> ComposeResult:
        with Horizontal(classes='key-container'):
            yield Label(id='platform-key', classes='key')
            yield Label(id='context-id-key', classes='key')
            yield Label(id='context-name', classes='key')
            yield Label(id='path-key', classes='key')
        yield Label('', classes='meta')
        yield Label('', classes='mode')

    def update_meta(self) -> None:
        meta: list[str] = []

        meta.append(self.encoding.upper())
        meta.append(f'Spaces: {self.spaces}')
        meta.append(f'Theme: {self.theme}')

        meta_line = ' • '.join(meta)
        self.query_one('.meta', Label).update(meta_line)

    def watch_platform_name(self, platform: str) -> None:
        self.query_one('#platform-key', Label).update(f'[reverse]{platform.upper()}[/reverse]')

    def watch_theme(self) -> None:
        self.update_meta()

    def watch_current_context(self, context_id: int) -> None:
        self.query_one('#context-id-key', Label).update(f'Context: [reverse]{context_id}[/reverse]')

    def watch_context_name(self, context_name: str) -> None:
        if context_name:
            self.query_one('#context-name', Label).update(f'Name: [reverse]{context_name}[/reverse]')

    def watch_path(self, path: str) -> None:
        self.query_one('#path-key', Label).update(f'{self.source.capitalize()} source: [reverse]{path}[/reverse]')

    def watch_source(self, source: str) -> None:
        self.query_one('#path-key', Label).update(f'{source.capitalize()} source: [reverse]{self.path}[/reverse]')

    def watch_mode(self, mode: str) -> None:
        self.query_one('.mode', Label).update(mode)

    def watch_encoding(self) -> None:
        self.update_meta()

    def watch_spaces(self) -> None:
        self.update_meta()
