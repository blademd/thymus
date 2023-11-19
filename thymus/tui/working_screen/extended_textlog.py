from __future__ import annotations

from random import random
from typing import TYPE_CHECKING

from textual.widgets import RichLog


if TYPE_CHECKING:
    from .working_screen import WorkingScreen


class ExtendedTextLog(RichLog):
    screen: WorkingScreen

    def on_mouse_scroll_down(self) -> None:
        if random() <= 0.25:
            self.screen.draw()
