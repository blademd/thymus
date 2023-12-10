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
        content.insert(0, 'version ')  # mimics to IOS-like
        super().__init__(name, content, encoding=encoding, settings=settings, logger=logger)
        self.content[0] = '!'
        self.tree.stubs.remove('version')

    def _rebuild_tree(self) -> None:
        if self.content and self.content[0] == '!':
            self.content.pop(0)
        self.content.insert(0, 'version ')
        super()._rebuild_tree()
        self.content[0] = '!'
        self.tree.stubs.remove('version')
