from twisted.internet import reactor

import ibid.source.irc
from ibid.module import modules
from ibid.processor import Processor

class Ibid(object):

	def __init__(self, config):
		self.sources = {}
		self.processor = Processor()
		self.config = config

		for source in config['sources']:
			if source['type'] == 'irc':
				self.sources[source['name']] = ibid.source.irc.SourceFactory(self.processor, source['nick'], source['channels'])
				reactor.connectTCP(source['server'], source['port'], self.sources[source['name']])

		self.processor.sources = self.sources
		mod = modules.Module(self.processor)
		self.processor.handlers = [mod]
		print config['modules']
		for name, config in config['modules'].items():
			print 'Loading %s config %s' % (name, config)
			mod.load(name, config)

	def run(self):
		reactor.run()
