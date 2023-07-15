from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Static


if TYPE_CHECKING:
    from textual.geometry import Size

    from ...tuier import TThymus
    from .working_screen import WorkingScreen


class PathBar(Static):
    app: TThymus
    screen: WorkingScreen

    def update_path(self) -> None:
        current_path = str(self.renderable)
        active_path = self.screen.context.prompt
        new_value = current_path
        if current_path != active_path:
            new_value = active_path + '#'
            new_value = new_value.replace(self.screen.context.delimiter, '>')
        if len(new_value) >= self.size.width:
            new_value = new_value[-(self.size.width - 3):]
            self.update(f'...{new_value}')
        else:
            self.update(new_value)

    def watch_virtual_size(self, prev: Size, new: Size) -> None:
        self.update_path()
