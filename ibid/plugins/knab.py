import perl

import ibid
from ibid.plugins import Processor, handler

class Knab(Processor):

	knabdir = '../knab/'
	config = 'Knab.cfg'

	def __init__(self, name):
		Processor.__init__(self, name)

		perl.eval('use lib "%s"' % self.knabdir)
		perl.require('Knab::Dumper')
		perl.require('Knab::Conf')
		perl.require('Knab::Modules')
		perl.require('Knab::Processor')
		perl.eval('$::dumper=new Knab::Dumper();')
		perl.eval('$::config = new Knab::Conf(Basedir=>"%s", Filename=>"%s");' % (self.knabdir, self.config))
		factoidDB = perl.eval('$::config->getValue("FactoidDB/module");')
		perl.require(factoidDB)
		perl.eval('$::db=new %s();' % factoidDB)
		modules = perl.callm('new', 'Knab::Modules')
		self.processor = perl.callm('new', 'Knab::Processor', modules)

	@handler
	def handler(self, event):
		event.input = event.message
		event.oldinput = event.message_raw
		event.withpunc = event.message_raw
		self.processor.Process(event)

		responses = []
		for response in event.responses:
			if 'items' in dir(response):
				new = {}
				for key, value in response.items():
					new[key] = value
				responses.append(new)
			else:
				responses.append(response)
				
		event.responses = responses
