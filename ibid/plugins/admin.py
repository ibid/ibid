"""Administrative commands for loading modules and configuration."""

import os

import ibid
from ibid.plugins import Processor, match, authorise

class ListModules(Processor):
    """Usage: list plugins"""

    @match('^\s*lsmod|list\s+plugins\s*$')
    def handler(self, event):
        plugins = []
        for processor in ibid.processors:
            if processor.name not in plugins:
                plugins.append(processor.name)

        event.addresponse(', '.join(plugins))
        return event

class ReloadCoreModules(Processor):

    priority = -5

    @match(r'^\s*reload\s+(reloader|dispatcher|databases|auth)\s*')
    @authorise('core')
    def reload(self, event, module):
        module = module.lower()
        if module == 'reloader':
            result = ibid.reload_reloader()
        else:
            result = getattr(ibid.reloader, 'reload_%s' % module)()

        event.addresponse(result and u'%s reloaded' % module or u"Couldn't reload %s" % module)

class LoadModules(Processor):
    """Usage: (load|unload|reload) <plugin|processor>"""

    @match('^\s*(?:re)?load\s+(\S+)\s*$')
    @authorise('plugins')
    def load(self, event, plugin):
        result = ibid.reloader.unload_processor(plugin)
        result = ibid.reloader.load_processor(plugin)
        event.addresponse(result and u'%s reloaded' % plugin or u"Couldn't reload %s" % plugin)

    @match('^\s*unload\s+(\S+)\s*')
    @authorise('plugins')
    def unload(self, event, plugin):
        result = ibid.reloader.unload_processor(plugin)
        event.addresponse(result and u'%s unloaded' % plugin or u"Couldn't unload %s" % plugin)

# vi: set et sta sw=4 ts=4:
