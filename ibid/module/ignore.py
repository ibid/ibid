import ibid.module

class Module(ibid.module.Module):

	def process(self, query):
		if not query['addressed'] or query['processed'] or 'msg' not in query:
			return

		for who in self.config['ignore']:
			if query['user'] == who:
				query['processed'] = True

		return query
