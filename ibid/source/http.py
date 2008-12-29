from twisted.web import server, resource
from twisted.application import internet

import ibid
from ibid.source import IbidSourceFactory
from ibid.event import Event

class IbidRequest(resource.Resource):
	isLeaf = True
	requests = {}

	def render_GET(self, request):
		ibid.sources['http'].respond = self.respond
		event = Event('http', 'message')
		event.sender = 'http'
		event.channel = 'http'
		event.addressed = True
		event.public = False
		event.who = event.sender
		event.sender_id = event.sender
		event.message = request.args['m'][0]
		event.id = request
		ibid.dispatcher.dispatch(event)
		return server.NOT_DONE_YET

	def respond(self, response):
		request = response['id']
		request.write(response['reply'].encode('latin-1'))
		request.finish()

class SourceFactory(IbidSourceFactory):

	def __init__(self, name):
		IbidSourceFactory.__init__(self, name)
		self.site = server.Site(IbidRequest())

	def setServiceParent(self, service):
		internet.TCPServer(8080, self.site).setServiceParent(service)
