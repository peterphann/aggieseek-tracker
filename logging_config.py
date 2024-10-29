import logging
import socket
from logging.handlers import SysLogHandler
from dotenv import load_dotenv
import os

load_dotenv()
PAPERTRAIL_HOST = os.getenv('PAPERTRAIL_HOST')
PAPERTRAIL_PORT = int(os.getenv('PAPERTRAIL_PORT'))

class ContextFilter(logging.Filter):
    hostname = socket.gethostname()
    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True

def init_logging():
    syslog = SysLogHandler(address=(PAPERTRAIL_HOST, PAPERTRAIL_PORT))
    syslog.addFilter(ContextFilter())

    format = '%(asctime)s %(hostname)s aggieseek-tracker: %(message)s'
    formatter = logging.Formatter(format, datefmt='%b %d %H:%M:%S')
    syslog.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(syslog)
    logger.setLevel(logging.DEBUG)
