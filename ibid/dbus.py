# Copyright (c) 2008-2009, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import dbus.service

class DbusModule(dbus.service.Object):

    @dbus.service.method('org.ibid.ModuleInterface', in_signature='s', out_signature='s')
    def init(self, name):
        self.name = name
        return 'pattern'

    @dbus.service.method('org.ibid.ModuleInterface', in_signature='s', out_signature='s')
    def process(self, event):
        return 'reply'

# vi: set et sta sw=4 ts=4:
