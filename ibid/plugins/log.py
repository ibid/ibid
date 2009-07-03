"""Logs messages sent and received."""

from time import time, localtime
from os.path import dirname, join, expanduser
from os import makedirs

import ibid
from ibid.plugins import Processor
from ibid.config import Option

class Log(Processor):

    addressed = False
    processed = True
    priority = 1900
    log = Option('log', 'Log file to log messages to. Can contain substitutions.', 'logs/%(source)s.%(channel)s.%(year)d.%(month)02d.log')
    message_format = Option('message_format', 'Format string for messages', '%(year)d/%(month)02d/%(day)02d %(hour)02d:%(minute)02d:%(second)02d <%(sender_nick)s> %(message)s')
    presence_format = Option('presence_format', 'Format string for presence events', '%(year)d/%(month)02d/%(day)02d %(hour)02d:%(minute)02d:%(second)02d %(sender_nick)s (%(sender_connection)s) is now %(state)s')
    logs = {}

    def get_logfile(self, source, channel, when):
        when = localtime(when)
        if ibid.sources[source].type == 'jabber':
            channel = channel.split('/')[0]
        filename = self.log %   {   'source': source.replace('/', '-'),
                                    'channel': channel.replace('/', '-'),
                                    'year': when[0],
                                    'month': when[1],
                                    'day': when[2],
                                }
        filename = join(ibid.options['base'], expanduser(filename))
        if filename not in self.logs:
            try:
                makedirs(dirname(filename))
            except OSError, e:
                if e.errno != 17:
                    raise e

            file = open(filename, 'a')
            self.logs[filename] = [file, None]

        self.logs[filename][1] = time()
        return self.logs[filename][0]

    def log_message(self, file, source, channel, sender, when, message):
        when = localtime(when)
        file.write((self.message_format %    {   'source': source,
                                                'channel': channel,
                                                'sender_connection': sender['connection'],
                                                'sender_id': sender['id'],
                                                'sender_nick': sender['nick'],
                                                'message': message,
                                                'year': when[0],
                                                'month': when[1],
                                                'day': when[2],
                                                'hour': when[3],
                                                'minute': when[4],
                                                'second': when[5],
                                            }).encode('utf-8') + '\n')
        file.flush()

    def log_presence(self, file, source, channel, sender, when, state):
        when = localtime(when)
        file.write((self.presence_format %   {   'source': source,
                                                'channel': channel,
                                                'sender_connection': sender['connection'],
                                                'sender_id': sender['id'],
                                                'sender_nick': sender['nick'],
                                                'state': state,
                                                'year': when[0],
                                                'month': when[1],
                                                'day': when[2],
                                                'hour': when[3],
                                                'minute': when[4],
                                                'second': when[5],
                                            }).encode('utf-8') + '\n')
        file.flush()

    def process(self, event):
        if event.type == 'message':
            self.log_message(self.get_logfile(event.source, event.channel, event.time), event.source, event.channel, event.sender, event.time, event.message['raw'])

        elif event.type == 'state':
            self.log_presence(self.get_logfile(event.source, event.channel, time()), event.source, event.channel, event.sender, time(), event.state)

        bot = { 'id': ibid.config['botname'],
                'connection': ibid.config['botname'],
                'nick': ibid.config['botname'],
              }
        for response in event.responses:
            if 'reply' in response and isinstance(response['reply'], basestring):
                self.log_message(self.get_logfile(response['source'], response['target'], time()), response['source'], response['target'], bot, time(), response['reply'])

# vi: set et sta sw=4 ts=4:
