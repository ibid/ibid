from random import choice

from dictclient import Connection

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption
from ibid.utils import human_join

help = {'dict': u'Defines words and checks spellings.'}

class Dict(Processor):
    u"""spell <word> [using <strategy>]
    define <word> [using <dictionary>]
    (dictionaries|strategies)
    (dictionary|strategy) <name>"""
    feature = 'dict'

    server = Option('server', 'Dictionary server hostname', 'localhost')
    port = IntOption('port', 'Dictionary server port number', 2628)

    @match(r'^(?:define|dict)\s+(.+?)(?:\s+using\s+(.+))?$')
    def define(self, event, word, dictionary):
        connection = Connection(self.server, self.port)
        dictionary = dictionary is None and '*' or dictionary.lower()
        dictionaries = connection.getdbdescs().keys()

        if dictionary != '*' and dictionary not in dictionaries:
            event.addresponse(
                    u"I'm afraid I don't have a dictionary of that name. I know about: %s",
                    human_join(sorted(dictionaries)))
            return

        definitions = connection.define(dictionary, word.encode('utf-8'))
        if definitions:
            event.addresponse(u', '.join(d.getdefstr() for d in definitions))
        else:
            suggestions = connection.match(dictionary, 'lev', word.encode('utf-8'))
            if suggestions:
                event.addresponse(
                        u"I don't know about %(word)s. Maybe you meant %(suggestions)s?", {
                            'word': word,
                            'suggestions': human_join([d.getword() for d in suggestions], conjunction=u'or'),
                })
            else:
                event.addresponse(u"I don't have a definition for that. Is it even a word?")

    @match(r'^spell\s+(.+?)(?:\s+using\s+(.+))?$')
    def handle_spell(self, event, word, strategy):
        connection = Connection(self.server, self.port)
        word = word.encode('utf-8')
        strategies = connection.getstratdescs().keys()

        if connection.match('*', 'exact', word):
            event.addresponse(choice((
                u'That seems correct. Carry on',
                u'Looks good to me',
                u"Yup, that's a word all right",
                u'Yes, you *can* spell',
            )))
            return

        strategy = strategy is None and 'lev' or strategy.lower()
        if strategy not in strategies:
            event.addresponse(
                    u"I'm afraid I don't know about such a strategy. I know about: %s",
                    human_join(sorted(strategies)))

        suggestions = connection.match('*', strategy, word)
        if suggestions:
            event.addresponse(u'Suggestions: %s', human_join([d.getword() for d in suggestions]))
        else:
            event.addresponse(u"That doesn't seem correct, but I can't find anything to suggest")

    @match(r'^dictionaries$')
    def handle_dictionaries(self, event):
        connection = Connection(self.server, self.port)
        dictionaries = connection.getdbdescs()
        event.addresponse(u'My Dictionaries: %s', human_join(sorted(dictionaries.keys())))

    @match(r'^strater?gies$')
    def handle_strategies(self, event):
        connection = Connection(self.server, self.port)
        strategies = connection.getstratdescs()
        event.addresponse(u'My Strategies: %s', human_join(sorted(strategies.keys())))

    @match(r'^dictionary\s+(.+?)$')
    def handle_dictionary(self, event, dictionary):
        connection = Connection(self.server, self.port)
        dictionaries = connection.getdbdescs()
        dictionary = dictionary.lower()
        if dictionary in dictionaries:
            event.addresponse(unicode(dictionaries[dictionary]))
        else:
            event.addresponse(u"I don't have that dictionary")

    @match(r'^strater?gy\s+(.+?)$')
    def handle_strategy(self, event, strategy):
        connection = Connection(self.server, self.port)
        strategies = connection.getstratdescs()
        strategy = strategy.lower()
        if strategy in strategies:
            event.addresponse(unicode(strategies[strategy]))
        else:
            event.addresponse(u"I don't have that strategy")

# vi: set et sta sw=4 ts=4:
