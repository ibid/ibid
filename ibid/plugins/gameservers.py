# Copyright (c) 2009-2010, Ben Steenhuisen, Stefano Rivera,
# Tslil Clingman, Marco Gallotta
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import re
import socket
import struct

from ibid.plugins import Processor, match
from ibid.config import Option, IntOption
from ibid.utils import human_join

features = {'gameservers': {
    'description': u'Lists the users on Game servers',
    'categories': ('lookup',),
}}

class Bnet(Processor):
    usage = u'dota players | who is playing dota'
    features = ('gameservers',)
    autoload = False

    bnet_host = Option('bnet_host', 'Bnet server hostname / IP', '127.0.0.1')
    bnet_port = IntOption('bnet_port', 'Bnet server port', 6112)
    bnet_user = Option('bnet_user', 'Bnet username', 'guest')
    bnet_pass = Option('bnet_pass', 'Bnet password', 'guest')

    def bnet_players(self, gametype):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.bnet_host, self.bnet_port))
        s.settimeout(5)
        s.send('\03%s\n%s\n/con\n/quit\n' % (self.bnet_user, self.bnet_pass))

        out = ""
        while (True):
            line = s.recv(1024)
            if line == "":
                break
            out += line

        s.close()

        player_re = re.compile(r'^1018 Idata "\s+bnet\s+%s\s+"(\S+?)"?\s+\d+\s+' % gametype)
        users = [player_re.match(line).group(1) for line in out.splitlines() if player_re.match(line)]
        users.sort()
        return users

    @match(r'^(?:dota\s+players|who(?:\'s|\s+is)\s+(?:playing\s+dota|on\s+bnet))$')
    def dota_players(self, event):
        users = self.bnet_players('W3XP')
        if users:
            event.addresponse(u'The battlefield contains %s', human_join(users))
        else:
            event.addresponse(u'Nobody. Everyone must have a lives...')

class CounterStrike(Processor):
    usage = u'cs players | who is playing cs'
    features = ('gameservers',)
    autoload = False

    cs_host = Option('cs_host', 'CS server hostname / IP', '127.0.0.1')
    cs_port = IntOption('cs_port', 'CS server port', 27015)

    @match(r'^(?:(?:cs|counter[\s-]*strike)\s+players|who(?:\'s|\s+is)\s+(?:playing|on)\s+(?:cs|counter[\s-]*strike))$')
    def cs_players(self, event):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        server.sendto('\xFF\xFF\xFF\xFFdetails', (self.cs_host, self.cs_port))
        server.settimeout(5)
        data = server.recv(16384)

        assert data.startswith('\xFF\xFF\xFF\xFFm')
        data = data[5:]

        address, hostname, map, mod, modname, details = data.split('\x00', 5)

        details = details[:5] # We don't care about the rest
        clientcount, clientmax, protocol, type, os = struct.unpack('<3Bcc', details)

        if clientcount == 0:
            event.addresponse(u'Nobody. Everyone must have lives...')
            return

        server.sendto('\xFF\xFF\xFF\xFFplayers', (self.cs_host, self.cs_port))
        data = server.recv(16384)

        assert data.startswith('\xFF\xFF\xFF\xFF')
        data = data[6:]

        players = []
        while data:
            player = {}
            data = data[1:]
            player['nickname'], data = data.split('\x00', 1)
            player['fragtotal'] = struct.unpack('<i', data[:4])[0]
            data = data[8:]
            players.append(player)

        players.sort(key=lambda x: x['fragtotal'], reverse=True)
        event.addresponse(u'There are %(clients)i/%(clientmax)s players playing %(map)s: %(players)s', {
            'clients': clientcount,
            'clientmax': clientmax,
            'map': map,
            'players': human_join(u'%s (%i)' % (p['nickname'], p['fragtotal']) for p in players),
        })

class Teeworlds(Processor):
    usage = u'teeworlds players <server>:<port>'
    features = ('gameservers',)
    autoload = False

    @match(r'^(?:tw|teeworlds)\s+players\s+([\d\D.]+):(\d+)$')
    def tw_players(self, event, tw_host, tw_port):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.settimeout(5)
        server.sendto(chr(255) * 10 + 'gief', (tw_host, int(tw_port)))
        data, _ = server.recvfrom(1024)
        data = data.split(chr(0))
        data[0] = data[0][data[0].find('info') + 4:]
        data = [d.decode('utf-8', 'ignore') for d in data]

        event.addresponse(u'%(host_name)s(%(host_version)s) has '
            '%(num_players)s of %(max_players)s players playing %(mode)s '
            'on %(map)s.', {
                'host_version': data[0],
                'host_name': data[1],
                'map': data[2],
                'mode': data[3],
                'num_players': data[6],
                'max_players': data[7],
            })
        if len(data) > 9:
            scores = zip(map(int, data[9::2]), data[8::2])
            scores.sort(reverse=True)
            event.addresponse('Scores: ' + human_join(
                ['%s = %d' % (score[1], score[0])for score in scores]))


# vi: set et sta sw=4 ts=4:
