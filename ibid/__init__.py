from twisted.internet import reactor
import ibid.source.irc
import ibid.module.greet
from ibid.processor import Processor

class Ibid(object):

	def __init__(self, config):
		self.sources = {}
		self.processor = Processor()

		for source in config['sources']:
			if source['type'] == 'irc':
				self.sources[source['name']] = ibid.source.irc.SourceFactory(self.processor, source['nick'], source['channels'])
				reactor.connectTCP(source['server'], source['port'], self.sources[source['name']])

		self.processor.sources = self.sources
		self.processor.handlers = [ibid.module.greet.Module()]

	def run(self):
		reactor.run()
