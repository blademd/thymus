from __future__ import annotations

from logging import Logger

from . import IOSContext


class EOSContext(IOSContext):
    @property
    def nos_type(self) -> str:
        return 'EOS'

    def __init__(
        self, name: str, content: list[str], *, encoding: str, settings: dict[str, str | int], logger: Logger
    ) -> None:
        super().__init__(name, content, encoding=encoding, settings=settings, logger=logger)
