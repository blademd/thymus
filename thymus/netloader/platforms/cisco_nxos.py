from __future__ import annotations

import re

from thymus.netloader.platforms import CiscoIOS


class CiscoNXOS(CiscoIOS):
    @staticmethod
    def normalize_lines(data: str) -> str:
        new_line = re.compile(r'(\r\r\n|\r\n)')
        return new_line.sub('\n', data).replace('\r', '')
