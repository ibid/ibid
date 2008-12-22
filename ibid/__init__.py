import sys

import ibid.reloader

class Ibid(object):

	def __init__(self):
		self.sources = {}
		self.config = {}
		self.dispatcher = None
		self.processors = []

	def run(self, config):
		self.config = config
		self.reload_reloader()
		self.reloader.run()

	def reload_reloader(self):
		reload(ibid.reloader)
		reloader = ibid.reloader.Reloader()
		self.reloader = reloader

core = Ibid()
sys.modules['ibid.core'] = core
