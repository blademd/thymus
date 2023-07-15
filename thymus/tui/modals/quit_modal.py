from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label


if TYPE_CHECKING:
    from typing import Optional

    from textual.app import ComposeResult

    from ...tuier import TThymus
    from ..working_screen.working_screen import WorkingScreen


class QuitApp(ModalScreen):
    def compose(self) -> ComposeResult:
        with Grid(id='qs-dialog'):
            yield Label('Are you sure you want to quit [b]Thymus[/b]?', id='qs-question')
            yield Button('Quit', variant='error', id='qs-quit')
            yield Button('Cancel', variant='primary', id='qs-cancel')

    def on_show(self) -> None:
        self.query_one('#qs-cancel', Button).focus()

    @on(Button.Pressed, '#qs-quit')
    def quit_app(self) -> None:
        self.app.logger.info('Thymus stopped.')
        self.app.exit()

    @on(Button.Pressed, '#qs-cancel')
    def cancel(self) -> None:
        self.app.pop_screen()

class QuitScreen(ModalScreen):
    app: TThymus

    def __init__(
        self,
        screen: WorkingScreen,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None
    ) -> None:
        super().__init__(name, id, classes)
        self.screen_to_quit: WorkingScreen = screen

    def compose(self) -> ComposeResult:
        with Grid(id='qs-dialog'):
            yield Label('Close this context?', id='qs-question')
            yield Button('Close', variant='error', id='qs-quit')
            yield Button('Cancel', variant='primary', id='qs-cancel')

    def on_show(self) -> None:
        self.query_one('#qs-cancel', Button).focus()

    @on(Button.Pressed, '#qs-quit')
    def quit_screen(self) -> None:
        m = f'File "{self.screen_to_quit.filename}" for the platform "{self.screen_to_quit.nos_type}" was closed.'
        self.app.logger.info(m)
        self.app.pop_screen()  # for itself
        self.app.pop_screen()  # for a WorkingScreen instance
        if self.screen_to_quit.name in self.app.working_screens:
            self.app.working_screens.remove(self.screen_to_quit.name)
        self.app.uninstall_screen(self.screen_to_quit)
        self.screen_to_quit.context.free()

    @on(Button.Pressed, '#qs-cancel')
    def cancel(self) -> None:
        self.app.pop_screen()
