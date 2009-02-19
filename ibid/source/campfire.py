from pinder import Campfire
from twisted.application import internet

import ibid
from ibid import AuthException
from ibid.event import Event
from ibid.config import Option
from ibid.source import IbidSourceFactory

class CampfireBot(Campfire):

    def __init__(self, factory):
        self.factory = factory
        super(CampfireBot, self).__init__(self.factory.subdomain)
        self.rooms = {}
        self.factory.join = self.join
        self.factory.part = self.part
        self.factory.send = self.send

    def run_one(self):
        if not self.logged_in and not self.login(self.factory.username, self.factory.password):
            raise AuthException(u"Login failed")

        for room in self.rooms:
            for message in room.messages():
                self._create_message(message, room.name)

    def _create_message(message, room):
        event = Event(self.factory.name, u'message')
        event.sender = event.sender_id = message['user_id']
        event.who = message['username']
        event.message = message['message']
        event.channel = room
        event.public = True
        ibid.dispatcher.dispatch(event).addCallback(self.respond)

    def respond(self, event):
        for response in event.responses:
            self.send(response)

    def send(self, response):
        if response['target'] not in self.rooms:
            raise SourceException(u"Invalid room")

        self.speak(response['reply'].encode('utf-8'))

    def join(self, room):
        room = find_or_create_room_by_name(room)
        if not room:
            return False

        self.rooms[room.name] = room

    def part(self, room):
        if room not in self.rooms:
            return False

        self.rooms[room].leave()
        del self.rooms[room]

class SourceFactory(IbidSourceFactory):

    subdomain = Option('subdomain', 'Campfire subdomain')
    username = Option('username', 'Email address')
    password = Option('password', 'Campfire password')

    def __init__(self, name):
        super(SourceFactory, self).__init__(name)
        self.bot = CampfireBot(self)

    def run_one(self):
        self.bot.run_one()

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
