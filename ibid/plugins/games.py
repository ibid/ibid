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

    timeout = FloatOption('timeout', 'How long is a duel on for', 10.0)
    extratime = FloatOption('extratime', 'How much more time to grant after every shot fire', 1.0)
    delay = FloatOption('delay', 'Countdown time', 3.0)

    duels = {}
    
    class Duel(object):
        pass

    @match(r'^(?:mexican\s+)?(?:shootout|standoff|du[ae]l)\s+(?:between\s+)?(\S+)\s+(?:and\s+)?(\S+)$')
    def initiate(self, event, a, b):
        if not event.addressed:
            return

        if (event.source, event.channel) in self.duels:
            event.addresponse(u"We already have a war in here. Take your fight outside")
            return

        if a.lower() == b.lower():
            # Yes I know schizophrenia isn't the same as DID, but this sounds better :P
            event.addresponse(u"Is %s schizophrenic?", a)
            return

        if [True for name in ibid.config.plugins['core']['names'] if name.lower() in (a.lower(), b.lower())]:
            event.addresponse(choice((
                u"I'm a peaceful bot",
                u"The ref can't take part in the battle",
                u"You just want me to die. No way",
            )))
            return

        duel = self.Duel()
        self.duels[(event.source, event.channel)] = duel

        duel.hp = {a.lower(): 100.0, b.lower(): 100.0}
        duel.names = {a.lower(): a, b.lower(): b}

        duel.started = False
        delay = self.delay and max(gauss(self.delay, self.delay / 2), 0) or 0.0

        if self.delay:
            ibid.dispatcher.call_later(delay, self.start_duel, event)
            event.addresponse(True)
        else:
            self.start_duel(event)

        duel.timeout = ibid.dispatcher.call_later(self.timeout + delay, self.end_duel, event)

    def start_duel(self, event):
        self.duels[(event.source, event.channel)].started = True

        event.addresponse(choice((
            u'aaaand ... go!',
            u'5 ... 4 ... 3 ... 2 ... 1 ... fire!',
            u'match on!',
            u'read ... aim ... fire!'
        )))

    def setup(self):
        self.fire.im_func.pattern = re.compile(r'^(%s)$' % '|'.join(self.weapons.keys()), re.I | re.DOTALL)

    @handler
    def fire(self, event, weapon):
        shooter = event.sender['nick']
        if (event.source, event.channel) not in self.duels:
            return

        duel = self.duels[(event.source, event.channel)]

        if shooter.lower() not in duel.names:
            event.addresponse(choice((
                u"You aren't in a war",
                u'You are a non-combatant',
                u'You are a spectator',
            )))
            return

        # Correct capitalisation from shooter's nick
        duel.names[shooter.lower()] = shooter
        shooter = shooter.lower()

        enemy = set(duel.names.keys())
        enemy.remove(shooter)
        enemy = enemy.pop()

        if not duel.started:
            event.addresponse(choice((
                u"FOUL! %(shooter)s fired before my mark. Just as well you didn't hit anything. I refuse to referee under these conditions",
                u"FOUL! %(shooter)s injures %(enemy)s before the match started and is marched away in handcuffs",
                u"FOUL! %(shooter)s killed %(enemy)s before the match started and was shot by the referee before he could hurt anyone else",
            )), {
                'shooter': duel.names[shooter],
                'enemy': duel.names[enemy],
            })
            del self.duels[(event.source, event.channel)]
            duel.timeout.cancel()
            return

        chance, power = self.weapons[weapon.lower()]

        if random() < chance:
            damage = max(gauss(power, power/2.0), 0)
            duel.hp[enemy] -= damage
            if duel.hp[enemy] <= 0.0:
                del self.duels[(event.source, event.channel)]
                duel.timeout.cancel()
            else:
                duel.timeout.delay(self.extratime)

            if damage > 100.0:
                event.addresponse(u'VICTORY: ' +
                    choice((
                        u'%(winner)s blows %(loser)s away',
                        u'%(winner)s destroys %(loser)s',
                )), {
                    'winner': duel.names[shooter],
                    'loser': duel.names[enemy],
                })
            elif duel.hp[enemy] <= 0.0:
                event.addresponse(u'VICTORY: ' +
                    choice((
                        u'%(winner)s kills %(loser)s with a shot to the %(part)s',
                        u'%(winner)s shoots %(loser)s killing him with a fatal shot to the %(part)s',
                )), {
                    'winner': duel.names[shooter],
                    'loser': duel.names[enemy],
                    'part': choice(self.vitals),
                })
            else:
                event.addresponse(
                    choice((
                        u'%(winner)s hits %(loser)s in the %(part)s, wounding him',
                        u'%(winner)s shoots %(loser)s in the %(part)s, but %(loser)s can still fight',
                )), {
                    'winner': duel.names[shooter],
                    'loser': duel.names[enemy],
                    'part': choice(self.extremities),
                })
            
        else:
            event.addresponse(choice((
                u'%s misses',
                u'%s aims wide',
                u'%s is useless with a weapon'
            )), duel.names[shooter])

    def end_duel(self, event):
        duel = self.duels[(event.source, event.channel)]
        del self.duels[(event.source, event.channel)]

        winner, loser = duel.names.keys()
        if duel.hp[winner] < duel.hp[loser]:
            winner, loser = loser, winner

        if duel.hp[loser] == 100.0:
            event.addresponse(u"DRAW: %(a)s and %(b)s shake hands and %(ending)s", {
                'a': duel.names[winner],
                'b': duel.names[loser],
                'ending': choice(self.happy_endings)
            })
        elif duel.hp[winner] < 50.0:
            event.addresponse(u"DRAW: %(a)s and %(b)s bleed to death together", {
                'a': duel.names[winner],
                'b': duel.names[loser],
            })
        elif duel.hp[loser] < 50.0:
            event.addresponse(u"VICTORY: %s bleeds to death", duel.names[loser])
        elif duel.hp[winner] < 100.0:
            event.addresponse(u"DRAW: %(a)s and %(b)s hobble off together", {
                'a': duel.names[winner],
                'b': duel.names[loser],
            })
        else:
            event.addresponse(u"VICTORY: %(loser)s hobbles off while %(winner)s looks victorious", {
                'loser': duel.names[loser],
                'winner': duel.names[winner],
            })
    
# vi: set et sta sw=4 ts=4:
