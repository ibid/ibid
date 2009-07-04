"""Logs messages sent and received."""

from time import time, localtime
from os.path import dirname, join, expanduser
from os import makedirs

import ibid
from ibid.plugins import Processor
from ibid.config import Option
from ibid.event import Event

class Log(Processor):

    addressed = False
    processed = True
    priority = 1900
    log = Option('log', 'Log file to log messages to. Can contain substitutions.',
            'logs/%(source)s.%(channel)s.%(year)d.%(month)02d.log')
    message_format = Option('message_format', 'Format string for messages',
            u'%(year)d/%(month)02d/%(day)02d %(hour)02d:%(minute)02d:%(second)02d <%(sender_nick)s> %(message)s')
    action_format = Option('action_format', 'Format string for actions',
            u'%(year)d/%(month)02d/%(day)02d %(hour)02d:%(minute)02d:%(second)02d  * %(sender_nick)s %(message)s')
    presence_format = Option('presence_format', 'Format string for presence events',
            u'%(year)d/%(month)02d/%(day)02d %(hour)02d:%(minute)02d:%(second)02d %(sender_nick)s (%(sender_connection)s) is now %(state)s')
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

    def log_event(self, event):
        if event.type in ('message', 'state', 'action'):
            when = localtime(event.time)

            format = {
                    'message': self.message_format,
                    'state': self.presence_format,
                    'action': self.action_format,
                }[event.type]

            fields = {
                    'source': event.source,
                    'channel': event.channel,
                    'sender_connection': event.sender['connection'],
                    'sender_id': event.sender['id'],
                    'sender_nick': event.sender['nick'],
                    'year': when.tm_year,
                    'month': when.tm_mon,
                    'day': when.tm_mday,
                    'hour': when.tm_hour,
                    'minute': when.tm_min,
                    'second': when.tm_sec,
            }

            if event.type == 'state':
                fields['state'] = event.state
            elif isinstance(event.message, dict):
                fields['message'] = event.message['raw']
            else:
                fields['message'] = event.message

            file = self.get_logfile(event.source, event.channel, event.time)

            file.write((format % fields).encode('utf-8') + '\n')
            file.flush()

    def process(self, event):
        self.log_event(event)

        for response in event.responses:
            if 'reply' in response and isinstance(response['reply'], basestring):
                e = Event(response['source'],
                        'action' in response and 'action' or 'message')
                e.source = response['source']
                e.channel = response['target']
                e.time = time()
                e.sender = {
                    'id': ibid.config['botname'],
                    'connection': ibid.config['botname'],
                    'nick': ibid.config['botname'],
                }
                e.message = response['reply']
                self.log_event(e)

# vi: set et sta sw=4 ts=4:
