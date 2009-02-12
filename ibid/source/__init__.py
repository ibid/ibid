from copy import copy

import ibid

class IbidSourceFactory(object):

    type = None
    auth = ()

    def __new__(cls, *args):
        for name, option in options.items():
            new = copy(option)
            default = getattr(cls, name)
            new.default = default
            setattr(cls, name, new)

        return super(IbidSourceFactory, cls).__new__(cls, *args)

    def __init__(self, name):
        self.name = name

    def setServiceParent(self, service):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

from ibid.config import Option
options = {
    'type': Option('type', 'Source type'),
    'auth': Option('auth', 'Authentication methods to allow'),
}
# vi: set et sta sw=4 ts=4:
