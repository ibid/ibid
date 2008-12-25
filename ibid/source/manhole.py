from twisted.internet import reactor
from twisted.application import internet
from twisted.manhole.telnet import ShellFactory
import ibid
from ibid.source import IbidSourceFactory

class SourceFactory(ShellFactory, IbidSourceFactory):
    def __init__(self, name):
        self.name = name

    def setServiceParent(self, service=None):
        port = 9898
        if 'port' in ibid.config.sources[self.name]:
            port = ibid.config.sources[self.name]['port']
        
        if service:
            return internet.TCPServer(port, ShellFactory()).setServiceParent(service)
        else:
            reactor.listenTCP(port, self)
    
    def connect(self):
        return self.setServiceParent(None)

# vi: set et sta sw=4 ts=4:
