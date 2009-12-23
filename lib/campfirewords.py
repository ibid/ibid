#!/usr/bin/env python
# Copyright 2009 Stefano Rivera <scripts@rivera.za.net>
# Released under the MIT license

# Speaks Campfire API protocol.

from base64 import b64encode
import logging

from twisted.internet import protocol, reactor, ssl
from twisted.web.client import HTTPPageGetter, HTTPClientFactory, getPage

from ibid.compat import json

log = logging.getLogger('campfire')

class HTTPStreamGetter(HTTPPageGetter):

    def connectionMade(self):
        log.debug(u'Stream Connected')
        self.__buffer = ''
        self.factory.stream_connected()
        HTTPPageGetter.connectionMade(self)

    def handleResponsePart(self, data):
        self.factory.keepalive_received()
        if self.__buffer == '' and data == ' ':
            return
        if '\r' in data:
            data = self.__buffer + data
            self.__buffer = ''
            for part in data.split('\r'):
                part = part.strip()
                if part != '':
                    self.factory.event(part)
        else:
            self.__buffer += data

class JSONStream(HTTPClientFactory, protocol.ReconnectingClientFactory):

    protocol = HTTPStreamGetter

    _reconnect_deferred = None

    def __init__(self, url, keepalive_timeout=0, *args, **kwargs):
        self.keepalive_timeout = keepalive_timeout
        HTTPClientFactory.__init__(self, url, *args, **kwargs)

    def connectionMade(self):
        HTTPClientFactory.connectionMade(self)
        self.keepalive_received()

    def keepalive_received(self):
        log.debug(u'We appear to be alive')
        if self._reconnect_deferred:
            self._reconnect_deferred.cancel()
        if self.keepalive_timeout:
            self._reconnect_deferred = reactor.callLater(self.keepalive_timeout,
                     self.keepalive_reconnect)

    def keepalive_reconnect(self):
        log.info(u'No keep-alive received in a while, reconnecting.')
        self._reconnect_deferred = None
        self.proto.transport.loseConnection()

class CampfireClient(object):

    subdomain = 'ibid'
    token = '7c6f164ef01eb3b75a52810ee145f28e8cd49f2a'
    rooms = ('Room 1',)
    keepalive_timeout = 10

    _streams = {}
    _rooms = {}
    _users = {}

    # Callbacks:
    def event(self, room_name, room_id, user_name, user_id, event_type, body):
        log.debug(u'Saw event: [%s] %s: %s in %s', event_type, user_name, body,
                  room_name)

    # Internal:
    def failure(self, failure, task):
        log.error(u'%s Request failed: %s', task, unicode(failure))
        self.disconnect()

    def disconnect(self):
        for id, stream in self._streams.iteritems():
            stream.proto.transport.loseConnection()
            self.leave_room(id)

    def connect(self):
        self.get_room_list()

    def get_room_list(self):
        self.get_data('rooms.json', (self.do_room_list,), 'room list')

    def do_room_list(self, data):
        roommeta = json.loads(data)['rooms']

        for room in roommeta:
            # We want this present before we get to room metadata
            self._rooms[room['id']] = {'name': room['name']}

            if room['name'] in self.rooms:
                logging.debug(u'Connecting to: %s', room['name'])

                self.join_room(room['id'])

    def leave_room(self, room_id, callback=None):
        log.debug('Leaving room: %i', room_id)
        self.get_data('room/%i/leave.json' % room_id, callback)

    def join_room(self, room_id):
        log.debug('Joining room: %i', room_id)
        self._streams[room_id] = stream = JSONStream(
                'https://streaming.campfirenow.com/room/%i/live.json' % room_id,
                keepalive_timeout=self.keepalive_timeout,
                headers={'Authorization': self.auth_header()})
        stream.event = self._event
        stream.stream_connected = lambda : self.joined_room(room_id)
        stream.clientConnectionLost = lambda connector, unused_reason: \
                self.stream_connection_lost(room_id)

        contextFactory = ssl.ClientContextFactory()
        stream.proto = reactor.connectSSL(
                'streaming.campfirenow.com', 443,
                stream, contextFactory)

    def stream_connection_lost(self, room_id):
        log.debug('Connection Lost: %i', room_id)
        self.leave_room(room_id, (lambda x, y: self.join_room(y), room_id))

    def joined_room(self, room_id):
        self.get_data('room/%i/join.json' % room_id)
        self.get_data('room/%i.json' % room_id,
                      (self.do_room_info,), 'room info')

    def do_room_info(self, data):
        d = json.loads(data)['room']
        r = self._rooms[d['id']]
        for k, v in d.iteritems():
            if k != 'users':
                r[k] = v

        r['users'] = set()
        for user in d['users']:
            self._users[user['id']] = u = user
            r['users'].add(user['id'])

    def auth_header(self):
        return 'Basic ' + b64encode(self.token + ':')

    def base_url(self):
        return str('http://%s.campfirenow.com/' % self.subdomain)

    def get_data(self, path, callback=None, errback_description=None):
        d = getPage(self.base_url() + path, method='POST',
                    headers={'Authorization': self.auth_header()})
        if callback:
            d = d.addCallback(*callback)
        if errback_description:
            d = d.addErrback(self.failure, errback_description)
        return d

    def _event(self, data):
        log.debug(u'Received: %s', repr(data))
        d = json.loads(data)

        if d['type'] == 'TimestampMessage':
            return

        self.event(room_name=self._rooms[d['room_id']]['name'],
                   room_id=d['room_id'],
                   user_name=self._users[d['user_id']]['name'],
                   user_id=d['user_id'],
                   event_type=d['type'],
                   body=d['body'])

# Small testing framework:
def main():

    logging.basicConfig(level=logging.NOTSET)

    class TestClient(CampfireClient):
        pass

    t = TestClient()
    t.connect()

    reactor.run()

if __name__ == '__main__':
    main()

# vi: set et sta sw=4 ts=4:
