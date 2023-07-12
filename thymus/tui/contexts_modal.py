from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option, Separator


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from ..tuier import TThymus


class ContextListScreen(ModalScreen):
    app: TThymus

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Quit'),
    ]

    def compose(self) -> ComposeResult:
        yield OptionList(
            Option('Please, select a context to work with (Esc to quit):', id='cm-title'),
            Separator(),
            id='cm-options'
        )

    def on_show(self) -> None:
        control = self.query_one(OptionList)
        header = control.get_option_at_index(0)
        header.disabled = True
        for screen_name in self.app.working_screens:
            screen = self.app.get_screen(screen_name)
            if hasattr(screen, 'filename') and hasattr(screen, 'nos_type'):
                control.add_option(Option(f'{screen.nos_type.upper()}: {screen.filename}', id=screen.name))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        screen = event.option.id
        self.app.pop_screen()  # pops itself
        if len(self.app.screen_stack) == 1:
            self.app.push_screen(screen)
        else:
            self.app.switch_screen(screen)  # pushes selected one
        self.app.logger.debug(f'Switched to screen: {screen}. Screen stack depth: {len(self.app.screen_stack)}.')
        for screen_name in self.app.screen_stack:
            self.app.logger.debug(f'Screen name: {str(screen_name.name)}, id: {str(screen_name.id)}.')
