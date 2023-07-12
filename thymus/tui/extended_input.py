from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.events import Key
from textual.widgets import (
    ListItem,
    ListView,
    Label,
    Input,
)

from .path_bar import PathBar

import sys


if TYPE_CHECKING:
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Iterable
    else:
        from typing import Iterable

    from .working_screen import WorkingScreen
    from ..tuier import TThymus


class ExtendedInput(Input):
    app: TThymus
    screen: WorkingScreen

    def action_submit(self) -> None:
        if not self.screen.context:
            return
        if self.value.startswith('global '):
            out = self.app.settings.process_command(self.value)
            self.screen.draw(out)
        elif out := self.screen.context.on_enter(self.value):
            self.screen.draw(out)
        self.screen.query_one('#ws-sections-list', ListView).clear()
        self.screen.query_one('#ws-path-line', PathBar).update_path()
        self.value = ''
        super().action_submit()

    async def on_input_changed(self, message: Input.Changed) -> None:
        if message.value:
            self.__update_side_bar(self.screen.context.update_virtual_cursor(message.value))
        else:
            self.screen.query_one('#ws-sections-list', ListView).clear()

    def _on_key(self, event: Key) -> None:
        if event.key == 'space':
            if self.value:
                if self.value[-1] == ' ':
                    self.value = self.value[:-1]
        elif event.key == 'tab':
            if self.value and self.cursor_position == len(self.value):
                control = self.screen.query_one('#ws-sections-list', ListView)
                if selected := control.highlighted_child:
                    if selected.name != 'filler' and (match := self.screen.context.get_virtual_from(self.value)):
                        self.value = selected.name.join(self.value.rsplit(match.strip(), 1))
                        self.cursor_position = len(self.value)
            event.stop()
        elif event.key == 'up':
            control = self.screen.query_one('#ws-sections-list', ListView)
            if control.children:
                control.action_cursor_up()
        elif event.key == 'down':
            control = self.screen.query_one('#ws-sections-list', ListView)
            if control.children:
                control.action_cursor_down()
        super()._on_key(event)

    @work(exclusive=True, exit_on_error=False)
    async def __update_side_bar(self, data: Iterable[str]) -> None:
        control = self.screen.query_one('#ws-sections-list', ListView)
        limit = self.app.settings.globals['sidebar_limit']
        await control.clear()
        for elem in data:
            if not limit:
                await control.append(ListItem(Label('...'), name='filler'))
                break
            await control.append(ListItem(Label(elem), name=elem))
            limit -= 1
