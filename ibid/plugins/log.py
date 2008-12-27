"""Logs messages sent and received."""

import time

import ibid
from ibid.plugins import Processor, match

class Log(Processor):

    addressed = False
    processed = True
    priority = 1900

    def __init__(self, name):
        Processor.__init__(self, name)
        self.log = open(ibid.config.plugins[self.name]['logfile'], 'a')

    @match(r'')
    def handler(self, event):
        then = time.strftime(u"%Y/%m/%d %H:%M:%S", time.localtime(event.time))
        now = time.strftime(u"%Y/%m/%d %H:%M:%S", time.localtime())
        self.log.write(u'%s %s: %s > %s: %s\n' % (then, event.source, event.sender, event.channel, event.message_raw))
        for response in event.responses:
            self.log.write(u'%s %s: %s > %s: %s\n' % (now, event.source, ibid.config['botname'], response['target'], response['reply']))
        self.log.flush()

# vi: set et sta sw=4 ts=4:
