from Utils.Confloader import conf

import logging
import os
import re
import datetime

os.makedirs("logs", exist_ok=True)

CHAT_LEVEL_NUM = 15 
logging.addLevelName(CHAT_LEVEL_NUM, "CHAT")

def chat(self, message, *args, **kwargs):
    if self.isEnabledFor(CHAT_LEVEL_NUM):
        self._log(CHAT_LEVEL_NUM, message, args, **kwargs)

logging.Logger.chat = chat

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m',
        'CHAT': '\033[97m',
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        message = super().format(record)
        return f"{color}{message}{self.RESET if color else ''}"

class NoColorFormatter(logging.Formatter):
    ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

    def format(self, record):
        message = super().format(record)
        return self.ANSI_ESCAPE.sub('', message)

format_string = '[%(asctime)s %(levelname)s]: %(message)s'
date_format = '%H:%M:%S'

console_handler = logging.StreamHandler()
console_handler.setFormatter(ColorFormatter(format_string, date_format))

now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
log_filename = f'logs/server-{now_str}.log'
if conf['log-console']:
    file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
    file_handler.setFormatter(NoColorFormatter(format_string, date_format))


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.handlers.clear()
logger.addHandler(console_handler)
if conf['log-console']:
    logger.addHandler(file_handler)
