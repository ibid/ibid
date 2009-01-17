import logging
from threading import Timer

from twisted.python import log

logger = None

def log_exception(message):
	logger.exception(message)

class PythonExceptionLoggingObserver(object):

	def __init__(self, loggerName='twisted'):
		global logger
		logger = logging.getLogger(loggerName)

	def start(self):
		log.addObserver(self.emit)

	def stop(self):
		log.removeObserver(self.emit)

	def emit(self, eventDict):
		if eventDict['isError'] and 'failure' in eventDict:
			message = eventDict.get('why') or 'Unhandled Error' + '\n' + eventDict['failure'].getTraceback()
			Timer(0, log_exception, (message,)).start()
