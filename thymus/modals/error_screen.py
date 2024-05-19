from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ErrorScreen(ModalScreen):
    BINDINGS = [
        ('escape', 'dismiss', 'Dismiss'),
    ]

    def __init__(self, err_msg: str) -> None:
        super().__init__()
        self._err_msg = err_msg

    def compose(self) -> ComposeResult:
        with Grid(id='error-screen-grid'):
            yield Label(self._err_msg, classes='error-screen-center')
            yield Button('Quit', variant='error', id='error-screen-quit', classes='error-screen-center')

    def on_show(self) -> None:
        self.query_one(Button).focus()

    @on(Button.Pressed, '#error-screen-quit')
    def quit(self) -> None:
        self.dismiss()
