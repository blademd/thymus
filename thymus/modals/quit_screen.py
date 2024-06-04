from __future__ import annotations


from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Grid


class QuitScreen(ModalScreen[bool]):
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Grid(id='quit-screen-dialog'):
            yield Label(self.message, id='quit-screen-question')
            yield Button('Cancel', variant='primary', id='quit-screen-cancel-button')
            yield Button('Close', variant='error', id='quit-screen-close-button')

    @on(Button.Pressed, '#quit-screen-close-button')
    def on_close_screen(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, '#quit-screen-cancel-button')
    def on_cancel(self) -> None:
        self.dismiss(False)
