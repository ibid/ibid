import logging

from twisted.web import server, resource, error
from twisted.application import internet
from twisted.internet import reactor
from twisted.spread import pb
import simplejson

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

class Index(resource.Resource):

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)

class Message(resource.Resource):

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

class Plugin(resource.Resource):
    isLeaf = True

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)

    def render_GET(self, request):
        plugin = request.postpath[0]
        classname = request.postpath[1]
        method = request.postpath[2]

        args = []
        for arg in request.postpath[3:]:
            try:
                arg = simplejson.loads(arg)
            except ValueError, e:
                pass
            args.append(arg)

        kwargs = {}
        for key, value in request.args.items():
            try:
                value = simplejson.loads(value[0])
            except ValueError, e:
                value = value[0]
            kwargs[key] = value

        self.log.debug(u'plugins.%s.%s.%s(%s, %s)', plugin, classname, method, ', '.join([str(arg) for arg in args]), ', '.join(['%s=%s' % (k,v) for k,v in kwargs.items()]))

        for processor in ibid.processors:
            if issubclass(processor.__class__, pb.Referenceable) and processor.name == plugin:
                if hasattr(processor, 'remote_%s' % method):
                    try:
                        result = getattr(processor, 'remote_%s' % method)(*args, **kwargs)
                        return simplejson.dumps(result)
                    except Exception, e:
                        return simplejson.dumps({'exception': True, 'message': e.message})

        return "Not found"

class SourceFactory(IbidSourceFactory):

    port = 8080
    host = 'localhost'

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        root = Index(self.name)
        root.putChild('message', Message(name))
        root.putChild('plugin', Plugin(name))
        self.site = server.Site(root)

    def setServiceParent(self, service):
            if service:
                return internet.TCPServer(self.port, self.site).setServiceParent(service)
            else:
                reactor.listenTCP(self.port, self.site)

# vi: set et sta sw=4 ts=4:
