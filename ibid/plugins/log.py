# -*- coding: utf-8 -*-
# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera, Adrianna Pińska
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

"""Logs messages sent and received."""

from datetime import datetime
from errno import EEXIST
import fnmatch
import logging
from os.path import dirname, join, expanduser
from os import chmod, makedirs
from threading import Lock
from weakref import WeakValueDictionary

from dateutil.tz import tzlocal, tzutc

import ibid
from ibid.plugins import Processor, handler
from ibid.config import Option, BoolOption, IntOption, ListOption
from ibid.event import Event

log = logging.getLogger('plugins.log')

class Log(Processor):

    addressed = False
    processed = True
    event_types = (u'message', u'state', u'action', u'notice')
    priority = 1900

    log = Option('log', 'Log file to log messages to. Can contain substitutions: source, channel, year, month, day',
            'logs/%(year)d/%(month)02d/%(source)s/%(channel)s.log')

    timestamp_format = Option('timestamp_format', 'Format to substitute %(timestamp)s with', '%Y-%m-%d %H:%M:%S%z')
    date_utc = BoolOption('date_utc', 'Log with UTC timestamps', False)

    message_format = Option('message_format', 'Format string for messages',
            u'%(timestamp)s <%(sender_nick)s> %(message)s')
    action_format = Option('action_format', 'Format string for actions',
            u'%(timestamp)s * %(sender_nick)s %(message)s')
    notice_format = Option('notice_format', 'Format string for notices',
            u'%(timestamp)s -%(sender_nick)s- %(message)s')
    presence_format = Option('presence_format', 'Format string for presence events',
            u'%(timestamp)s %(sender_nick)s (%(sender_connection)s) is now %(state)s')
    rename_format = Option('rename_format', 'Format string for rename events',
            u'%(timestamp)s %(sender_nick)s (%(sender_connection)s) has renamed to %(new_nick)s')

    public_logs = ListOption('public_logs',
            u'List of source:channel globs for channels which should have public logs',
            [])
    public_mode = Option('public_mode',
            u'File Permissions mode for public channels, in octal', '644')
    private_mode = Option('private_mode',
            u'File Permissions mode for private chats, in octal', '640')
    dir_mode = Option('dir_mode',
            u'Directory Permissions mode, in octal', '755')

    blacklist = ListOption('blacklist',
            u'List of source:channel globs for channels which should not be logged (the whitelist overrides the blacklist)',
            [])
    whitelist = ListOption('whitelist',
            u'List of source:channel globs for channels which should be logged (the whitelist overrides the blacklist)',
            [])

    fd_cache = IntOption('fd_cache', 'Number of log files to keep open.', 5)

    lock = Lock()
    logs = WeakValueDictionary()
    # Ensures that recently used FDs are still available in logs:
    recent_logs = []

    def setup(self):
        sources = list(set(ibid.config.sources.keys())
                       | set(ibid.sources.keys()))
        for globlistname in ["public_logs", "blacklist", "whitelist"]:
            for glob in getattr(self, globlistname):
                if u':' not in glob:
                    log.warning(u"%s configuration values must follow the "
                                u"format source:channel. \"%s\" doesn't contain a "
                                u"colon.", globlistname, glob)
                    continue
                source_glob = glob.split(u':', 1)[0]
                if not fnmatch.filter(sources, source_glob):
                    log.warning(u'%s includes "%s", but there is no '
                                u'configured source matching "%s"',
                                globlistname, glob, source_glob)

    def get_channel(self, event):
        if event.channel is not None:
            return ibid.sources[event.source].logging_name(event.channel)
        return ibid.sources[event.source].logging_name(event.sender['id'])

    def matches(self, event, globlist):
        channel = self.get_channel(event)

        for glob in globlist:
            if u':' not in glob:
                continue
            source_glob, channel_glob = glob.split(u':', 1)
            if (fnmatch.fnmatch(event.source, source_glob)
                    and fnmatch.fnmatch(channel, channel_glob)):
                return True

        return False

    def get_logfile(self, event):
        self.lock.acquire()
        try:
            when = event.time
            if not self.date_utc:
                when = when.replace(tzinfo=tzutc()).astimezone(tzlocal())

            channel = self.get_channel(event)

            filename = self.log % {
                    'source': event.source.replace('/', '-'),
                    'channel': channel.replace('/', '-'),
                    'year': when.year,
                    'month': when.month,
                    'day': when.day,
                    'hour': when.hour,
                    'minute': when.minute,
                    'second': when.second,
            }
            filename = join(ibid.options['base'], expanduser(filename))
            log = self.logs.get(filename, None)
            if log is None:
                try:
                    makedirs(dirname(filename), int(self.dir_mode, 8))
                except OSError, e:
                    if e.errno != EEXIST:
                        raise e

                log = open(filename, 'a')
                self.logs[filename] = log

                if self.matches(event, self.public_logs):
                    chmod(filename, int(self.public_mode, 8))
                else:
                    chmod(filename, int(self.private_mode, 8))
            else:
                # recent_logs is an LRU cache, we'll be moving log to the
                # front of the queue, if it's in the queue.
                # It might not be, GCs are fickle LP: 655645
                try:
                    self.recent_logs.remove(log)
                except ValueError:
                    pass

            self.recent_logs = [log] + self.recent_logs[:self.fd_cache - 1]
            return log
        finally:
            self.lock.release()

    def log_event(self, event):
        if self.matches(event, self.blacklist) and not self.matches(event, self.whitelist):
            return

        when = event.time
        if not self.date_utc:
            when = when.replace(tzinfo=tzutc()).astimezone(tzlocal())

        format = {
                'message': self.message_format,
                'state': self.presence_format,
                'action': self.action_format,
                'notice': self.notice_format,
            }[event.type]

        # We get two events on a rename, ignore one of them
        if event.type == 'state' and hasattr(event, 'othername'):
            if event.state == 'online':
                return
            format = self.rename_format

        fields = {
                'source': event.source,
                'channel': event.channel,
                'sender_connection': event.sender['connection'],
                'sender_id': event.sender['id'],
                'sender_nick': event.sender['nick'],
                'timestamp': unicode(
                    when.strftime(self.timestamp_format.encode('utf8')),
                    'utf8')
        }

        if event.type == 'state':
            if hasattr(event, 'othername'):
                fields['new_nick'] = event.othername
            else:
                fields['state'] = event.state
        elif isinstance(event.message, dict):
            fields['message'] = event.message['raw']
        else:
            fields['message'] = event.message

        file = self.get_logfile(event)

        file.write((format % fields).encode('utf-8') + '\n')
        file.flush()

    @handler
    def log_handler(self, event):
        self.log_event(event)

        for response in event.responses:
            if 'reply' in response and isinstance(response['reply'], basestring):
                type = 'message'
                if response.get('action', False):
                    type = 'action'
                elif response.get('notice', False):
                    type = 'notice'
                e = Event(response['source'], type)
                e.source = response['source']
                e.channel = response['target']
                e.time = datetime.utcnow()
                e.sender = {
                    'id': ibid.config['botname'],
                    'connection': ibid.config['botname'],
                    'nick': ibid.config['botname'],
                }
                e.message = response['reply']
                self.log_event(e)

# vi: set et sta sw=4 ts=4:
