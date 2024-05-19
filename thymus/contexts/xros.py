from __future__ import annotations

from collections import deque
from copy import copy

from thymus.contexts import IOSContext
from thymus.responses import Response
from thymus.lexers import CommonLexer


class XROSContext(IOSContext):
    lexer = CommonLexer

    def command_set(self, args: deque[str]) -> Response:
        if args:
            xargs = copy(args)

            command = xargs.popleft()
            command = command.lower()

            if command == 'promisc':
                return Response.error('The command "set promisc" is not supported!')

        return super().command_set(args)
