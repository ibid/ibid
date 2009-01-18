"""Logs messages sent and received."""

from time import time, localtime
from os.path import dirname, join
from os import makedirs

import ibid
from ibid.plugins import Processor, match, handler

class Log(Processor):

    addressed = False
    processed = True
    priority = 1900
    log = 'logs/%(source)s.%(channel)s.%(year)d.%(month)02d.log'
    message_format = '%(year)d/%(month)02d/%(day)02d %(hour)02d:%(minute)02d:%(second)02d <%(who)s> %(message)s'
    presence_format = '%(year)d/%(month)02d/%(day)02d %(hour)02d:%(minute)02d:%(second)02d %(who)s (%(sender)s) is now %(state)s'
    logs = {}

    def get_logfile(self, source, channel, when):
        when = localtime(when)
        if ibid.config.sources[source]['type'] == 'jabber':
            channel = channel.split('/')[0]
        filename = self.log %   {   'source': source,
                                    'channel': channel,
                                    'year': when[0],
                                    'month': when[1],
                                    'day': when[2],
                                }
        filename = join(ibid.options['base'], filename)
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

    def log_message(self, file, source, channel, sender_id, sender, who, when, message):
        when = localtime(when)
        file.write(self.message_format %    {   'source': source,
                                                'channel': channel,
                                                'sender': sender,
                                                'sender_id': sender_id,
                                                'who': who,
                                                'message': message,
                                                'year': when[0],
                                                'month': when[1],
                                                'day': when[2],
                                                'hour': when[3],
                                                'minute': when[4],
                                                'second': when[5],
                                            } + '\n')
        file.flush()

    def log_presence(self, file, source, channel, sender_id, sender, who, when, state):
        when = localtime(when)
        file.write(self.presence_format %   {   'source': source,
                                                'channel': channel,
                                                'sender_id': sender_id,
                                                'sender': sender,
                                                'who': who,
                                                'state': state,
                                                'year': when[0],
                                                'month': when[1],
                                                'day': when[2],
                                                'hour': when[3],
                                                'minute': when[4],
                                                'second': when[5],
                                            } + '\n')
        file.flush()

    def process(self, event):
        if event.type == 'message':
            self.log_message(self.get_logfile(event.source, event.channel, event.time), event.source, event.channel, event.sender_id, event.sender, event.who, event.time, event.message_raw)

        elif event.type == 'state':
            self.log_presence(self.get_logfile(event.source, event.channel, time()), event.source, event.channel, event.sender_id, event.sender, event.who, time(), event.state)

        for response in event.responses:
            if 'reply' in response and isinstance(response['reply'], basestring):
                self.log_message(self.get_logfile(response['source'], response['target'], time()), response['source'], response['target'], ibid.config['botname'], ibid.config['botname'], ibid.config['botname'], time(), response['reply'])

# vi: set et sta sw=4 ts=4:
