import ibid
from ibid.config import Option

class IbidSourceFactory(object):

    def __init__(self, name):
        self.name = name
        self.type = Option('type', 'Source type', name)

    def setServiceParent(self, service):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

# vi: set et sta sw=4 ts=4:
