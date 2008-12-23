import os

import ibid
from ibid.module import Module
from ibid.decorators import *

class ListModules(Module):

    @addressed
    @notprocessed
    @match('^\s*lsmod\s*$')
    def process(self, event):
        reply = ''
        for processor in ibid.processors:
            reply = u'%s%s, ' % (reply, processor.name)

        event.addresponse(reply)
        return event

class LoadModules(Module):

    @addressed
    @notprocessed
    @message
    @match('^\s*(load|unload|reload)\s+(\S+)\s*$')
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
