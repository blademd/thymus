from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from textual import on
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label


if TYPE_CHECKING:
    from textual.app import ComposeResult


class ErrorScreen(ModalScreen):
    BINDINGS = [
        ('escape', 'app.pop_screen()', 'Cancel'),
    ]

    def __init__(
        self,
        err_msg: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None
    ) -> None:
        super().__init__(name, id, classes)
        self.err_msg = err_msg

    def compose(self) -> ComposeResult:
        with Grid(id='qs-dialog'):
            yield Label(self.err_msg, id='es-err-msg')
            yield Button('Close', variant='error', id='es-quit')

    def on_show(self) -> None:
        self.query_one('#es-quit', Button).focus()

    @on(Button.Pressed, '#es-quit')
    def cancel(self) -> None:
        self.app.pop_screen()
