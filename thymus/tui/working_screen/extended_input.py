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
            self.screen.print_help()
        elif out := self.screen.context.on_enter(self.value):
            self.screen.draw(out)
        self.screen.query_one('#ws-sections-list', LeftSidebar).clear()
        self.screen.query_one('#ws-path-line', PathBar).update_path()
        self.value = ''
        super().action_submit()

    async def on_input_changed(self, message: Input.Changed) -> None:
        param = 'go |'
        sidebar = self.screen.query_one('#ws-sections-list', LeftSidebar)
        if self.value:
            param = message.value
            # pipe here is for the auto-filling of the left sidebar
            if message.value[-1] == ' ':
                param += '|'
        sidebar.update(param)

    def _on_key(self, event: Key) -> None:
        sidebar = self.screen.query_one('#ws-sections-list', LeftSidebar)
        textlog = self.screen.query_one('#ws-main-out', ExtendedTextLog)
        if event.key == 'tab':
            if self.value:
                if self.cursor_position == len(self.value):
                    # cursor is at the end of the input
                    repl = sidebar.get_replacement(self.value)
                    if repl != self.value:
                        if repl[-1] != ' ' and len(sidebar.children) == 1:
                            # add space to trigger the leftsidebar's update
                            # implicitly calls the on_input_changed
                            repl += ' '
                        self.value = repl
                        self.cursor_position = len(self.value)
                event.stop()
        elif event.key == 'up':
            if self.app.settings.is_bool_set('sidebar_strict_on_tab'):
                textlog.action_scroll_up()
            else:
                if self.value:
                    sidebar.action_cursor_up()
                else:
                    textlog.action_scroll_up()
        elif event.key == 'down':
            if self.app.settings.is_bool_set('sidebar_strict_on_tab'):
                textlog.action_scroll_down()
            else:
                if self.value:
                    sidebar.action_cursor_down()
                else:
                    textlog.action_scroll_down()
        elif event.key == 'ctrl+up':
            if self.screen.context and (prev_cmd := self.screen.context.get_input_from_log()):
                self.value = prev_cmd
                self.cursor_position = len(self.value)
        elif event.key == 'ctrl+down':
            if self.screen.context and (next_cmd := self.screen.context.get_input_from_log(forward=False)):
                self.value = next_cmd
                self.cursor_position = len(self.value)
        super()._on_key(event)
