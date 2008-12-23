import ibid

class IbidSourceFactory(object):

    def __init__(self, name):
        self.name = name
        self.respond = None

    def setServiceParent(self, service):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

# vi: set et sta sw=4 ts=4:
