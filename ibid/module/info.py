"""Retrieves various bits of information."""

import time
from subprocess import Popen, PIPE

from ibid.module import Module
from ibid.decorators import *

class DateTime(Module):
    """Usage: (date|time)"""

    @addressed
    @notprocessed
    @message
    @match('^\s*(?:date|time)\s*$')
    def process(self, event):
        reply = time.strftime(u"It is %H:%M.%S on %a, %e %b %Y",time.localtime())
        if event.public:
            reply = u'%s: %s' % (event.who, reply)

        event.addresponse(reply)
        return event

class Fortune(Module):
    """Usage: fortune"""

    @addressed
    @notprocessed
    @match('^\s*fortune\s*$')
    def process(self, event):
        fortune = Popen(['fortune'], stdout=PIPE, stderr=PIPE)
        output, error = fortune.communicate()
        code = fortune.wait()

        if code == 0:
            event.addresponse(output.strip())
        else:
            event.addresponse(u"Coludn't execute fortune")

        return event

# vi: set et sta sw=4 ts=4:
