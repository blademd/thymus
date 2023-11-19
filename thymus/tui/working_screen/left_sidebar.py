from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.widgets import (
    ListItem,
    ListView,
    Label,
)

from ...misc import (
    find_common,
    rreplace,
)

import sys


if TYPE_CHECKING:
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Iterable, Sequence
    else:
        from typing import Iterable, Sequence

    from .working_screen import WorkingScreen
    from ...tuier import TThymus


class LeftSidebar(ListView, can_focus=False):
    app: TThymus
    screen: WorkingScreen
    children: Sequence[ListItem]

    async def add_element(self, value: str) -> None:
        name = 'filler' if value == '...' else value
        for child in self.children:
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
        if not self.screen.context:
            return
        if value:
            if '| ' in value:
                return
            self.__update(self.screen.context.update_virtual_cursor(value))
        else:
            self.clear()

    def get_replacement(self, value: str) -> str:
        if self.highlighted_child and self.highlighted_child.name == 'filler':
            return value
        if not self.screen.context:
            return value
        value = value.lower()
        strict_tab = False
        if strict_val := self.app.settings.current_settings.get('sidebar_strict_on_tab', ''):
            strict_tab = strict_val in (1, '1', 'on')
        if strict_tab:
            if len(self.children) > 1:
                try:
                    elems = [x.name for x in self.children if x.name]
                    if elems[-1] == 'filler':
                        elems = elems[:-1]
                    common = find_common(elems)
                    extra_chars = self.screen.context.get_virtual_from(value)
                    if not extra_chars or not common:
                        return value
                    return rreplace(value, extra_chars, common)
                except Exception as err:
                    self.app.logger.debug(f'Error during enhanced Tab: {err}.')
                    return value
            elif len(self.children):
                if match := self.screen.context.get_virtual_from(value):
                    return (
                        rreplace(value, match, self.highlighted_child.name)
                        if self.highlighted_child and self.highlighted_child.name
                        else value
                    )
            else:
                return value
        else:
            if match := self.screen.context.get_virtual_from(value):
                return (
                    rreplace(value, match, self.highlighted_child.name)
                    if self.highlighted_child and self.highlighted_child.name
                    else value
                )
        return value

    @work(exclusive=True, exit_on_error=False)
    async def __update(self, data: Iterable[str]) -> None:
        limit = int(self.app.settings.current_settings['sidebar_limit'])
        await self.clear()
        for elem in data:
            if not limit:
                await self.add_element('...')
                break
            await self.add_element(elem)
            limit -= 1
