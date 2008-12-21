import ibid.module

class Module(ibid.module.Module):

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		for who in self.config['ignore']:
			if query['user'] == who:
				query['processed'] = True

		return query
