import logging

from campfirewords import CampfireClient

import ibid
from ibid.config import IntOption, Option, ListOption
from ibid.event import Event
from ibid.source import IbidSourceFactory

class CampfireBot(CampfireClient):

    def _create_event(self, type, user_id, user_name, room_id, room_name):
        event = Event(self.factory.name, type)
        if user_id is not None:
            user_id = unicode(user_id)
            user_name = unicode(user_name)
            event.sender['connection'] = user_id
            event.sender['id'] = user_id
            event.sender['nick'] = user_name
        event.channel = unicode(room_name)
        event.public = True
        event.source = self.factory.name
        return event

    def _message_event(self, body, type=u'message', **kwargs):
        event = self._create_event(type, **kwargs)
        event.message = unicode(body)
        self.factory.log.debug(u'Received %s from %s in %s: %s', type,
                               kwargs['user_name'], kwargs['room_name'], body)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def _state_event(self, state, **kwargs):
        event = self._create_event(u'state', **kwargs)
        event.state = state
        self.factory.log.debug(u'%s in %s is now %s', kwargs['user_name'],
                               kwargs['room_name'], state)
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def handle_Text(self, **kwargs):
        self._message_event(**kwargs)

    def handle_TopicChange(self, **kwargs):
        self._message_event(type=u'topic', **kwargs)

    def handle_Leave(self, **kwargs):
        self._state_event(state=u'offline', **kwargs)

    def handle_Enter(self, **kwargs):
        self._state_event(state=u'online', **kwargs)

    def joined_room(self, room_info):
        self._message_event(type=u'topic', body=room_info['topic'],
                            user_id=None, user_name=None,
                            room_id=room_info['id'],
                            room_name=room_info['name'])

    def send(self, response):
        message = response['reply']
        if response.get('action', False):
            message = u'*%s*' % message
        elif response.get('topic', False):
            self.topic(response['target'], message)
            return

        self.say(response['target'], message)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

class SourceFactory(IbidSourceFactory):

    auth = ('implicit',)
    supports = ('action', 'topic')

    subdomain = Option('subdomain', 'Campfire subdomain')
    token = Option('token', 'Campfire token')
    rooms = ListOption('rooms', 'Rooms to join', [])
    keepalive_timeout = IntOption('keepalive_timeout',
            'Stream keepalive timeout. '
            'Campfire sends a keepalive every <5 seconds', 30)

    def __init__(self, name):
        super(SourceFactory, self).__init__(name)
        self.log = logging.getLogger('source.%s' % self.name)
        self.client = CampfireBot()
        self.client.factory = self
        self.client.subdomain = self.subdomain
        self.client.token = self.token
        self.client.rooms = self.rooms
        self.client.keepalive_timeout = self.keepalive_timeout

    def setServiceParent(self, service):
        self.client.connect()

    def disconnect(self):
        self.client.disconnect()
        return True

    def url(self):
        return 'http://%s.campfirenow.com/' % self.subdomain

    def send(self, response):
        self.client.send(response)

# vi: set et sta sw=4 ts=4:
