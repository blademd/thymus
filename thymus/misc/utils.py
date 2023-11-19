from __future__ import annotations


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
