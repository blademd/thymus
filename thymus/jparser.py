import re

Content = dict[str, list[str]]

def parser(data: list[str], path: str, delimiter='>') -> tuple[list[str], list[str]]:
    sections = []
    params = []
    container = []
    parts = path.split(delimiter)
    plen = len(parts)
    for line in data:
        stripped = line.strip()
        if '{' in stripped and ';' not in stripped:
            sections.append(stripped)
        elif '}' in stripped and ';' not in stripped:
            sections.pop()
        elif ';' in line:
            if parts == [x[:-2] for x in sections]:
                params.append(stripped)
        if parts == [x[:-2] for x in sections[:plen]]:
            container.append(stripped)
    if container:
        container.append('}')
    return container, params

def wc_parser(data: list[str], path: str, pattern: str, delimiter='>') -> tuple[Content, Content]:
    sections = []
    container: Content = {}
    params: Content = {}
    parts = path.split(delimiter)
    plen = len(parts)
    for line in data:
        stripped = line.strip()
        if '{' in stripped and ';' not in stripped:
            sections.append(stripped)
            if parts == [x[:-2] for x in sections[:-1]]:
                if re.match(pattern, sections[-1], re.I):
                    key = sections[-1][:-2]
                    container[key] = []
                    params[key] = []
        elif '}' in stripped and ';' not in stripped:
            if parts == [x[:-2] for x in sections[:-1]]:
                if re.match(pattern, sections[-1], re.I):
                    key = sections[-1][:-2]
                    if r := container.get(key):
                        r.append('}')
            sections.pop()
        elif ';' in line:
            if len(sections) == plen + 1 and \
                parts == [x[:-2] for x in sections[:plen]] and \
                    re.match(pattern, sections[plen], re.I):
                key = sections[plen][:-2]
                params[key].append(stripped)
        if parts == [x[:-2] for x in sections[:plen]]:
            if len(sections) > plen and re.match(pattern, sections[plen], re.I):
                container[sections[plen][:-2]].append(stripped)
    return container, params
