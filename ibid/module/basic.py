import random

from ibid.module import Module, addresponse
from ibid.decorators import *

class Greet(Module):

	@addressedmessage('^\s*(?:hi|hello|hey)\s*$')
	def process(self, query):
		response = u'Hi %s' % query['user']
		addresponse(query, response)
		return query

class SayDo(Module):

	@addressed
	@notprocessed
	@match('^\s*(say|do)\s+(\S+)\s+(.*)\s*$')
	def process(self, query, action, where, what):
		if (query["user"] != u"Vhata"):
			reply = u"No!  You're not the boss of me!"
			if action.lower() == "say":
				query['responses'].append({'target': where, 'reply': u"Ooooh! %s was trying to make me say '%s'!" % (query["user"], what)})
			else:
				query['responses'].append({'target': where, 'reply': u"refuses to do '%s' for '%s'" % (what, query["user"]), 'action': True})
		else:
			if action.lower() == u"say":
				reply = {'target': where, 'reply': what}
			else:
				reply = {'target': where, 'reply': what, 'action': True}

		addresponse(query, reply)
		return query

complaints = (u'Huh?', u'Sorry...', u'?', u'Excuse me?')

class Complain(Module):

	@addressedmessage()
	def process(self, query):
		reply = complaints[random.randrange(len(complaints))]
		if query['public']:
			reply = u'%s: %s' % (query['user'], reply)

		addresponse(query, reply)
		return query
