__version__ = '0.1.6-alpha'

CONFIG_PATH = 'settings/'
CONFIG_NAME = 'thymus.json'
WELCOME_TEXT = """\
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


"""
WELCOME_TEXT_LEN = 55
WRAPPER_DIR = '~/thymus_data/'
SAVES_DIR = 'saves/'
SCREENS_DIR = 'screenshots/'
LOGGING_CONF_DIR = 'settings/'
LOGGING_CONF = LOGGING_CONF_DIR + 'logging.conf'
LOGGING_CONF_ENCODING = 'utf-8'
LOGGING_LEVEL = 'INFO'
LOGGING_FILE_DIR = 'log/'
LOGGING_FILE = LOGGING_FILE_DIR + 'thymus.log'
LOGGING_FILE_ENCODING = 'utf-8'
LOGGING_FILE_MAX_SIZE_BYTES = 5000000
LOGGING_FILE_MAX_INSTANCES = 5
LOGGING_BUF_CAP = 65535
LOGGING_FORMAT = '%(asctime)s %(module)-14s %(levelname)-3s %(message)s'
N_VALUE_LIMIT = 65535
CONTEXT_HELP = 'templates/context_help.json'
