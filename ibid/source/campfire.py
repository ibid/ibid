import logging
from socket import timeout
from urlparse import urlparse

from pinder import Campfire
from twisted.application import internet

import ibid
from ibid import AuthException, SourceException
from ibid.event import Event
from ibid.config import Option, ListOption
from ibid.source import IbidSourceFactory

class CampfireBot(Campfire):

    def __init__(self, factory):
        self.factory = factory
        super(CampfireBot, self).__init__(self.factory.subdomain)
        self.uri = urlparse('http://%s.campfirenow.com' % self.factory.subdomain)
        self.rooms = {}
        self.factory.join = self.join
        self.factory.leave = self.leave
        self.factory.send = self.send

    def run_one(self):
        if not self.logged_in:
            if not self.login(self.factory.username, self.factory.password):
                raise AuthException(u"Login failed")
            for room in self.factory.rooms:
                self.join(room)

        for room in self.rooms.values():
            try:
                messages = room.messages()
            except timeout, e:
                self.factory.log.debug(u"Campfire timed out on us")
                break
            for message in messages:
                self.factory.log.debug('Received message: %s', str(message))
                self._create_message(message, room.name)

    def _create_message(self, message, room):
        event = Event(self.factory.name, u'message')
        event.sender['connection'] = event.sender['id'] = unicode(message['user_id'], 'utf-8', 'replace')
        event.sender['nick'] = unicode(message['username'], 'utf-8', 'replace')
        event.message = unicode(message['message'], 'utf-8', 'replace')
        event.channel = room
        event.public = True
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        if response['target'] not in self.rooms:
            raise SourceException(u"Invalid room")

        self.rooms[response['target']].speak(response['reply'].encode('utf-8'))
        self.factory.log.debug(u"Sent message to %s: %s", response['target'], response['reply'])

    def join(self, room):
        self.factory.log.info(u"Joining %s", room)
        room = self.find_or_create_room_by_name(room)
        if not room:
            return False

        room.join()
        self.rooms[room.name] = room

    def leave(self, room):
        if room not in self.rooms:
            return False

        self.factory.log.info(u"Leaving %s", room)
        self.rooms[room].leave()
        del self.rooms[room]

class SourceFactory(IbidSourceFactory):

    subdomain = Option('subdomain', 'Campfire subdomain')
    username = Option('username', 'Email address')
    password = Option('password', 'Campfire password')
    rooms = ListOption('rooms', 'Rooms to join', [])

    def __init__(self, name):
        super(SourceFactory, self).__init__(name)
        self.bot = CampfireBot(self)
        self.log = logging.getLogger('source.%s' % self.name)

    def run_one(self):
        try:
            self.bot.run_one()
        except Exception, e:
            self.log.exception(u"Error while polling")

    def setServiceParent(self, service):
        self.timer = internet.TimerService(5, self.run_one)
        if service is None:
            self.timer.startService()
        else:
            self.timer.setServiceParent(service)

    def disconnect(self):
        self.bot.logout()
        self.timer.stopService()

# vi: set et sta sw=4 ts=4:
