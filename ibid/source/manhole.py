from twisted.internet import reactor
from twisted.application import internet
from twisted.manhole.telnet import ShellFactory

from ibid.source import IbidSourceFactory
from ibid.config import Option, IntOption

class SourceFactory(ShellFactory, IbidSourceFactory):

    port = IntOption('port', 'Port number to listen on', 9898)
    username = Option('username', 'Login Username', 'admin')
    password = Option('password', 'Login Password', 'admin')

    def __init__(self, name):
        ShellFactory.__init__(self)
        IbidSourceFactory.__init__(self, name)
        self.name = name

    def setServiceParent(self, service=None):
        if service:
            self.listener = internet.TCPServer(self.port, self).setServiceParent(service)
            return self.listener
        else:
            self.listener = reactor.listenTCP(self.port, self)

    def connect(self):
        return self.setServiceParent(None)

    def disconnect(self):
        self.listener.stopListening()
        return True

# vi: set et sta sw=4 ts=4:
