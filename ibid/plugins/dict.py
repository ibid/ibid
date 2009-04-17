from socket import error

from dictclient import Connection

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption

help = {'dict': u'Defines words and checks spellings.'}

class Dict(Processor):
    u"""spell <word> [using <strategy>]
    define <word> [using <dictionary>]
    (dictionaries|strategies)
    (dictionary|strategy) <name>"""
    feature = 'dict'

    server = Option('server', 'Dictionary server hostname', 'localhost')
    port = IntOption('port', 'Dictionary server port number', 2628)

    @match(r'^define\s+(.+?)(?:\s+using\s+(.+))?$')
    def define(self, event, word, dictionary):
        connection = Connection(self.server, self.port)
        try:
            definitions = connection.define(dictionary or '*', word)
        except Exception, e:
            event.addresponse(u'The dictionary complained: %s' % unicode(e))
            return

        if definitions:
            event.addresponse(u'%s', u', '.join([d.getdefstr() for d in definitions]))
        else:
            event.addresponse(u"I don't have a definition for that. Is it even a word?")

    @match(r'^spell\s+(.+?)(?:\s+using\s+(.+))?$')
    def handle_spell(self, event, word, strategy):
        connection = Connection(self.server, self.port)
        try:
            correct = connection.match('*', 'exact', word)
            if correct:
                event.addresponse(u'That seems correct. Carry on')
                return
            suggestions = connection.match('*', strategy or 'lev', word)
        except Exception, e:
            event.addresponse(u'The dictionary complained: %s' % unicode(e))
        if suggestions:
            event.addresponse(u'Suggestions: %s', u', '.join([d.getword() for d in suggestions]))
        else:
            event.addresponse(u"That doesn't seem correct, but I can't find anything to suggest")

    @match(r'^dictionaries$')
    def handle_dictionaries(self, event):
        connection = Connection(self.server, self.port)
        dictionaries = connection.getdbdescs()
        event.addresponse(u'Dictionaries: %s', u', '.join(sorted(dictionaries.keys())))

    @match(r'^strater?gies$')
    def handle_strategies(self, event):
        connection = Connection(self.server, self.port)
        strategies = connection.getstratdescs()
        event.addresponse(u'Strategies: %s', u', '.join(sorted(strategies.keys())))

    @match(r'^dictionary\s+(.+?)$')
    def handle_dictionary(self, event, dictionary):
        connection = Connection(self.server, self.port)
        dictionaries = connection.getdbdescs()
        if dictionary in dictionaries:
            event.addresponse(u'%s', dictionaries[dictionary])
        else:
            event.addresponse(u"I don't have that dictionary")

    @match(r'^strater?gy\s+(.+?)$')
    def handle_strategy(self, event, strategy):
        connection = Connection(self.server, self.port)
        strategies = connection.getstratdescs()
        if strategy in strategies:
            event.addresponse(u'%s', strategies[strategy])
        else:
            event.addresponse(u"I don't have that strategy")

# vi: set et sta sw=4 ts=4:
