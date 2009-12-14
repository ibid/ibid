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

# vi: set et sta sw=4 ts=4:
