from __future__ import annotations

from typing import cast, Optional
from collections.abc import Iterable, Callable

from textual import work
from textual.widgets import ListView, ListItem, Label
from textual.worker import Worker

from thymus.utils import find_common, rreplace


class Sidebar(ListView):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.current_worker: Optional[Worker] = None
        self.get_virtual_cb: Optional[Callable[[str], str]] = None
        super().__init__()

    def update(self, data: Iterable[str]) -> None:
        if self.current_worker:
            self.current_worker.cancel()

        self.current_worker = self._update(data)

    async def add_element(self, value: str) -> None:
        name = 'filler' if value == '...' else value

        for child in self.children:
            child = cast(ListItem, child)

            if child.name == value:
                return

        await self.append(ListItem(Label(value), name=name))

    def enter_view(self) -> None: ...

    def exit_view(self) -> None:
        if self.current_worker:
            self.current_worker.cancel()

        self.clear()

    @work(exclusive=True, exit_on_error=False)
    async def _update(self, data: Iterable[str]) -> None:
        limit = self.limit
        await self.clear()

        for elem in data:
            if not limit:
                await self.add_element('...')
                break

            await self.add_element(elem)
            limit -= 1

    def get_replacement(self, value: str) -> tuple[int, str]:
        if not self.get_virtual_cb:
            return len(self.children), value

        if self.highlighted_child and self.highlighted_child.name == 'filler':
            return len(self.children), value

        value = value.lower()

        if len(self.children) > 1:
            try:
                elements = [x.name for x in self.children if x.name]

                if elements[-1] == 'filler':
                    elements = elements[:-1]

                common = find_common(elements)
                extra_chars = self.get_virtual_cb(value)

                if not extra_chars or not common:
                    return len(self.children), value

                return len(self.children), rreplace(value, extra_chars, common)
            except Exception:
                return len(self.children), value
        elif len(self.children):
            if vmatch := self.get_virtual_cb(value):
                if self.highlighted_child and self.highlighted_child.name:
                    return 1, rreplace(value, vmatch, self.highlighted_child.name)

        return len(self.children), value
