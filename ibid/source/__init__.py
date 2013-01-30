# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from copy import copy

try:
    from twisted.plugin import pluginPackagePaths
except ImportError:
    # Not available in Twisted 2.5.0 in Ubuntu hardy
    # This is straight from twisted.plugin
    import os.path
    import sys
    def pluginPackagePaths(name):
        package = name.split('.')
        return [os.path.abspath(os.path.join(x, *package)) for x in sys.path
            if not os.path.exists(os.path.join(x, *package + ['__init__.py']))]

__path__ = pluginPackagePaths(__name__) + __path__

class IbidSourceFactory(object):

    supports = ()
    auth = ()
    permissions = ()

    def __new__(cls, *args):
        cls.type = cls.__module__.split('.')[2]

        for name, option in options.items():
            new = copy(option)
            default = getattr(cls, name)
            new.default = default
            setattr(cls, name, new)

        return super(IbidSourceFactory, cls).__new__(cls, *args)

    def __init__(self, name):
        self.name = name
        self.setup()

    def setup(self):
        "Apply configuration. Called on every config reload"
        pass

    def setServiceParent(self, service):
        "Start the source and connect"
        raise NotImplementedError

    def connect(self):
        "Connect (if disconncted)"
        return self.setServiceParent(None)

    def disconnect(self):
        "Disconnect source"
        raise NotImplementedError

    def url(self):
        "Return a URL describing the source"
        return None

    def logging_name(self, identity):
        "Given an identity or connection, return a name suitable for logging"
        return identity

    def truncation_point(self, response, event=None):
        """Given a target, and possibly a related event, return the number of
        bytes to clip at, or None to indicate that a complete message will
        be delivered.
        """
        if (event is not None
                and response.get('target', None) == event.get('channel', None)
                and event.get('public', True)):
            return 490

        return None

from ibid.config import Option

options = {
    'auth': Option('auth', 'Authentication methods to allow'),
    'permissions': Option('permissions', 'Permissions granted to users on this source')
}
# vi: set et sta sw=4 ts=4:
