#!/usr/bin/env python
# Copyright (c) 2008, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import gobject

import dbus
import dbus.service
import dbus.mainloop.glib

class Ping(dbus.service.Object):

    @dbus.service.method('org.ibid.ModuleInterface',
                        in_signature='s', out_signature='(bbs)')
    def init(self, name):
        self.name = name
        addressed = True
        notprocessed = True
        pattern = '^ping$'
        return (addressed, notprocessed, pattern)

    @dbus.service.method("org.ibid.ModuleInterface",
                         in_signature='a{ss}', out_signature='a{ss}')
    def process(self, event):
        print "Handling event %s" % event
        return {'reply': 'pong'}


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    session_bus = dbus.SessionBus()
    name = dbus.service.BusName("org.ibid.module.Ping", session_bus)
    object = Ping(session_bus, '/org/ibid/module/Ping')

    mainloop = gobject.MainLoop()
    mainloop.run()

# vi: set et sta sw=4 ts=4:
