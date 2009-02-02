from dictclient import Connection

from ibid.plugins import Processor, match, Option, IntOption

help = {'dict': 'Defines words and checks spellings.'}

class Dict(Processor):
    """(spell|define) <word> [using (<dictionary>|<stratergy>)]
    (dictionaries|strategies)"""
    feature = 'dict'

    server = Option('server', 'Dictionary server hostname', 'localhost')
    port = IntOption('port', 'Dictionary server port number', 2628)

    def setup(self):
        self.connection = Connection(self.server, self.port)
        self.dictionaries = self.connection.getdbdescs()
        self.strategies = self.connection.getstratdescs()

    @match(r'^define\s+(.+?)(?:\s+using\s+(.+))?$')
    def define(self, event, word, dictionary):
        definitions = self.connection.define(dictionary or '*', word)
        event.addresponse(u', '.join([d.getdefstr() for d in definitions]))

    @match(r'spell\s+(.+?)(?:\s+using\s+(.+))?$')
    def handle_spell(self, event, word, stratergy):
        suggestions = self.connection.match('*', stratergy or 'soundex', word)
        event.addresponse(u', '.join([d.getword() for d in suggestions]))

    @match(r'^dictionaries$')
    def handle_dictionaries(self, event):
        event.addresponse(u', '.join(self.dictionaries.keys()))

    @match(r'^strategies$')
    def handle_strategies(self, event):
        event.addresponse(u', '.join(self.strategies.keys()))

    @match(r'^dictionary\s+(.+?)$')
    def handle_dictionary(self, event, dictionary):
        if dictionary in self.dictionaries:
            event.addresponse(unicode(self.dictionaries[dictionary]))
        else:
            event.addresponse(u"I don't have that response")

    @match(r'^stratergy\s+(.+?)$')
    def handle_stratergy(self, event, stratergy):
        if stratergy in self.strategies:
            event.addresponse(unicode(self.strategies[stratergy]))
        else:
            event.addresponse(u"I don't have that response")

# vi: set et sta sw=4 ts=4:
