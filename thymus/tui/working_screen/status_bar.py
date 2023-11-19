from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Static


if TYPE_CHECKING:
    from textual.geometry import Size

    from ...tuier import TThymus
    from .working_screen import WorkingScreen

LINE_NAMED = '{NOS}  Context:_{CONTEXT}  Spaces:_{SPACES}  Lines:_{LINES}  Theme:_{THEME}  {ENCODING}  {FILENAME}'
LINE_UNNAMED = '{NOS}  Spaces:_{SPACES}  Lines:_{LINES}  Theme:_{THEME}  {ENCODING}  {FILENAME}'


class StatusBar(Static, can_focus=False):
    app: TThymus
    screen: WorkingScreen

    def update_bar(self) -> None:
        if not self.screen.context:
            return
        status: str = ''
        filename = self.screen.filename
        filename_limit = int(self.app.settings.current_settings['filename_len'])
        theme = str(self.app.settings.current_settings['theme'])
        if len(filename) > (filename_limit - max(3, int(filename_limit * 0.1))):
            filename = f'...{filename[-filename_limit:]}'
        if context_name := self.screen.context.name:
            status = LINE_NAMED.format(
                NOS=self.screen.nos_type.upper(),
                CONTEXT=context_name,
                SPACES=self.screen.context.spaces,
                LINES=len(self.screen.context.content),
                THEME=theme.upper(),
                ENCODING=self.screen.encoding.upper(),
                FILENAME=filename,
            )
        else:
            status = LINE_UNNAMED.format(
                NOS=self.screen.nos_type.upper(),
                SPACES=self.screen.context.spaces,
                LINES=len(self.screen.context.content),
                THEME=theme.upper(),
                ENCODING=self.screen.encoding.upper(),
                FILENAME=filename,
            )
        while len(status) > self.size.width:
            parts = status.split()
            status = '  '.join(parts[:-1])
        self.update(status.replace('_', ' '))

    def watch_virtual_size(self, prev: Size, new: Size) -> None:
        self.update_bar()
