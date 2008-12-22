from traceback import print_exc

from twisted.internet import reactor

import ibid
import ibid.module

class Dispatcher(object):

	def _process(self, query):
		for handler in ibid.core.processors:
			try:
				result = handler.process(query)
				if result:
					query = result
			except Exception, e:
				print_exc()

		for response in query['responses']:
			if response['source'] in ibid.core.sources:
				reactor.callFromThread(ibid.core.sources[response['source']].respond, response)
			else:
				print u'Invalid source %s' % response['source']

	def dispatch(self, query):
		reactor.callInThread(self._process, query)
