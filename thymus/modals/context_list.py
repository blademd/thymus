from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option, Separator

from thymus.working_screen import WorkingScreen


class ContextListScreen(ModalScreen):
    BINDINGS = [
        ('escape', 'dismiss', 'Dismiss'),
    ]

    def __init__(self, screens: list[WorkingScreen]) -> None:
        super().__init__()
        self.working_screens = screens

    def compose(self) -> ComposeResult:
        yield OptionList(
            Option('Please, select a context below (press Escape to dismiss):'),
            Separator(),
        )

    def on_show(self) -> None:
        control = self.query_one(OptionList)

        header = control.get_option_at_index(0)
        header.disabled = True

        for screen in self.working_screens:
            try:
                if screen.shortcut.name:
                    line = f'{screen.platform_name.upper()}: {screen.shortcut.name} ({screen.source})'
                else:
                    line = f'{screen.platform_name.upper()}: {screen.path} ({screen.source})'
                control.add_option(Option(line, id=screen.name))

            except Exception:
                ...

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        screen = event.option.id
        assert screen

        self.app.pop_screen()  # pops itself

        if len(self.app.screen_stack) == 1:
            self.app.push_screen(screen)
        else:
            self.app.switch_screen(screen)
