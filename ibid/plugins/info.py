import time
from subprocess import Popen, PIPE

from nickometer import nickometer

import ibid
from ibid.plugins import Processor, match

help = {}

class DateTime(Processor):
    """(date|time)"""

    @match(r'^(?:date|time)$')
    def handler(self, event):
        reply = time.strftime(u"It is %H:%M.%S on %a, %e %b %Y",time.localtime())
        event.addresponse(reply)
        return event

help['fortune'] = 'Returns a random fortune.'
class Fortune(Processor):
    """fortune"""
    feature = 'fortune'

    fortune = 'fortune'

    @match(r'^fortune$')
    def handler(self, event):
        fortune = Popen(self.fortune, stdout=PIPE, stderr=PIPE)
        output, error = fortune.communicate()
        code = fortune.wait()

        if code == 0:
            event.addresponse(output.strip())
        else:
            event.addresponse(u"Couldn't execute fortune")

        return event

help['nickometer'] = 'Calculates how lame a nick is.'
class Nickometer(Processor):
    """nickometer [<nick>] [with reasons]"""
    feature = 'nickometer'
    
    @match(r'^(?:nick|lame)-?o-?meter(?:(?:\s+for)?\s+(.+?))?(\s+with\s+reasons)?$')
    def handle_nickometer(self, event, nick, wreasons):
        nick = nick or event.who
        score, reasons = nickometer(str(nick))
        print reasons
        event.addresponse(u"%s is %s%% lame" % (nick, score))
        if wreasons:
            event.addresponse(', '.join(['%s (%s)' % reason for reason in reasons]))

# vi: set et sta sw=4 ts=4:
