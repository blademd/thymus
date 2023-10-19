from __future__ import annotations

from typing import TYPE_CHECKING
from logging.handlers import BufferingHandler
from pygments.token import (  # type: ignore
    Whitespace,
    Keyword,
    Generic,
    Comment,
)

from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import RichLog
from rich.text import Text
from rich.syntax import Syntax, ANSISyntaxTheme
from rich.style import Style

from ...lexers import SyslogLexer


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from ...tuier import TThymus

SYSLOG_DARK_STYLES = {
    Whitespace: Style(color='white'),
    Keyword: Style(color='yellow'),
    Comment: Style(color='bright_white'),
    Generic.DEBUG: Style(color='blue', bold=True),
    Generic.INFO: Style(color='green', bold=True),
    Generic.WARNING: Style(color='yellow', bold=True),
    Generic.ERROR: Style(color='red', bold=True),
    Generic.CRITICAL: Style(color='bright_red', bold=True),
}
SYSLOG_LIGHT_STYLES = {
    Whitespace: Style(color='black'),
    Keyword: Style(color='yellow'),
    Comment: Style(color='black'),
    Generic.DEBUG: Style(color='blue', bold=True),
    Generic.INFO: Style(color='green', bold=True),
    Generic.WARNING: Style(color='yellow', bold=True),
    Generic.ERROR: Style(color='red', bold=True),
    Generic.CRITICAL: Style(color='bright_red', bold=True),
}


class LogsScreen(ModalScreen):
    app: TThymus

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Quit'),
    ]

    def compose(self) -> ComposeResult:
        with Container():
            yield RichLog(id='lm-log')

    def on_show(self) -> None:
        control = self.query_one(RichLog)
        control.write(Text('Current log (Esc to quit):', style='green italic'))
        lexer = SyslogLexer()
        theme = ANSISyntaxTheme(SYSLOG_DARK_STYLES)
        if not self.app.dark:
            theme = ANSISyntaxTheme(SYSLOG_LIGHT_STYLES)
        if not self.app.logger:
            return
        for handler in self.app.logger.handlers:
            if type(handler) is not BufferingHandler:
                continue
            for record in handler.buffer:
                try:
                    line = f'{record.asctime} {record.module} {record.levelname} {record.message}'
                    syntax = Syntax(line, lexer=lexer, theme=theme, code_width=len(line) + 2)
                    control.write(syntax)
                except Exception:
                    line = f'{record.module} {record.levelname} {record.msg}'
                    syntax = Syntax(line, lexer=lexer, theme=theme, code_width=len(line) + 2)
                    control.write(syntax)
