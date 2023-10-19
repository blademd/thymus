from __future__ import annotations

from re import MULTILINE, IGNORECASE
from typing import Any
from pygments.lexer import RegexLexer, bygroups  # type: ignore
from pygments.token import (  # type: ignore
    Generic,
    Whitespace,
    Keyword,
    Comment,
    _TokenType,
)


def wr(
    reg_exp: str,
    *args: tuple[_TokenType, ...],
    **kwargs: Any
) -> tuple[Any, ...]:
    if 'stage' in kwargs and kwargs['stage']:
        if len(args) > 1:
            return reg_exp, bygroups(*args), kwargs['stage']
        else:
            return reg_exp, *args, kwargs['stage']
    else:
        if len(args) > 1:
            return reg_exp, bygroups(*args)
        else:
            return reg_exp, *args


class SyslogLexer(RegexLexer):
    tokens = {
        'root': [
            # DATE
            wr(
                r'^\d{4}(?:-\d{2}){2}\s+',
                Whitespace,
                stage='#push'
            ),
            # TIME
            wr(
                r'\d{2}(?::\d{2}){2},\d+\s+',
                Whitespace,
                stage='#push'
            ),
            # NAME
            wr(
                r'[a-z][a-z0-9-_\.]+\s+',
                Keyword,
                stage='#push'
            ),
            # DEBUG
            wr(
                r'DEBUG\s',
                Generic.DEBUG,
                stage='#push'
            ),
            # INFO
            wr(
                r'INFO\s',
                Generic.INFO,
                stage='#push'
            ),
            # WARNING
            wr(
                r'WARNING\s',
                Generic.WARNING,
                stage='#push'
            ),
            # ERROR
            wr(
                r'ERROR\s',
                Generic.ERROR,
                stage='#push'
            ),
            # CRITICAL
            wr(
                r'CRITICAL\s',
                Generic.CRITICAL,
                stage='#push'
            ),
            # THE REST
            wr(
                r'[^\n]+\n',
                Comment
            )
        ]
    }

class CommonLexer(RegexLexer):
    flags = IGNORECASE | MULTILINE
    tokens = {
        'root': [
            # DIFF/COMPARE +
            (
                r'(\s*)(\+)(\s)(.+\n)',
                bygroups(
                    Whitespace,
                    Generic.Inserted,
                    Whitespace,
                    Generic.Inserted
                )
            ),
            # DIFF/COMPARE -
            (
                r'(\s*)(-)(\s)(.+\n)',
                bygroups(
                    Whitespace,
                    Generic.Deleted,
                    Whitespace,
                    Generic.Deleted
                )
            ),
            # DIFF/COMPARE ?
            (
                r'(\s*)(\?)(.+\n)',
                bygroups(
                    Whitespace,
                    Comment,
                    Comment
                )
            ),
            # THE REST
            (
                r'.+',
                Keyword
            ),
        ],
    }
