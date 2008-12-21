import re

import ibid.module

pattern = re.compile('\s*(say|do)\s+(\S+)\s+(.*)\s*', re.I)

class Module(ibid.module.Module):

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		match = pattern.search(query['msg'])
		if not match:
			return

		print "Processing say"
		(action, where, what) = match.groups()

		if (query["user"] != "Vhata"):
			reply = u"No!  You're not the boss of me!"
			if action.lower() == "say":
				query['responses'].append({'target': where, 'reply': u"Ooooh! %s was trying to make me say '%s'!" % (query["user"], what)})
			else:
				query['responses'].append({'target': where, 'reply': u"refuses to do '%s' for '%s'" % (what, query["user"]), 'action': True})
		else:
			if action.lower() == "say":
				reply = {'target': where, 'reply': what}
			else:
				reply = {'target': where, 'reply': what, 'action': True}

		query['responses'].append(reply)
		query['processed'] = True
		return query
