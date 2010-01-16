from twisted.internet import reactor

import ibid
from ibid.utils import human_join
from ibid.plugins import Processor, match, authorise

help = {}

help['plugins'] = u'Lists, loads and unloads plugins.'
class ListPLugins(Processor):
    u"""list plugins"""
    feature = 'plugins'

    @match(r'^lsmod|list\s+plugins$')
    def handler(self, event):
        plugins = []
        for processor in ibid.processors:
            if processor.name not in plugins:
                plugins.append(processor.name)

        event.addresponse(u'Plugins: %s', human_join(sorted(plugins)) or u'none')

help['core'] = u'Reloads core modules.'
class ReloadCoreModules(Processor):
    u"""reload (reloader|dispatcher|databases|auth)"""
    feature = 'core'

    priority = -5
    permission = u'core'

    @match(r'^reload\s+(reloader|dispatcher|databases|auth)$')
    @authorise()
    def reload(self, event, module):
        module = module.lower()
        if module == 'reloader':
            result = ibid.reload_reloader()
        else:
            result = getattr(ibid.reloader, 'reload_%s' % module)()

        event.addresponse(result and u'%s reloaded' or u"Couldn't reload %s", module)

class LoadModules(Processor):
    u"""(load|unload|reload) <plugin|processor>"""
    feature = 'plugins'

    permission = u'plugins'

    @match(r'^(?:re)?load\s+(\S+)(?:\s+plugin)?$')
    @authorise()
    def load(self, event, plugin):
        result = ibid.reloader.unload_processor(plugin)
        result = ibid.reloader.load_processor(plugin)
        event.addresponse(result and u'%s reloaded' or u"Couldn't reload %s", plugin)

    @match(r'^unload\s+(\S+)$')
    @authorise()
    def unload(self, event, plugin):
        result = ibid.reloader.unload_processor(plugin)
        event.addresponse(result and u'%s unloaded' or u"Couldn't unload %s", plugin)

help['die'] = u'Terminates the bot'
class Die(Processor):
    u"""die"""
    feature = 'die'

    permission = u'admin'

    @match(r'^die$')
    @authorise()
    def die(self, event):
        reactor.stop()

help['sources'] = u'Controls and lists the configured sources.'
class Admin(Processor):
    u"""(connect|disconnect) (to|from) <source>
    load <source> source"""
    feature = 'sources'

    permission = u'sources'

    @match(r'^connect\s+(?:to\s+)?(\S+)$')
    @authorise()
    def connect(self, event, source):
        if source not in ibid.sources:
            event.addresponse(u"I don't have a source called %s", source)
        elif ibid.sources[source].connect():
            event.addresponse(u'Connecting to %s', source)
        else:
            event.addresponse(u"I couldn't connect to %s", source)

    @match(r'^disconnect\s+(?:from\s+)?(\S+)$')
    @authorise()
    def disconnect(self, event, source):
        if source not in ibid.sources:
            event.addresponse(u"I am not connected to %s", source)
        elif ibid.sources[source].disconnect():
            event.addresponse(u'Disconnecting from %s', source)
        else:
            event.addresponse(u"I couldn't disconnect from %s", source)

    @match(r'^(?:re)?load\s+(\S+)\s+source$')
    @authorise()
    def load(self, event, source):
        if ibid.reloader.load_source(source, ibid.service):
            event.addresponse(u"%s source loaded", source)
        else:
            event.addresponse(u"Couldn't load %s source", source)

class Info(Processor):
    u"""(sources|list configured sources)"""
    feature = 'sources'

    @match(r'^sources$')
    def list(self, event):
        sources = []
        for name, source in ibid.sources.items():
            url = source.url()
            sources.append(url and u'%s (%s)' % (name, url) or name)
        event.addresponse(u'Sources: %s', human_join(sorted(sources)) or u'none')

    @match(r'^list\s+configured\s+sources$')
    def listall(self, event):
        event.addresponse(u'Configured sources: %s', human_join(sorted(ibid.config.sources.keys())) or u'none')

# vi: set et sta sw=4 ts=4:
