#!/usr/bin/env python

import gobject

import dbus
import dbus.service
import dbus.mainloop.glib

class Ping(dbus.service.Object):

	@dbus.service.method('org.ibid.ModuleInterface',
						in_signature='s', out_signature='s')
	def init(self, name):
		self.name = name
		return '^ping$'

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
