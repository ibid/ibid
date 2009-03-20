from socket import error

from dictclient import Connection

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption

help = {'dict': u'Defines words and checks spellings.'}

class Dict(Processor):
    u"""spell <word> [using <dictionary>]
    define <word> [using <strategy>]
    (dictionaries|strategies)
    (dictionary|strategy) <name>"""
    feature = 'dict'

    server = Option('server', 'Dictionary server hostname', 'localhost')
    port = IntOption('port', 'Dictionary server port number', 2628)

    @match(r'^define\s+(.+?)(?:\s+using\s+(.+))?$')
    def define(self, event, word, dictionary):
        try:
            connection = Connection(self.server, self.port)
            definitions = connection.define(dictionary or '*', word)
            if definitions:
                event.addresponse(u'%s', u', '.join([d.getdefstr() for d in definitions]))
            else:
                event.addresponse(u"I don't have a definition for that. Is it even a word?")
        except error:
            event.addresponse(u'Unable to connect to dictionary server')
            raise
        except Exception, e:
            event.addresponse(u'The dictionary complained: %s' % unicode(e))

    @match(r'^spell\s+(.+?)(?:\s+using\s+(.+))?$')
    def handle_spell(self, event, word, strategy):
        try:
            connection = Connection(self.server, self.port)
            correct = connection.match('*', 'exact', word)
            if correct:
                event.addresponse(u'That seems correct. Carry on')
                return
            suggestions = connection.match('*', strategy or 'lev', word)
            if suggestions:
                event.addresponse(u'Suggestions: %s', u', '.join([d.getword() for d in suggestions]))
            else:
                event.addresponse(u"That doesn't seem correct, but I can't find anything to suggest")
        except error:
            event.addresponse(u'Unable to connect to dictionary server')
            raise
        except Exception, e:
            event.addresponse(u'The dictionary complained: %s' % unicode(e))

    @match(r'^dictionaries$')
    def handle_dictionaries(self, event):
        try:
            connection = Connection(self.server, self.port)
            dictionaries = connection.getdbdescs()
            event.addresponse(u'Dictionaries: %s', u', '.join(sorted(dictionaries.keys())))
        except error:
            event.addresponse(u'Unable to connect to dictionary server')
            raise

    @match(r'^strater?gies$')
    def handle_strategies(self, event):
        try:
            connection = Connection(self.server, self.port)
            strategies = connection.getstratdescs()
            event.addresponse(u'Strategies: %s', u', '.join(sorted(strategies.keys())))
        except error:
            event.addresponse(u'Unable to connect to dictionary server')
            raise

    @match(r'^dictionary\s+(.+?)$')
    def handle_dictionary(self, event, dictionary):
        try:
            connection = Connection(self.server, self.port)
            dictionaries = connection.getdbdescs()
            if dictionary in dictionaries:
                event.addresponse(u'%s', dictionaries[dictionary])
            else:
                event.addresponse(u"I don't have that dictionary")
        except error:
            event.addresponse(u'Unable to connect to dictionary server')
            raise

    @match(r'^strater?gy\s+(.+?)$')
    def handle_strategy(self, event, strategy):
        try:
            connection = Connection(self.server, self.port)
            strategies = connection.getstratdescs()
            if strategy in strategies:
                event.addresponse(u'%s', strategies[strategy])
            else:
                event.addresponse(u"I don't have that strategy")
        except error:
            event.addresponse(u'Unable to connect to dictionary server')
            raise

# vi: set et sta sw=4 ts=4:
