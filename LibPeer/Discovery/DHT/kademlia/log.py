import sys
from LibPeer.Logging import log

class Logger:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def msg(self, message, **kw):
        identifier = log.get_identifier(2)
	log.log(1, identifier, message)

    def info(self, message, **kw):
        identifier = log.get_identifier(2)
	log.log(2, identifier, message)

    def debug(self, message, **kw):
        identifier = log.get_identifier(2)
	log.log(0, identifier, message)

    def warning(self, message, **kw):
        identifier = log.get_identifier(2)
	log.log(3, identifier, message)

    def error(self, message, **kw):
        identifier = log.get_identifier(2)
	log.log(4, identifier, message)

    def critical(self, message, **kw):
        identifier = log.get_identifier(2)
	log.log(5, identifier, message)

try:
    theLogger
except NameError:
    theLogger = Logger()
    msg = theLogger.msg
    info = theLogger.info
    debug = theLogger.debug
    warning = theLogger.warning
    error = theLogger.error
    critical = theLogger.critical
