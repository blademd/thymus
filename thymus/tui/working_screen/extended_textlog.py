from __future__ import annotations

from random import random

from textual.widgets import RichLog


class ExtendedTextLog(RichLog):
    def on_mouse_scroll_down(self) -> None:
        if random() <= 0.25:
            self.screen.draw()
