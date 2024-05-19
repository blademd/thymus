from __future__ import annotations


from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Label
from textual.widget import Widget
from textual.containers import Horizontal
from textual.message import Message


class EditorOverlay(Widget):
    # Kudos the toolong project :)

    class Stop(Message): ...

    DEFAULT_CSS = """
    EditorOverlay {
        display: none;
        dock: bottom;
        layer: overlay;
        width: 1fr;
        visibility: hidden;
        offset-y: -1;
        text-style: bold;
    }

    EditorOverlay Horizontal {
        width: 1fr;
        align: center bottom;
    }

    EditorOverlay Label {
        visibility: visible;
        width: auto;
        height: 1;
        background: $panel;
        color: $success;
        padding: 0 1;

        &:hover {
            background: $success;
            color: auto 90%;
            text-style: bold;
        }
    }
    """

    message = reactive('')

    def compose(self) -> ComposeResult:
        self.tooltip = 'Click here to stop'

        with Horizontal():
            yield Label('')

    def watch_message(self, message: str) -> None:
        self.display = bool(message.strip())
        self.query_one(Label).update(message)

    def on_click(self) -> None:
        self.message = ''
        self.post_message(EditorOverlay.Stop())
