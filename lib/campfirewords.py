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
        self.resetDelay()

    def keepalive_received(self):
        if self._reconnect_deferred:
            self._reconnect_deferred.cancel()
        if self.keepalive_timeout:
            self._reconnect_deferred = reactor.callLater(self.keepalive_timeout,
                     self.keepalive_reconnect)

    def keepalive_reconnect(self):
        log.info(u'No keep-alive received in a while, reconnecting.')
        self._reconnect_deferred = None
        self.proto.transport.loseConnection()

    def disconnect(self):
        if self._reconnect_deferred:
            self._reconnect_deferred.cancel()
            self._reconnect_deferred = None
        self.stopTrying()
        self.proto.transport.loseConnection()


class RoomNameException(Exception):
    pass


class CampfireClient(object):

    # Configuration
    subdomain = ''
    secure = False
    token = ''
    rooms = ()
    keepalive_timeout = 10

    # Looked up
    my_id = 0
    my_name = ''

    _streams = {}
    _rooms = {}
    _users = {}
    _room_info_queue = []

    def __init__(self, subdomain, token, rooms, secure=False,
                 keepalive_timeout=10):
        self.subdomain = subdomain
        self.token = token
        self.rooms = rooms
        self.secure = secure
        self.keepalive_timeout = keepalive_timeout

    # Callbacks:
    def joined_room(self, room_info):
        pass

    # Actions:
    def say(self, room_name, message, type='TextMessage'):
        data = {
            'message': {
                'body': message,
                'type': type,
            }
        }

        self._get_data('room/%(room_id)i/speak.json',
                      self._locate_room(room_name), 'speak', method='POST',
                      headers={'Content-Type': 'application/json'},
                      postdata=json.dumps(data))

    def topic(self, room_name, topic):
        data = {'request': {'room': {'topic': topic}}}

        self._get_data('room/%(room_id)i.json',
                      self._locate_room(room_name), 'set topic', method='PUT',
                      headers={'Content-Type': 'application/json'},
                      postdata=json.dumps(data))

    # Internal:
    def _locate_room(self, room_name):
        if isinstance(room_name, int):
            return room_name
        else:
            rooms = [k for k, r in self._rooms.iteritems()
                                if r['name'] == room_name]
            if len(rooms) != 1:
                raise RoomNameException(room_name)

            return rooms[0]

    def disconnect(self):
        for id in self._streams.iterkeys():
            self.leave_room(id)

    def connect(self):
        self._get_id()

    def _get_id(self):
        log.debug(u'Finding my ID')
        self._get_data('users/me.json', None, 'my info') \
                .addCallback(self._do_get_id)

    def _do_get_id(self, data):
        log.debug(u'Parsing my info')
        meta = json.loads(data)['user']
        self.my_id = meta['id']
        self.my_name = meta['name']
        self.get_room_list()

    def get_room_list(self):
        log.debug(u'Getting room list')
        self._get_data('rooms.json', None, 'room list') \
                .addCallback(self._do_room_list)

    def _do_room_list(self, data):
        log.debug(u'Parsing room list')
        roommeta = json.loads(data)['rooms']

        for room in roommeta:
            # We want this present before we get to room metadata
            self._rooms[room['id']] = {'name': room['name']}

            if room['name'] in self.rooms:
                logging.debug(u'Connecting to: %s', room['name'])

                self.join_room(room['id'])

    def leave_room(self, room_id):
        log.debug('Leaving room: %i', room_id)
        if room_id in self._streams:
            del self._streams[room_id].clientConnectionLost
            self._streams[room_id].disconnect()
        return self._get_data('room/%(room_id)i/leave.json', room_id, None,
                              method='POST')

    def stream_failure(self, connector, unused_reason, room_id):
        log.error('Lost stream for room %i', room_id)
        self.join_room(room_id)

    def join_room(self, room_id):
        log.debug('Joining room: %i', room_id)
        self._streams[room_id] = stream = JSONStream(
                'https://streaming.campfirenow.com/room/%i/live.json' % room_id,
                keepalive_timeout=self.keepalive_timeout,
                headers={'Authorization': self._auth_header()})
        stream.event = self._event
        stream.stream_connected = lambda : self._joined_room(room_id)
        stream.clientConnectionLost = lambda connector, unused_reason: \
                self.stream_failure(connector, unused_reason, room_id)

        contextFactory = ssl.ClientContextFactory()
        stream.proto = reactor.connectSSL(
                'streaming.campfirenow.com', 443,
                stream, contextFactory)

    def _joined_room(self, room_id):
        self._get_data('room/%(room_id)i/join.json', room_id, 'join room',
                       method='POST')
        self.get_room_info(room_id, join=True)

    def get_room_info(self, room_id, join=False):
        self._get_data('room/%(room_id)i.json', room_id, 'room info') \
                .addCallback(self._do_room_info, join)

    def _do_room_info(self, data, join):
        d = json.loads(data)['room']
        r = self._rooms[d['id']]
        for k, v in d.iteritems():
            if k != 'users':
                r[k] = v

        r['users'] = set()
        for user in d['users']:
            self._users[user['id']] = u = user
            r['users'].add(user['id'])
        if join:
            self.joined_room(r)

        queue, self._room_info_queue = self._room_info_queue, []
        for room_id, item in queue:
            if room_id == d['id']:
                self._event(item)
            else:
                self._room_info_queue.append((room_id, item))

    def _auth_header(self):
        return 'Basic ' + b64encode(self.token + ':')

    def _base_url(self):
        protocol = self.secure and 'https' or 'http'
        return str('%s://%s.campfirenow.com/' % (protocol, self.subdomain))

    def _failed_get_data(self, failure, args):
        log.error(u'Campfire %s failed: %s', args['error_description'],
                  repr(failure))
        args['retry'] += 1
        if args['retry'] < 8:
            reactor.callLater(pow(2, args['retry']), self._get_data, **args)
        else:
            log.error(u'Gave up retrying to %s', args['error_description'])

    def _get_data(self, path, room_id, error_description=None, method='GET',
                 headers={}, postdata=None, retry=0):
        "Make a campfire API request"

        headers['Authorization'] = self._auth_header()
        if postdata is None and method in ('POST', 'PUT'):
            postdata = ''

        d = getPage(self._base_url() + path % {'room_id': room_id},
                    method=method, headers=headers, postdata=postdata)
        if error_description is not None:
            d = d.addErrback(self._failed_get_data, {
                'path': path,
                'room_id': room_id,
                'error_description': error_description,
                'method': method,
                'headers': headers,
                'postdata': postdata,
                'retry': retry,
            })
        return d

    def _event(self, data):
        "Handle a JSON stream event, data is the JSON"
        d = json.loads(data)

        if d['user_id'] == self.my_id:
            return

        type = d['type']
        if type.endswith('Message'):
            type = type[:-7]
        if type == 'Enter':
            self.get_room_info(d['room_id'])
        if hasattr(self, 'handle_' + type):
            params = {}
            params['room_id'] = d['room_id']
            params['room_name'] = self._rooms[d['room_id']]['name']
            if d.get('user_id') is not None:
                if d['user_id'] not in self._users:
                    # User list not loaded yet, stick it on a queue:
                    self._room_info_queue.append((d['room_id'], data))
                    return
                params['user_id'] = d['user_id']
                params['user_name'] = self._users[d['user_id']]['name']
            if d.get('body', None) is not None:
                params['body'] = d['body']

            getattr(self, 'handle_' + type)(**params)

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
