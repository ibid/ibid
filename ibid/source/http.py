# Copyright (c) 2008-2010, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import logging
import os

from twisted.web import server, resource, static, xmlrpc, soap
from twisted.application import internet
from twisted.internet import reactor
from jinja2 import Environment, FileSystemLoader

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event
from ibid.config import Option, IntOption
from ibid.utils import locate_resource

templates = Environment(loader=FileSystemLoader(
        os.path.abspath(locate_resource('ibid', 'templates'))))

class Index(resource.Resource):

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name
        self.log = logging.getLogger('source.%s' % name)
        self.template = templates.get_template('index.html')

    def render_GET(self, request):
        return self.template.render(rpc=ibid.rpc.keys()).encode('utf-8')

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
        event.sender['nick'] = event.sender['id'] = event.sender['connection'] = event.channel = unicode(request.transport.getPeer().host)
        event.addressed = True
        event.public = False
        event.message = unicode(request.args['m'][0], 'utf-8', 'replace')
        self.log.debug(u"Received GET request from %s: %s", event.sender['connection'], event.message)
        ibid.dispatcher.dispatch(event).addCallback(self.respond, request)
        return server.NOT_DONE_YET

    def respond(self, event, request):
        output = '\n'.join([response['reply'].encode('utf-8') for response in event.responses])
        request.setHeader('Content-Type', 'text/plain; charset=utf-8')
        request.write(output)
        request.finish()
        self.log.debug(u"Responded to request from %s: %s", event.sender['connection'], output)

class Plugin(resource.Resource):

    def __init__(self, name, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)
        self.name = name

    def getChild(self, path, request):
        return path in ibid.rpc and ibid.rpc[path] or None

class XMLRPC(xmlrpc.XMLRPC):

    def _getFunction(self, functionPath):
        if functionPath.find(self.separator) != -1:
            plugin, functionPath = functionPath.split(self.separator, 1)
            object = ibid.rpc[plugin]
        else:
            object = self

        return getattr(object, 'remote_%s' % functionPath)

class SOAP(soap.SOAPPublisher):

    separator = '.'

    def lookupFunction(self, functionName):
        if functionName.find(self.separator) != -1:
            plugin, functionName = functionName.split(self.separator, 1)
            object = ibid.rpc[plugin]
        else:
            object = self

        return getattr(object, 'remote_%s' % functionName)

class SourceFactory(IbidSourceFactory):

    port = IntOption('port', 'Port number to listen on', 8080)
    myurl = Option('url', 'URL to advertise')

    def __init__(self, name):
        IbidSourceFactory.__init__(self, name)
        root = Plugin(name)
        root.putChild('', Index(name))
        root.putChild('message', Message(name))
        root.putChild('static', static.File(locate_resource('ibid', 'static')))
        root.putChild('RPC2', XMLRPC())
        root.putChild('SOAP', SOAP())
        self.site = server.Site(root)

    def setServiceParent(self, service):
        if service:
            return internet.TCPServer(self.port, self.site).setServiceParent(service)
        else:
            reactor.listenTCP(self.port, self.site)

    def url(self):
        return self.myurl

# vi: set et sta sw=4 ts=4:
