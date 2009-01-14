import time
from subprocess import Popen, PIPE

from nickometer import nickometer

import ibid
from ibid.plugins import Processor, match

help = {}

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

help['man'] = 'Retrieves information from manpages.'
class Man(Processor):
    """man [<section>] <page>"""
    feature = 'man'

    man = 'man'

    @match(r'^man\s+(?:(\d)\s+)?(\S+)$')
    def handle_man(self, event, section, page):
        command = [self.man, page]
        if section:
            command.insert(1, section)
        man = Popen(command, stdout=PIPE, stderr=PIPE)
        output, error = man.communicate()
        code = man.wait()

        if code != 0:
            event.addresponse(u'Manpage not found')
        else:
            lines = output.splitlines()
            index = lines.index('NAME')
            if index:
                event.addresponse(lines[index+1].strip())
            index = lines.index('SYNOPSIS')
            if index:
                event.addresponse(lines[index+1].strip())
        

# vi: set et sta sw=4 ts=4:
