from __future__ import annotations

import re


def find_common(elems: list[str]) -> str:
    result = ''
    min_len = min(len(x) for x in elems)
    for step in range(min_len):
        char = elems[0][step]
        if all(s[step].lower() == char.lower() for s in elems):
            result += char
        else:
            return result
    return result


def rreplace(line: str, pattern: str, replacement: str, count: int = 1) -> str:
    return replacement.join(line.rsplit(pattern.lstrip(), count))


def dot_notation_fix(value: str) -> str:
    value = value.lower()
    pattern = '([a-z][-a-z0-9/]*)\.(\d+)'
    if re_match := re.search(re.escape(pattern), value, re.IGNORECASE):
        ifd = re_match.group(1)
        ifl = re_match.group(2)
        value = value.replace(ifd + '.' + ifl, ifd + ' unit ' + ifl)
    return value


def get_spaces(line: str) -> int:
    if m := re.search(r'^(\s+)', line):
        return len(m.group(1))
    return 0
