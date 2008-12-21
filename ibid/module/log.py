import ibid.module

class Module(ibid.module.Module):

	def __init__(self, config):
		self.log = open(config['logfile'], 'a')
		#super.__init__(config)

	def process(self, query):
		self.log.write(u'%s > %s: %s\n' % (query['user'], query['channel'], query['msg']))
		self.log.flush()
