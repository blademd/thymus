from __future__ import annotations
from random import random
from textual.widgets import TextLog


class ExtendedTextLog(TextLog):
    def on_mouse_scroll_down(self) -> None:
        if random() <= 0.25:
            self.screen.draw()
