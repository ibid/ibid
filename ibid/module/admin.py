"""Administrative commands for loading modules and configuration."""

import os

import ibid
from ibid.module import Module
from ibid.decorators import *

class ReloadConfig(Module):
    """Usage: reload config"""

    @addressed
    @notprocessed
    @match('^\s*reload\s+config\s*$')
    def process(self, event):
        try:
            ibid.config.reload()
            event.addresponse(u"Configuration reloaded")
        except:
            event.addresponse(u"Error reloading configuration")

class ListModules(Module):
    """Usage: list plugins"""

    @addressed
    @notprocessed
    @match('^\s*lsmod|list\s+plugins\s*$')
    def process(self, event):
        plugins = []
        for processor in ibid.processors:
            if processor.name not in plugins:
                plugins.append(processor.name)

        event.addresponse(', '.join(plugins))
        return event

class LoadModules(Module):
    """Usage: (load|unload|reload) <plugin|processor>"""

    @addressed
    @notprocessed
    @message
    @match('^\s*(load|unload|reload)\s+(\S+)\s+plugin\s*$')
    def process(self, event, action, module):
        reply = ''

        if action == u'load':
            reply = ibid.reloader.load_processor(module)
            reply = reply and u'Loaded %s' % module or u"Couldn't load %s" % module
        elif action == u'unload':
            reply = ibid.reloader.unload_processor(module)
            reply = reply and u'Unloaded %s' % module or u"Couldn't unload %s" % module
        elif action == u'reload':
            if module == u'reloader':
                ibid.reload_reloader()
                reply = "Done"
            elif module == u'dispatcher':
                ibid.reloader.reload_dispatcher()
                reply = "done"
            else:
                ibid.reloader.unload_processor(module)
                reply = ibid.reloader.load_processor(module)
                reply = reply and u'Reloaded %s' % module or u"Couldn't reload %s" % module

        if reply:
            event.addresponse(reply)
            return event

# vi: set et sta sw=4 ts=4:
