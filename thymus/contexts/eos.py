from __future__ import annotations

from . import IOSContext

class EOSContext(IOSContext):
    def __init__(self, name: str, content: list[str], encoding: str = 'utf-8-sig') -> None:
        super().__init__(name, content, encoding)
        self.spaces = 2

    @property
    def nos_type(self) -> str:
        return 'EOS'
