import logging

from twisted.web import server, resource
from twisted.application import internet
from twisted.internet import reactor

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

class IbidRequest(resource.Resource):
    isLeaf = True

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)

    def render_GET(self, request):
        event = Event(self.name, u'message')
        event.who = event.sender_id = event.sender = event.channel = request.transport.getPeer().host
        event.addressed = True
        event.public = False
        event.message = request.args['m'][0]
        self.log.debug(u"Received GET request from %s: %s", event.sender, event.message)
        ibid.dispatcher.dispatch(event).addCallback(self.respond, request)
        return server.NOT_DONE_YET

    def respond(self, event, request):
        output = '\n'.join([response['reply'].encode('utf-8') for response in event.responses])
        request.write(output)
        request.finish()
        self.log.debug(u"Responded to request from %s: %s", event.sender, output)

class SourceFactory(IbidSourceFactory):

    port = 8080
    host = 'localhost'

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        self.site = server.Site(IbidRequest(self.name))

    def setServiceParent(self, service):
            if service:
                return internet.TCPServer(self.port, self.site).setServiceParent(service)
            else:
                reactor.listenTCP(self.port, self.site)

# vi: set et sta sw=4 ts=4:
