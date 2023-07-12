from __future__ import annotations

from pygments.lexer import RegexLexer
from pygments.token import (
    Text,
    Whitespace,
    Comment,
    Keyword,
    Name,
    Number,
    Generic,
)

from ..common.common import wr
from ..common.regexps import IPV4_REGEXP, IPV6_REGEXP


class IOSLexer(RegexLexer):
    tokens = {
        'root': [
            # DIFF/COMPARE +
            wr(
                r'(\s*)(\+)(\s)(.+)(\n)',
                Whitespace,
                Generic.Inserted,
                Whitespace,
                Generic.Inserted,
                Whitespace
            ),
            # DIFF/COMPARE -
            wr(
                r'(\s*)(-)(\s)(.+)(\n)',
                Whitespace,
                Generic.Deleted,
                Whitespace,
                Generic.Deleted,
                Whitespace
            ),
            # DIFF/COMPARE ?
            wr(
                r'(\s*)(\?)(.+)(\n)',
                Whitespace,
                Comment,
                Comment,
                Whitespace
            ),
            # COMMENT WITH "!"
            wr(
                r'(\s*)(\!(?:[^\n]+)?)(\n)',
                Whitespace,
                Comment,
                Whitespace
            ),
            # SPECIAL: VERSION
            wr(
                r'(version)(\s)([^\n]+)(\n)',
                Keyword,
                Whitespace,
                Number,
                Whitespace
            ),
            # SPECIAL: HOSTNAME
            wr(
                r'(hostname)(\s)([^\n]+)(\n)',
                Keyword,
                Whitespace,
                Text,
                Whitespace
            ),
            # SPECIAL: DESCRIPTION
            wr(
                r'(\s*)(description)(\s)([^\n]+)(\n)',
                Whitespace,
                Keyword,
                Whitespace,
                Text,
                Whitespace
            ),
            # SPECIAL: INTERFACE
            wr(
                r'(\s*)(interface)(\s)([^\n]+)(\n)',
                Whitespace,
                Keyword,
                Whitespace,
                Keyword.Type,
                Whitespace
            ),
            # SPECIAL: SHUTDOWN
            wr(
                r'(\s*)(shutdown)(\n)',
                Whitespace,
                Name.Constant,
            ),
            # SPECIAL: NO INSTRUCTION
            wr(
                r'(\s*)(no)(?=\s)',
                Whitespace,
                Name.Constant,
                stage='stager'
            ),
            # REGULAR INSTRUCTION
            wr(
                r'(\s*)([^\n\s]+)',
                Whitespace,
                Keyword,
                stage='stager'
            )
        ],
        'stager': [
            # DOT EXCEPTION
            wr(
                r'(\s+)(\.\n)',
                Whitespace,
                Name.Tag,
            ),
            # IPV4 RD/RT
            wr(
                rf'(\s+)({IPV4_REGEXP}:)(\d+)(?=\s|\n)',
                Whitespace,
                Whitespace,
                Number,
                stage='#push'
            ),
            # IPV6 RD/RT
            wr(
                rf'(\s+)({IPV6_REGEXP}:)(\d+)(?=\s|\n)',
                Whitespace,
                Whitespace,
                Number,
                stage='#push'
            ),
            # IPV4 PREFIX OR ADDRESS
            wr(
                rf'(\s+)({IPV4_REGEXP}(?:\/\d{1,2})?)(?=\s|\n)',
                Whitespace,
                Whitespace,
                stage='#push'
            ),
            # IPV6 PREFIX OR ADDRESS
            wr(
                rf'(\s+)({IPV6_REGEXP}(?:\/\d{1,2})?)(?=\s|\n)',
                Whitespace,
                Whitespace,
                stage='#push'
            ),
            # NUMERIC RD/RT
            wr(
                r'(\s+)(\d+)(:)(\d+)(?=\s|\n)',
                Whitespace,
                Number,
                Text,
                Number,
                stage='#push'
            ),
            # MAC ADDRESS IN A PECULIAR NOTATION
            wr(
                r'(\s+)((?:[a-f0-9]{4}\.){2}[a-f0-9]{4})',
                Whitespace,
                Whitespace,
                stage='#push'
            ),
            # LINKS
            wr(
                r'(\s+)([a-z0-9-_/]+\.(?:[a-z0-9-_/]+\.)*[a-z0-9-]+)(?=\s|\n)',
                Whitespace,
                Name.Tag,
                stage='#push',
            ),
            # HASH
            wr(
                r'(\s+)([A-F0-9]+)(?=\s|\n)',
                Whitespace,
                Number,
                stage='#push'
            ),
            # SPECIAL: REMARK
            wr(
                r'(\s+)(remark)(\s+)([^\n]+)(\n)',
                Whitespace,
                Keyword,
                Whitespace,
                Comment,
                Whitespace
            ),
            # SPECIAL: DESCRIPTION
            wr(
                r'(\s+)(description)(\s+)([^\n]+)(\n)',
                Whitespace,
                Keyword,
                Whitespace,
                Text,
                Whitespace
            ),
            # REGULAR KEYWORD
            wr(
                r'(?i)(\s+)([a-z][a-z0-9-]+)(?=\s|\n)',
                Whitespace,
                Keyword,
                stage='#push'
            ),
            # NUMBER
            wr(
                r'(\s+)(\d+)(?=\s|\n)',
                Whitespace,
                Number,
                stage='#push'
            ),
            # QUOTED LINE
            wr(
                r'(\s+)("[^"]+")(?=\s|\n)',
                Whitespace,
                Text,
                stage="#push"
            ),
            # THE REST
            wr(
                r'\s+[^\s\n]+',
                Keyword,
                stage='#push'
            ),
            # EOL
            wr(
                r'\s*\n',
                Comment
            )
        ],
    }
