import os

import ibid
from ibid.plugins import Processor, match, authorise

help = {}

help['plugins'] = 'Lists, loads and unloads plugins.'
class ListPLugins(Processor):
    """list plugins"""
    feature = 'plugins'

    @match(r'^lsmod|list\s+plugins$')
    def handler(self, event):
        plugins = []
        for processor in ibid.processors:
            if processor.name not in plugins:
                plugins.append(processor.name)

        event.addresponse(', '.join(plugins))
        return event

help['core'] = 'Reloads core modules.'
class ReloadCoreModules(Processor):
    feature = 'core'

    priority = -5

    @match(r'^reload\s+(reloader|dispatcher|databases|auth)')
    @authorise('core')
    def reload(self, event, module):
        module = module.lower()
        if module == 'reloader':
            result = ibid.reload_reloader()
        else:
            result = getattr(ibid.reloader, 'reload_%s' % module)()

        event.addresponse(result and u'%s reloaded' % module or u"Couldn't reload %s" % module)

class LoadModules(Processor):
    """(load|unload|reload) <plugin|processor>"""
    feature = 'plugins'

    @match(r'^(?:re)?load\s+(\S+)$')
    @authorise('plugins')
    def load(self, event, plugin):
        result = ibid.reloader.unload_processor(plugin)
        result = ibid.reloader.load_processor(plugin)
        event.addresponse(result and u'%s reloaded' % plugin or u"Couldn't reload %s" % plugin)

    @match(r'^unload\s+(\S+)')
    @authorise('plugins')
    def unload(self, event, plugin):
        result = ibid.reloader.unload_processor(plugin)
        event.addresponse(result and u'%s unloaded' % plugin or u"Couldn't unload %s" % plugin)

# vi: set et sta sw=4 ts=4:
