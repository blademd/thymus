from __future__ import annotations

from textual.widgets import RichLog


class Viewer(RichLog):
    def enter_view(self) -> None:
        self.clear()
        self.styles.display = 'block'

    def exit_view(self) -> None:
        self.styles.display = 'none'
        self.clear()
