from twisted.internet import reactor
from twisted.application import internet
from twisted.manhole.telnet import ShellFactory
import ibid
from ibid.source import IbidSourceFactory

class SourceFactory(ShellFactory, IbidSourceFactory):

    port = 9898

    def __init__(self, name):
        ShellFactory.__init__(self)
        IbidSourceFactory.__init__(self, name)
        self.name = name

    def setServiceParent(self, service=None):
        if service:
            return internet.TCPServer(self.port, ShellFactory()).setServiceParent(service)
        else:
            reactor.listenTCP(self.port, self)
    
    def connect(self):
        return self.setServiceParent(None)

# vi: set et sta sw=4 ts=4:
