from __future__ import annotations

from typing import Literal

from textual.widgets import Static
from textual.reactive import var


class PathBar(Static, can_focus=False):
    mode: var[Literal['view', 'edit']] = var('view')
    virtual_path = var('')
    delimiter = var('')

    def update_bar(self) -> None:
        path = self.virtual_path.replace(self.delimiter, '>')
        end = '#' if self.mode == 'edit' else '>'
        path += end
        if len(path) >= self.size.width:
            path = path[-(self.size.width - 3) :]
            path = '...' + path
        self.update(path)

    def watch_mode(self) -> None:
        self.update_bar()

    def watch_virtual_path(self) -> None:
        self.update_bar()

    def watch_delimiter(self) -> None:
        self.update_bar()

    def watch_virtual_size(self) -> None:
        self.update_bar()
