"""Logs messages sent and received."""

from time import time, localtime, strftime
from os.path import dirname
from os import makedirs

import ibid
from ibid.plugins import Processor, match, handler

class Log(Processor):

    addressed = False
    processed = True
    priority = 1900
    log = 'logs/%(source)s.%(where)s.%(year)d.%(month)02d.%(day)02d.log'

    def __init__(self, name):
        Processor.__init__(self, name)
        self.logs = {}

    def get_logfile(self, source, where, when):
        when = localtime(when)
        filename = self.log %   {   'source': source,
                                    'where': where,
                                    'year': when[0],
                                    'month': when[1],
                                    'day': when[2],
                                }
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

    def process(self, event):
        then = strftime(u"%Y/%m/%d %H:%M:%S", localtime(event.time))

        if event.type == 'message':
            now = strftime(u"%Y/%m/%d %H:%M:%S", localtime())
            self.get_logfile(event.source, event.channel, event.time).write(u'%s %s: %s > %s: %s\n' % (then, event.source, event.sender, event.channel, event.message_raw))
            for response in event.responses:
                self.get_logfile(response['source'], response['target'], time()).write(u'%s %s: %s > %s: %s\n' % (now, response['source'], ibid.config['botname'], response['target'], response['reply']))

        elif event.type == 'state':
            self.get_logfile(event.source, 'presence', time()).write(u'%s %s: %s is now %s\n' % (then, event.source, event.sender, event.state))

        else:
            return

# vi: set et sta sw=4 ts=4:
