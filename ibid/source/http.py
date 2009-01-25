import logging
from inspect import getargspec, ismethod

from twisted.web import server, resource, static
from twisted.application import internet
from twisted.internet import reactor
from twisted.spread import pb
import simplejson
from pkg_resources import resource_string, resource_filename
from jinja import Environment, PackageLoader

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

templates = Environment(loader=PackageLoader('ibid', 'templates'))

class Index(resource.Resource):

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)
        self.template = templates.get_template('index.html')

    def render_GET(self, request):
        return self.template.render().encode('utf-8')

class Message(resource.Resource):

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)
        self.form_template = templates.get_template('message_form.html')

    def render_GET(self, request):
        if 'm' in request.args:
            return self.render_POST(request)

        return self.form_template.render().encode('utf-8')

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
        self.form = templates.get_template('plugin_form.html')

    def get_function(self, request):
        plugin = request.postpath[0]
        classname = request.postpath[1]
        method = request.postpath[2]

        __import__('ibid.plugins.%s' % plugin)
        klass = eval('ibid.plugins.%s.%s' % (plugin, classname))
        for processor in ibid.processors:
            if isinstance(processor, klass) and issubclass(processor.__class__, pb.Referenceable) and processor.name == plugin:
                if hasattr(processor, 'remote_%s' % method):
                    return getattr(processor, 'remote_%s' % method)

        return None

    def render_POST(self, request):
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

        function = self.get_function(request)
        if not function:
            return "Not found"

        self.log.debug(u'%s(%s, %s)', function, ', '.join([str(arg) for arg in args]), ', '.join(['%s=%s' % (k,v) for k,v in kwargs.items()]))

        try:
            result = function(*args, **kwargs)
            return simplejson.dumps(result)
        except Exception, e:
            return simplejson.dumps({'exception': True, 'message': e.message})

    def render_GET(self, request):
        function = self.get_function(request)
        if not function:
            return "Not found"

        args, varargs, varkw, defaults = getargspec(function)
        if ismethod(function):
            del args[0]

        if len(args) == 0 or len(request.postpath) > 3 or len(request.args) > 0:
            return self.render_POST(request)

        return self.form.render(args=args).encode('utf-8')

class SourceFactory(IbidSourceFactory):

    port = 8080
    host = 'localhost'

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        root = Index(self.name)
        root.putChild('', Index(self.name))
        root.putChild('message', Message(name))
        root.putChild('plugin', Plugin(name))
        root.putChild('static', static.File(resource_filename('ibid', 'static')))
        self.site = server.Site(root)

    def setServiceParent(self, service):
            if service:
                return internet.TCPServer(self.port, self.site).setServiceParent(service)
            else:
                reactor.listenTCP(self.port, self.site)

# vi: set et sta sw=4 ts=4:
