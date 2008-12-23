import time

import ibid
from ibid.module import Module
from ibid.decorators import *

class Log(Module):

    def __init__(self, name):
        Module.__init__(self, name)
        self.log = open(ibid.config.modules[self.name]['logfile'], 'a')

    @message
    def process(self, event):
        then = time.strftime(u"%Y/%m/%d %H:%M:%S", time.localtime(event.time))
        now = time.strftime(u"%Y/%m/%d %H:%M:%S", time.localtime())
        self.log.write(u'%s %s: %s > %s: %s\n' % (then, event.source, event.user, event.channel, event.message))
        for response in event.responses:
            self.log.write(u'%s %s: %s > %s: %s\n' % (now, event.source, ibid.config['name'], response['target'], response['reply']))
        self.log.flush()

# vi: set et sta sw=4 ts=4:
