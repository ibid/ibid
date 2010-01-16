from unicodedata import normalize
from random import choice
import re

from nickometer import nickometer

from ibid.plugins import Processor, match

help = {}

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

help['choose'] = u'Choose one of the given options.'
class Choose(Processor):
    u"""choose <choice> or <choice>..."""
    feature = 'choose'

    choose_re = re.compile(r'(?:\s*,\s*(?:or\s+)?)|(?:\s+or\s+)', re.I)

    @match(r'^(?:choose|choice|pick)\s+(.+)$')
    def choose(self, event, choices):
        event.addresponse(u'I choose %s', choice(self.choose_re.split(choices)))

# vi: set et sta sw=4 ts=4:
