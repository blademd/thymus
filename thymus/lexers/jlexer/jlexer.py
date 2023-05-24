from __future__ import annotations

from ..common.regexps import IPV4_REGEXP, IPV6_REGEXP

from pygments.lexer import RegexLexer, bygroups
from pygments.token import (
    Text,
    Generic,
    Whitespace,
    Comment,
    Keyword,
    Name,
    Operator,
    Number,
)

from re import MULTILINE, IGNORECASE


class JunosLexer(RegexLexer):
    flags = IGNORECASE | MULTILINE
    tokens = {
        'root': [
            # STANDALONE COMMENT
            (
                r'(\s*)(##? [^\n]+)',
                bygroups(
                    Whitespace,
                    Comment
                )
            ),
            # STANDALONE ANNOTATION
            (
                r'(\s*)(/\*[^\*]+\*/)(\n)',
                bygroups(
                    Whitespace,
                    Comment,
                    Operator.Word
                )
            ),
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
            # INACTIVE
            (
                r'(\s*)(inactive: )(?=[^\n;\s])',
                bygroups(
                    Whitespace,
                    Name.Constant
                ),
                '#push'
            ),
            # PROTECTED
            (
                r'(\s*)(protected: )(?=[^\n;\s])',
                bygroups(
                    Whitespace,
                    Whitespace
                ),
                '#push'
            ),
            # SPECIAL: DESCRIPTION
            (
                r'(\s*)(description)(\s)(.+)(;\n)',
                bygroups(
                    Whitespace,
                    Keyword,
                    Whitespace,
                    Text,
                    Operator.Word
                )
            ),
            # SPECIAL: DISABLE
            (
                r'(\s*)(disable)(;\n)',
                bygroups(
                    Whitespace,
                    Name.Constant,
                    Operator.Word
                )
            ),
            # HANDLING TOKENS THROUGH THE STAGER
            # IPV4 STAGER
            (
                fr'(\s*)({IPV4_REGEXP})',
                bygroups(
                    Whitespace,
                    Whitespace
                ),
                'stager'
            ),
            # IPV6 STAGER
            (
                rf'(\s*)({IPV6_REGEXP})',
                bygroups(
                    Whitespace,
                    Whitespace
                ),
                'stager'
            ),
            # "TEXT"
            (
                r'(\s*)((?<=\s)".+"(?=;|\s))',
                bygroups(
                    Whitespace,
                    Text
                ),
                'stager'
            ),
            # NUMBER OR BANDWIDTH
            (
                r'(\s*)(\d+[mkg]?)(;\n)',
                bygroups(
                    Whitespace,
                    Number,
                    Operator.Word
                )
            ),
            # THE REST (REGULAR)
            (
                r'(\s*)([a-z0-9-_\./\*,$]+)',
                bygroups(
                    Whitespace,
                    Keyword
                ),
                'stager'
            ),
            # END OF A SECTION (WITH A POSSIBLE INLINE COMMENT)
            (
                r'(\s*)(\})(\s##\s[^\n]+)?(\n)',
                bygroups(
                    Whitespace,
                    Operator.Word,
                    Comment,
                    Whitespace
                )
            ),
        ],
        'stager': [
            # ASTERISK SECTIONS (e.g., unit *)
            (
                r'(\s)(\*)',
                bygroups(
                    Whitespace,
                    Keyword
                ),
                '#push'
            ),
            # START OF A SQUARE BLOCK
            (
                r'(\s)(\[)(\s)',
                bygroups(
                    Whitespace,
                    Operator.Word,
                    Whitespace
                ),
                '#push'
            ),
            # IPV4 ADDRESS OR PREFIX
            (
                rf'(\s)?({IPV4_REGEXP})',
                bygroups(
                    Whitespace,
                    Whitespace
                ),
                '#push'
            ),
            # IPV6 ADDRESS OR PREFIX
            (
                rf'(\s)?({IPV6_REGEXP})',
                bygroups(
                    Whitespace,
                    Whitespace
                ),
                '#push'
            ),
            # NUMBER OF BANDWIDTH
            (
                r'(\s)?(\d+[mkg]?(?=;|\s))',
                bygroups(
                    Whitespace,
                    Number
                ),
                '#push'
            ),
            # LINKS, IFLS, RIBS, etc.
            (
                r'(\s)?([a-z0-9-_/]+\.(?:[a-z0-9-_/]+\.)*[a-z0-9-]+)',
                bygroups(
                    Whitespace,
                    Name.Tag
                ),
                '#push'
            ),
            # "TEXT" (NOT GREEDY)
            (
                r'(\s*)((?<=\s)".+?"(?=;|\s))',
                bygroups(
                    Whitespace,
                    Text
                ),
                '#push'
            ),
            # "TEXT" IN A SQUARES BLOCK
            (
                r'(\s*)("[^"]+")(\s)',
                bygroups(
                    Whitespace,
                    Text,
                    Whitespace
                ),
                '#push'
            ),
            # INLINE ANNOTATIONS
            (
                r'(\s)?(/\*[^\*]+\*/)(?:(\s)(\}))?',
                bygroups(
                    Whitespace,
                    Comment,
                    Whitespace,
                    Operator.Word
                ),
                '#push'
            ),
            # THE REST (REGULAR)
            (
                r'(\s)?([a-z0-9-_\./+=\*:^&$,]+)',
                bygroups(
                    Whitespace,
                    Keyword.Type
                ),
                '#push'
            ),
            # BEGIN OF A SECTION (WITH A POSSIBLE INLINE COMMENT)
            (
                r'(\s)?(\{)(\s##\s[^\n]+)?',
                bygroups(
                    Whitespace,
                    Operator.Word,
                    Comment
                ),
                '#pop'
            ),
            # END OF A SQUARE BLOCK (WITH A POSSIBLE INLINE COMMENT)
            (
                r'(\s)?(\]?;)(\s##\s[^\n]+)?',
                bygroups(
                    Whitespace,
                    Operator.Word,
                    Comment
                ),
                '#pop'
            ),
        ],
    }
