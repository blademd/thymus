from __future__ import annotations

from typing import TYPE_CHECKING

from textual.events import Key
from textual.widgets import Input

from .path_bar import PathBar
from .left_sidebar import LeftSidebar
from .extended_textlog import ExtendedTextLog


if TYPE_CHECKING:
    from .working_screen import WorkingScreen
    from ...tuier import TThymus


class ExtendedInput(Input):
    app: TThymus
    screen: WorkingScreen

    def action_submit(self) -> None:
        if not self.screen.context or not self.value:
            return
        if self.value.startswith('global '):
            out = self.app.settings.process_command(self.value)
            self.screen.draw(out)
        elif self.value.strip() == 'help':
            out = self.screen.print_help()
        elif out := self.screen.context.on_enter(self.value):
            self.screen.draw(out)
        self.screen.query_one('#ws-sections-list', LeftSidebar).clear()
        self.screen.query_one('#ws-path-line', PathBar).update_path()
        self.value = ''
        super().action_submit()

    async def on_input_changed(self, message: Input.Changed) -> None:
        if not self.value:
            self.screen.query_one('#ws-sections-list', LeftSidebar).update('show |')
        self.screen.query_one('#ws-sections-list', LeftSidebar).update(message.value)

    def _on_key(self, event: Key) -> None:
        if event.key == 'space':
            if self.value:
                if self.value[-1] == ' ':
                    self.value = self.value[:-1]
        elif event.key == 'tab':
            if self.value:
                if self.cursor_position == len(self.value):
                    control = self.screen.query_one('#ws-sections-list', LeftSidebar)
                    self.value = control.get_replacement(self.value)
                    self.cursor_position = len(self.value)
                event.stop()
        elif event.key == 'up':
            if self.app.settings.is_bool_set('sidebar_strict_on_tab'):
                self.screen.query_one('#ws-main-out', ExtendedTextLog).action_scroll_up()
            else:
                if self.value:
                    self.screen.query_one('#ws-sections-list', LeftSidebar).action_cursor_up()
                else:
                    self.screen.query_one('#ws-main-out', ExtendedTextLog).action_scroll_up()
        elif event.key == 'down':
            if self.app.settings.is_bool_set('sidebar_strict_on_tab'):
                self.screen.query_one('#ws-main-out', ExtendedTextLog).action_scroll_down()
            else:
                if self.value:
                    self.screen.query_one('#ws-sections-list', LeftSidebar).action_cursor_down()
                else:
                    self.screen.query_one('#ws-main-out', ExtendedTextLog).action_scroll_down()
        super()._on_key(event)
