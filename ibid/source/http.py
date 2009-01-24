import logging

from twisted.web import server, resource
from twisted.application import internet
from twisted.internet import reactor
from twisted.spread import pb
import simplejson
from mako.template import Template
from mako.lookup import TemplateLookup
from pkg_resources import resource_string, resource_filename

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

templates = TemplateLookup(directories=[resource_filename('ibid.templates', '')], module_directory='/tmp/ibid-mako')

class Index(resource.Resource):

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)
        self.template = templates.get_template('index.html')

    def render_GET(self, request):
        return self.template.render()

class Message(resource.Resource):

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)
        self.form_template = templates.get_template('message_form.html')

    def render_GET(self, request):
        if 'm' in request.args:
            return self.render_POST(request)

        return self.form_template.render()

    def render_POST(self, request):
        event = Event(self.name, u'message')
        event.who = event.sender_id = event.sender = event.channel = unicode(request.transport.getPeer().host)
        event.addressed = True
        event.public = False
        event.message = unicode(request.args['m'][0], 'utf-8', 'replace')
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

    def render_POST(self, request):
        return self.render_GET(request)

class SourceFactory(IbidSourceFactory):

    port = 8080
    host = 'localhost'

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        root = Index(self.name)
        root.putChild('', Index(self.name))
        root.putChild('message', Message(name))
        root.putChild('plugin', Plugin(name))
        self.site = server.Site(root)

    def setServiceParent(self, service):
            if service:
                return internet.TCPServer(self.port, self.site).setServiceParent(service)
            else:
                reactor.listenTCP(self.port, self.site)

# vi: set et sta sw=4 ts=4:
