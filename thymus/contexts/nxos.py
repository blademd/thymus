from __future__ import annotations

from collections import deque
from copy import copy
from logging import Logger

from thymus.responses import Response

from . import IOSContext
from ..responses import AlertResponse


class NXOSContext(IOSContext):
    @property
    def nos_type(self) -> str:
        return 'NXOS'

    def __init__(
        self,
        name: str,
        content: list[str],
        *,
        encoding: str,
        settings: dict[str, str | int],
        logger: Logger,
    ) -> None:
        settings['promisc'] = 1
        super().__init__(name, content, encoding=encoding, settings=settings, logger=logger)

    def command_set(self, args: deque[str]) -> Response:
        if args:
            xargs = copy(args)
            command = xargs.popleft()
            command = command.lower()
            if command == 'promisc':
                return AlertResponse.error(f'The command "set {command}" is not supported for {self.nos_type}!')
        return super().command_set(args)
