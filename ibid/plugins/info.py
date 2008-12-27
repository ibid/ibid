"""Retrieves various bits of information."""

import time
from subprocess import Popen, PIPE

import ibid
from ibid.plugins import Processor, match

class DateTime(Processor):
    """Usage: (date|time)"""

    @match('^\s*(?:date|time)\s*$')
    def handler(self, event):
        reply = time.strftime(u"It is %H:%M.%S on %a, %e %b %Y",time.localtime())
        event.addresponse(reply)
        return event

class Fortune(Processor):
    """Usage: fortune"""

    @match('^\s*fortune\s*$')
    def handler(self, event):
        command = 'fortune'
        if self.name in ibid.config.plugins and 'fortune' in ibid.config.plugins[self.name]:
            command = ibid.config.plugins[self.name]['fortune']

        fortune = Popen(command, stdout=PIPE, stderr=PIPE)
        output, error = fortune.communicate()
        code = fortune.wait()

        if code == 0:
            event.addresponse(output.strip())
        else:
            event.addresponse(u"Couldn't execute fortune")

        return event

# vi: set et sta sw=4 ts=4:
