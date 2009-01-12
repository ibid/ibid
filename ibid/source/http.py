from twisted.web import server, resource
from twisted.application import internet
from twisted.internet import reactor

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

class IbidRequest(resource.Resource):
	isLeaf = True

	def render_GET(self, request):
		ibid.sources['http'].respond = self.respond
		event = Event(u'http', u'message')
		event.sender = event.channel = u'http'
		event.addressed = True
		event.public = False
		event.who = event.sender
		event.sender_id = event.sender
		event.message = request.args['m'][0]
		ibid.dispatcher.dispatch(event).addCallback(self.respond, request)
		return server.NOT_DONE_YET

	def respond(self, event, request):
		for response in event.responses:
			request.write(response['reply'].encode('utf-8'))
		request.finish()

class SourceFactory(IbidSourceFactory):

	port = 8080

	def __init__(self, name):
		IbidSourceFactory.__init__(self, name)
		self.site = server.Site(IbidRequest())

	def setServiceParent(self, service):
            if service:
                return internet.TCPServer(self.port, self.site).setServiceParent(service)
            else:
                reactor.listenTCP(self.port, self.site)
