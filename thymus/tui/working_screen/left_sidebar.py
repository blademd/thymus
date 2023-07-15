from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.widgets import (
    ListItem,
    ListView,
    Label,
)

import sys


if TYPE_CHECKING:
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Iterable
    else:
        from typing import Iterable

    from .working_screen import WorkingScreen
    from ...tuier import TThymus


class LeftSidebar(ListView):
    app: TThymus
    screen: WorkingScreen

    async def add_element(self, value: str) -> None:
        name = 'filler' if value == '...' else value
        for child in self.children:
            child: ListItem
            if child.name == value:
                return
        await self.append(ListItem(Label(value), name=name))

    def action_cursor_down(self) -> None:
        if self.children:
            super().action_cursor_down()

    def action_cursor_up(self) -> None:
        if self.children:
            super().action_cursor_up()

    def update(self, value: str) -> None:
        if value:
            if '| ' in value:
                return
            self.__update(self.screen.context.update_virtual_cursor(value))
        else:
            self.clear()

    @work(exclusive=True, exit_on_error=False)
    async def __update(self, data: Iterable[str]) -> None:
        limit = int(self.app.settings.globals['sidebar_limit'])
        await self.clear()
        for elem in data:
            if not limit:
                await self.add_element('...')
                break
            await self.add_element(elem)
            limit -= 1
