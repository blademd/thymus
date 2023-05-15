from __future__ import annotations

import sys

from typing import TYPE_CHECKING
from asyncio import create_task, CancelledError


from textual.reactive import var
from textual.events import Key
from textual.widgets import (
    ListItem,
    ListView,
    Label,
    Input,
)


if TYPE_CHECKING:
    from asyncio import Task
    from typing import Any

    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Iterable, Coroutine
    else:
        from typing import Iterable, Coroutine


class ExtendedInput(Input):
    current_task: var['Task | None'] = var(None)

    async def action_submit(self) -> None:
        if not self.screen.context:
            return
        if out := self.screen.context.on_enter(self.value):
            self.screen.draw(out)
        self.__clear_left_sections()
        self.screen.update_path()  # always updates path due to its possible changes
        self.value = ''
        return await super().action_submit()

    def __clear_left_sections(self) -> None:
        if self.current_task:
            self.current_task.cancel()
        self.screen.query_one('#ws-sections-list', ListView).clear()

    async def on_input_changed(self, message: Input.Changed) -> None:
        if self.current_task:
            self.current_task.cancel()
        if message.value:
            self.current_task = create_task(
                self.__update_left_sections(
                    self.screen.context.update_virtual(
                        message.value
                    )
                )
            )
        else:
            self.__clear_left_sections()

    async def _on_key(self, event: Key) -> 'Coroutine[Any, Any, None]':
        if event.key == 'space':
            if self.value:
                if self.value[-1] == ' ':
                    self.value = self.value[:-1]
        elif event.key == 'tab':
            if self.value and self.cursor_position == len(self.value):
                control = self.screen.query_one('#ws-sections-list', ListView)
                if selected := control.highlighted_child:
                    if match := self.screen.context.get_virtual_from(self.value):
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
        return await super()._on_key(event)

    async def __update_left_sections(self, data: 'Iterable[str]') -> None:
        control = self.screen.query_one('#ws-sections-list', ListView)
        height = control.size.height
        try:
            new_children = list(data)
            if len(control.children) != len(new_children[:height]):
                await control.clear()
                if len(new_children) > height:
                    new_children = new_children[:height]
                for child in new_children:
                    await control.append(ListItem(Label(child), name=child))
            else:
                for child in control.children:
                    if child.name not in new_children:
                        await control.clear()
                        for child in new_children:
                            await control.append(ListItem(Label(child), name=child))
                        break
        except CancelledError:
            pass
