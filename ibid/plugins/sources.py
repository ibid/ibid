import ibid
from ibid.plugins import Processor, match, authorise

help = {'sources': 'Controls and lists the configured sources.'}

class Admin(Processor):
    """(connect|disconnect) (to|from) <source>
    load <source> source"""
    feature = 'sources'

    permission = u'sources'

    @match(r'^connect\s+(?:to\s+)?(\S+)$')
    @authorise
    def connect(self, event, source):

        if ibid.sources[source.lower()].connect():
            event.addresponse(u'Connecting to %s' % source)
        else:
            event.addresponse(u"I couldn't connect to %s" % source)

    @match(r'^disconnect\s+(?:from\s+)?(\S+)$')
    @authorise
    def disconnect(self, event, source):

        if ibid.sources[source.lower()].disconnect():
            event.addresponse(u'Disconnecting from %s' % source)
        else:
            event.addresponse(u"I couldn't disconnect from %s" % source)

    @match(r'^(?:re)?load\s+(\S+)\s+source$')
    @authorise
    def load(self, event, source):
        if ibid.reloader.load_source(source, ibid.service):
            event.addresponse(u"%s source loaded" % source)
        else:
            event.addresponse(u"Couldn't load %s source" % source)

class Info(Processor):
    """(sources|list configured sources)"""
    feature = 'sources'

    @match(r'^sources$')
    def list(self, event):
        sources = []
        for name, source in ibid.sources.items():
            url = source.url()
            sources.append(url and '%s (%s)' % (name, url) or name)
        event.addresponse(u', '.join(sources))

    @match(r'^list\s+configured\s+sources$')
    def listall(self, event):
        event.addresponse(', '.join(ibid.config.sources.keys()))

# vi: set et sta sw=4 ts=4:
