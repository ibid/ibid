from dictclient import Connection

import ibid
from ibid.plugins import Processor, match

help = {'dict': 'Defines words and checks spellings.'}

class Dict(Processor):
    """(spell|define) <word> [using (<dictionary>|<stratergy>)]
    (dictionaries|strategies)"""
    feature = 'dict'

    server = 'localhost'
    port = 2628

    def setup(self):
        self.connection = Connection(self.server, self.port)
        self.dictionaries = self.connection.getdbdescs()
        self.strategies = self.connection.getstratdescs()

    @match(r'^define\s+(.+?)(?:\s+using\s+(.+))?$')
    def define(self, event, word, dictionary):
        definitions = self.connection.define(dictionary or '*', word)
        event.addresponse(', '.join([d.getdefstr() for d in definitions]))

    @match(r'spell\s+(.+?)(?:\s+using\s+(.+))?$')
    def handle_spell(self, event, word, stratergy):
        suggestions = self.connection.match('*', stratergy or 'soundex', word)
        event.addresponse(', '.join([d.getword() for d in suggestions]))

    @match(r'^dictionaries$')
    def handle_dictionaries(self, event):
        event.addresponse(', '.join(self.dictionaries.keys()))

    @match(r'^strategies$')
    def handle_strategies(self, event):
        event.addresponse(', '.join(self.strategies.keys()))

    @match(r'^dictionary\s+(.+?)$')
    def handle_dictionary(self, event, dictionary):
        if dictionary in self.dictionaries:
            event.addresponse(self.dictionaries[dictionary])
        else:
            event.addresponse(u"I don't have that response")

    @match(r'^stratergy\s+(.+?)$')
    def handle_stratergy(self, event, stratergy):
        if stratergy in self.strategies:
            event.addresponse(self.strategies[stratergy])
        else:
            event.addresponse(u"I don't have that response")

# vi: set et sta sw=4 ts=4:
