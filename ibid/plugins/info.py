from subprocess import Popen, PIPE
import os
from unicodedata import normalize

from nickometer import nickometer

from ibid.plugins import Processor, match, RPC
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output

help = {}

help['fortune'] = u'Returns a random fortune.'
class Fortune(Processor, RPC):
    u"""fortune"""
    feature = 'fortune'

    fortune = Option('fortune', 'Path of the fortune executable', 'fortune')

    def __init__(self, name):
        super(Fortune, self).__init__(name)
        RPC.__init__(self)

    def setup(self):
        if not file_in_path(self.fortune):
            raise Exception("Cannot locate fortune executable")

    @match(r'^fortune$')
    def handler(self, event):
        fortune = self.remote_fortune()
        if fortune:
            event.addresponse(fortune)
        else:
            event.addresponse(u"Couldn't execute fortune")

    def remote_fortune(self):
        fortune = Popen(self.fortune, stdout=PIPE, stderr=PIPE)
        output, error = fortune.communicate()
        code = fortune.wait()

        output = unicode_output(output.strip(), 'replace')
        output = output.replace(u'\t', u' ').replace(u'\n', u' ')

        if code == 0:
            return output
        else:
            return None

help['nickometer'] = u'Calculates how lame a nick is.'
class Nickometer(Processor):
    u"""nickometer [<nick>] [with reasons]"""
    feature = 'nickometer'
    
    @match(r'^(?:nick|lame)-?o-?meter(?:(?:\s+for)?\s+(.+?))?(\s+with\s+reasons)?$')
    def handle_nickometer(self, event, nick, wreasons):
        nick = nick or event.sender['nick']
        if u'\ufffd' in nick:
            score, reasons = 100., ((u'Not UTF-8 clean', u'infinite'),)
        else:
            score, reasons = nickometer(normalize('NFKD', nick).encode('ascii', 'ignore'))

        event.addresponse(u'%(nick)s is %(score)s%% lame', {
            'nick': nick,
            'score': score,
        })
        if wreasons:
            if not reasons:
                reasons = ((u'A good, traditional nick', 0),)
            event.addresponse(u'Because: %s', u', '.join(['%s (%s)' % reason for reason in reasons]))

help['man'] = u'Retrieves information from manpages.'
class Man(Processor):
    u"""man [<section>] <page>"""
    feature = 'man'

    man = Option('man', 'Path of the man executable', 'man')

    def setup(self):
        if not file_in_path(self.man):
            raise Exception("Cannot locate man executable")

    @match(r'^man\s+(?:(\d)\s+)?(\S+)$')
    def handle_man(self, event, section, page):
        command = [self.man, page]
        if section:
            command.insert(1, section)
        
        if page.strip().startswith("-"):
            event.addresponse(False)
            return

        env = os.environ.copy()
        env["COLUMNS"] = "500"

        man = Popen(command, stdout=PIPE, stderr=PIPE, env=env)
        output, error = man.communicate()
        code = man.wait()

        if code != 0:
            event.addresponse(u'Manpage not found')
        else:
            output = unicode_output(output.strip(), errors="replace")
            output = output.splitlines()
            index = output.index('NAME')
            if index:
                event.addresponse(output[index+1].strip())
            index = output.index('SYNOPSIS')
            if index:
                event.addresponse(output[index+1].strip())

# vi: set et sta sw=4 ts=4:
