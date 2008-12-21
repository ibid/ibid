from twisted.internet import reactor

import ibid.source.irc
from ibid.module import greet, complain, datetime, saydo
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
		self.processor.handlers = [greet.Module(), datetime.Module(), saydo.Module(), complain.Module()]

	def run(self):
		reactor.run()
