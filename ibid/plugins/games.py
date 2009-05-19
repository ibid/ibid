import logging
from random import choice, gauss, random
import re
from time import sleep

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option, IntOption, BoolOption, FloatOption
from ibid.utils import ibid_version

help = {}
log = logging.getLogger('plugins.games')

help['shootout'] = u"Mexcan Shootout between channel members"
class Shootout(Processor):
    u"""[mexican] shootout [between] <user> [and] <user>
    bang|kapow|pewpew|holyhandgrenadeofantioch"""
    feature = 'shootout'

    addressed = BoolOption('addressed', 'Must the bot be addressed', True)

    extremities = Option('extremities', u'Extremities that can be hit', (
        u'toe', u'foot', u'leg', u'thigh', u'finger', u'hand', u'arm',
        u'elbow', u'shoulder', u'ear', u'nose', u'stomach',
    ))

    vitals = Option('vitals', 'Vital parts of the body that can be hit', (
        u'head', u'groin', u'chest', u'heart', u'neck',
    ))

    happy_endings = Option('happy_endings', 'Both survive', (
        u'walk off into the sunset', u'go for a beer', u'call it quits',
    ))

    weapons = Option('weapons', 'Weapons that can be used: name: (chance, damage)', {
        u'bang': (0.75, 70),
        u'kapow': (0.75, 90),
        u'pewpew': (0.75, 110),
        u'holyhandgrenadeofantioch': (1.0, 200),
    })

    timeout = IntOption('timeout', 'How long is a duel on for', 10)
    delay = FloatOption('delay', 'Countdown time', 3.0)
    duels = []
    
    @match(r'^(?:mexican\s+)?(?:shootout|standoff|du[ae]l)\s+(?:between\s+)?(\S+)\s+(?:and\s+)?(\S+)$')
    def initiate(self, event, a, b):
        if not event.addressed:
            return
        for combatent in (a, b):
            if [True for duel in self.duels if combatent.lower() in duel]:
                event.addresponse(u"%s is already at war", combatent)
                return
        
        if self.delay:
            sleep(gauss(self.delay, self.delay / 2))
            ibid.dispatcher.send({
                'reply': choice((
                    u'aaaand ... go!', u'5 ... 4 ... 3 ... 2 ... 1 ... fire !', u'match on!',
                )),
                'source': event.source,
                'target': event.channel,
            })

        duel = {a.lower(): [100.0, a], b.lower(): [100.0, b]}
        self.duels.append(duel)
        sleep(self.timeout)
        try:
            self.duels.remove(duel)
        except ValueError:
            event.processed = True
            return

        winner, loser = a.lower(), b.lower()
        if duel[winner] < duel[loser]:
            winner, loser = loser, winner

        if duel[loser][0] == 100.0:
            event.addresponse(u"DRAW: %(a)s and %(b)s shake hands and %(ending)s", {
                'a': a,
                'b': b,
                'ending': choice(self.happy_endings)
            })
        elif duel[winner][0] < 50.0:
            event.addresponse(u"DRAW: %(a)s and %(b)s bleed to death together", {'a': a, 'b': b})
        elif duel[loser][0] < 50.0:
            event.addresponse(u"VICTORY: %s bleeds to death", duel[loser][1])
        elif duel[winner][0] < 100.0:
            event.addresponse(u"DRAW: %(a)s and %(b)s hobble off together", {'a': a, 'b': b})
        else:
            event.addresponse(u"VICTORY: %(loser)s hobbles off while %(winner)s looks victorious", {
                'loser': duel[leser][1],
                'winner': duel[winner][1],
            })
    
    def setup(self):
        self.fire.im_func.pattern = re.compile(r'^(%s)$' % '|'.join(self.weapons.keys()), re.I | re.DOTALL)

    @handler
    def fire(self, event, weapon):
        log.debug('Duels: %s', self.duels)
        shooter = event.sender['nick']
        duel = [duel for duel in self.duels if shooter.lower() in duel]

        if len(duel) == 0:
            if event.addressed:
                event.addresponse(choice((u"You aren't in a war", u'You are a non-combatant', u'You are a spectator')))
            return
        duel = duel[0]
        
        enemy = [duel[name][1] for name in duel.keys() if name != shooter.lower()][0]
        enemyk = enemy.lower()
        chance, power = self.weapons[weapon]

        if random() < chance:
            damage = gauss(power, power/2.0)
            duel[enemyk][0] -= damage
            if duel[enemyk][0] <= 0.0:
                self.duels.remove(duel)

            if damage > 100.0:
                event.addresponse(u'VICTORY: ' +
                    choice((
                        u'%(winner)s blows %(loser)s away',
                        u'%(winner)s destroys %(loser)s',
                )), {
                    'winner': shooter,
                    'loser': enemy,
                })
            elif duel[enemyk][0] <= 0.0:
                event.addresponse(u'VICTORY: ' +
                    choice((
                        u'%(winner)s kills %(loser)s with a shot to the %(part)s',
                        u'%(winner)s shoots %(loser)s killing him with a fatal shot to the %(part)s',
                )), {
                    'winner': shooter,
                    'loser': enemy,
                    'part': choice(self.vitals),
                })
            else:
                event.addresponse(
                    choice((
                        u'%(winner)s hits %(loser)s in the %(part)s, wounding him',
                        u'%(winner)s shoots %(loser)s in the %(part)s, but %(loser)s can still fight',
                )), {
                    'winner': shooter,
                    'loser': enemy,
                    'part': choice(self.extremities),
                })
            
        else:
            event.addresponse(choice((u'%s misses', u'%s aims wide', u'%s is useless with a weapon')), shooter)

# vi: set et sta sw=4 ts=4:
