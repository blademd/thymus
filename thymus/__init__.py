__version__ = '0.1.3.f1.e1-alpha'

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
