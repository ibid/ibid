from time import sleep
import logging

from twisted.internet import reactor

import ibid
from ibid.plugins import Processor, match
from ibid.config import IntOption
from ibid.utils import ibid_version

help = {}
log = logging.getLogger('plugins.misc')

help['coffee'] = u"Times coffee brewing and reserves cups for people"
class Coffee(Processor):
    u"""coffee (on|please)"""
    feature = 'coffee'

    pots = {}

    time = IntOption('coffee_time', u'Brewing time in seconds', 240)
    cups = IntOption('coffee_cups', u'Maximum number of cups', 4)
    
    def coffee_announce(self, source, channel):
        try:
            ibid.dispatcher.send({
                'reply': u"Coffee's ready for %s!" % u', '.join(self.pots[(source, channel)]),
                'source': source,
                'target': channel,
            })
            del self.pots[(source, channel)]
        except:
            log.exception('Coffee callback')

    @match(r'^coffee\s+on$')
    def coffee_on(self, event):
        if (event.source, event.channel) in self.pots:
            event.addresponse(u"There's already a pot on")
            return
        
        self.pots[(event.source, event.channel)] = [event.sender['nick']]
        reactor.callLater(float(self.time), self.coffee_announce, event.source, event.channel)

        event.addresponse({'action': True, 'reply': u'flips the salt-timer'})
    
    @match('^coffee\s+(?:please|pls)$')
    def coffee_accept(self, event):
        if (event.source, event.channel) not in self.pots:
            event.addresponse(u"There isn't a pot on")

        elif len(self.pots[(event.source, event.channel)]) >= self.cups:
            event.addresponse(u"Sorry, there aren't any more cups left")

        elif event.sender['nick'] in self.pots[(event.source, event.channel)]:
            event.addresponse(u"Now now, we don't want anyone getting caffine overdoses")

        else:
            self.pots[(event.source, event.channel)].append(event.sender['nick'])
            event.addresponse(True)

help['version'] = u"Show the Ibid version currently running"
class Version(Processor):
    u"""version"""
    feature = 'version'

    @match(r'^version$')
    def show_version(self, event):
        if ibid_version():
            event.addresponse(u'I am version %s', ibid_version())
        else:
            event.addresponse(u"I don't know what version I am :-(")

help['dvorak'] = u"Makes text typed on a QWERTY keyboard as if it was Dvorak work, and vice-versa"
class Dvorak(Processor):
    u"""(aoeu|asdf) <text>"""
    feature = 'dvorak'
    
    # List of characters on each keyboard layout
    dvormap = u"""',.pyfgcrl/=aoeuidhtns-;qjkxbmwvz"<>PYFGCRL?+AOEUIDHTNS_:QJKXBMWVZ[]{}|"""
    qwermap = u"""qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?-=_+|"""
    
    # Typed by a QWERTY typist on a Dvorak-mapped keyboard
    typed_on_dvorak = dict(zip(map(ord, dvormap), qwermap))
    # Typed by a Dvorak typist on a QWERTY-mapped keyboard
    typed_on_qwerty = dict(zip(map(ord, qwermap), dvormap))
    
    @match(r'^(?:asdf|dvorak)\s+(.+)$')
    def convert_from_qwerty(self, event, text):
        event.addresponse(text.translate(self.typed_on_qwerty))
    
    @match(r'^(?:aoeu|qwerty)\s+(.+)$')
    def convert_from_dvorak(self, event, text):
        event.addresponse(text.translate(self.typed_on_dvorak))

# vi: set et sta sw=4 ts=4:
