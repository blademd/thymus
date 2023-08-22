__version__ = '0.1.3.f1.e3-alpha'

CONFIG_PATH = 'thymus/settings/'
CONFIG_NAME = 'thymus.json'
WELCOME_TEXT = '''\
▄▄▄█████▓ ██░ ██▓██   ██▓ ███▄ ▄███▓ █    ██   ██████
▓  ██▒ ▓▒▓██░ ██▒▒██  ██▒▓██▒▀█▀ ██▒ ██  ▓██▒▒██    ▒
▒ ▓██░ ▒░▒██▀▀██░ ▒██ ██░▓██    ▓██░▓██  ▒██░░ ▓██▄
░ ▓██▓ ░ ░▓█ ░██  ░ ▐██▓░▒██    ▒██ ▓▓█  ░██░  ▒   ██▒
  ▒██▒ ░ ░▓█▒░██▓ ░ ██▒▓░▒██▒   ░██▒▒▒█████▓ ▒██████▒▒
  ▒ ░░    ▒ ░░▒░▒  ██▒▒▒ ░ ▒░   ░  ░░▒▓▒ ▒ ▒ ▒ ▒▓▒ ▒ ░
    ░     ▒ ░▒░ ░▓██ ░▒░ ░  ░      ░░░▒░ ░ ░ ░ ░▒  ░ ░
  ░       ░  ░░ ░▒ ▒ ░░  ░      ░    ░░░ ░ ░ ░  ░  ░
          ░  ░  ░░ ░            ░      ░           ░
                 ░ ░            v{}


'''
WELCOME_TEXT_LEN = 55
SAVES_DIR = 'thymus/saves/'
SCREENS_SAVES_DIR = 'thymus/saves/screenshots/'
LOGGING_CONF_DIR = 'thymus/settings/'
LOGGING_CONF = LOGGING_CONF_DIR + 'logging.conf'
LOGGING_CONF_ENCODING = 'utf-8'
LOGGING_LEVEL = 'INFO'
LOGGING_FILE_DIR = 'thymus/log/'
LOGGING_FILE = LOGGING_FILE_DIR + 'thymus.log'
LOGGING_FILE_ENCODING = 'utf-8'
LOGGING_FILE_MAX_SIZE_BYTES = 5000000
LOGGING_FILE_MAX_INSTANCES = 5
LOGGING_BUF_CAP = 65535
LOGGING_FORMAT = '%(asctime)s %(module)-14s %(levelname)-3s %(message)s'
LOGGING_DEFAULTS = f'''
[loggers]
keys=root

[handlers]
keys=hand01

[formatters]
keys=form01

[logger_root]
level={LOGGING_LEVEL}
handlers=hand01

[handler_hand01]
class=logging.handlers.RotatingFileHandler
level=NOTSET
formatter=form01
args=('{LOGGING_FILE}', 'a', {LOGGING_FILE_MAX_SIZE_BYTES}, {LOGGING_FILE_MAX_INSTANCES}, '{LOGGING_FILE_ENCODING}')

[formatter_form01]
format={LOGGING_FORMAT}
'''
N_VALUE_LIMIT = 65535
CONTEXT_HELP = {
    'header': '[bold yellow]Welcome to {NOS} context.[/]',
    'footer': '\nSome commands may be used with arguments. Please, see the [link=https://github.com/blademd/thymus/wiki]documentation[/link].\nEnter any command in the input field below.',
    'modificators_header': '\nUse any of the next commands for the show command after a pipe symbol:',
    'singletones': {
        'show': 'To show a configuration of a current path use: [bold yellow]{CMDS}[/].',
        'go': 'To switch a current path use: [bold yellow]{CMDS}[/].',
        'top': 'To switch a current path to the top use: [bold yellow]{CMDS}[/].',
        'up': 'To step back one or more sections use: [bold yellow]{CMDS}[/].',
        'help': 'To show these hints use: [bold yellow]{CMDS}[/].',
        'version': 'To show a version of this configuration file use: [bold yellow]{CMDS}[/].',
        'set': 'To configure a current context use: [bold yellow]{CMDS}[/].',
        'global': 'To configure or the application settings use: [bold yellow]{CMDS}[/] and [bold yellow]show[/] or [bold yellow]set[/].',
    },
    'modificators': {
        'filter': 'To filter a line of lines from the output use: [bold yellow]{CMDS}[/].',
        'wildcard': 'To filter a section of lines from the output use: [bold yellow]{CMDS}[/].',
        'stubs': 'To show all finite instructions (stubs) for a current path use: [bold yellow]{CMDS}[/].',
        'sections': 'To list all available nested sections use: [bold yellow]{CMDS}[/].',
        'save': 'To save a content of a current path to a file use: [bold yellow]{CMDS}[/].',
        'count': 'To count lines of a current section use: [bold yellow]{CMDS}[/].',
        'diff': 'To compare two contexts use: [bold yellow]{CMDS}[/].',
        'contains': 'To search a pattern in a configuration use: [bold yellow]{CMDS}[/].',
    },
}
