#!/usr/bin/env python

import gobject

import dbus
import dbus.service
import dbus.mainloop.glib
import traceback, sys

class SomeObject(dbus.service.Object):
    @dbus.service.method("org.ibid.IbidInterface", in_signature='s', out_signature='s')
    def HelloWorld(self, hello_message):
        print (str(hello_message))
        return "%s from example-service.py with unique name %s" % (str(hello_message), session_bus.get_unique_name())

    @dbus.service.method("org.ibid.IbidInterface", in_signature='', out_signature='')
    def Exit(self):
        mainloop.quit()

def catchall_signal_handler(*args, **kwargs):
    print "Caught-all [%s], {%s}" % (args, kwargs)

def this_signal_handler(*args, **kwargs):
    print "Caught this"
    for x in kwargs:
        print "   %s\t-> %s" % (x, kwargs[x])
    for x in args:
        print "   %s" % x

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()
    #name = dbus.service.BusName("org.ibid.IbidService", bus)
    #object = SomeObject(bus, '/org/ibid/IbidObject')

    bus.add_signal_receiver(this_signal_handler, interface_keyword='dbus_interface', member_keyword='member')

    mainloop = gobject.MainLoop()
    print "Running Ibid service."
    mainloop.run()
