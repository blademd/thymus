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


class LeftSidebar(ListView, can_focus=False):
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

    def get_replacement(self, value: str) -> str:
        if self.highlighted_child and self.highlighted_child.name == 'filler':
            return value
        if self.app.settings.is_bool_set('sidebar_strict_on_tab'):
            if len(self.children) > 1:
                try:
                    elems = [x.name for x in self.children]
                    if elems[-1] == 'filler':
                        elems = elems[:-1]
                    min_len = min(len(x) for x in elems)
                    common = ''
                    for step in range(min_len):
                        char = elems[0][step]
                        if all(s[step] == char for s in elems):
                            common += char
                        else:
                            break
                    if not common:
                        return value
                    parts = value.split()
                    parts[-1] = common
                    return ' '.join(parts)
                except Exception as err:
                    self.app.logger.debug(f'Error during enhanced Tab: {err}.')
                    return value
            elif len(self.children):
                if match := self.screen.context.get_virtual_from(value):
                    return self.highlighted_child.name.join(value.rsplit(match.strip(), 1))
            else:
                return value
        else:
            if match := self.screen.context.get_virtual_from(value):
                return self.highlighted_child.name.join(value.rsplit(match.strip(), 1))
        return value

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
