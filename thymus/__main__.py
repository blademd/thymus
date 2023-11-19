from __future__ import annotations

import sys

from . import __version__ as app_ver
from . import tuier
from . import clier


HELP_MESSAGE = """There are two possible options to run the Application:
* -- run the Terminal User Interface version:
** -- python -m thymus
** -- python -m thymus tuier

* -- run the Command Line Interface version:
** -- python -m thymus clier
"""


def run_tui() -> None:
    app = tuier.TThymus()
    app.run()


def run_cli() -> None:
    try:
        clier.main()
    except KeyboardInterrupt:
        pass


def help() -> None:
    print(HELP_MESSAGE)


def main(args: list[str]) -> None:
    if len(args) > 1:
        if args[1] == 'clier':
            run_cli()
        elif args[1] == 'tuier':
            run_tui()
        elif args[1] == 'version' or args[1] == 'ver':
            print(f'Thymus ver. {app_ver}')
        else:
            help()
    else:
        run_tui()


if __name__ == '__main__':
    main(sys.argv)
