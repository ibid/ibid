from time import sleep
from random import choice, gauss, random
import re

from ibid.plugins import Processor, match, handler
from ibid.config import Option, IntOption, BoolOption
from ibid.utils import ibid_version

help = {}

help['shootout'] = u"Mexcan Shootout between channel members"
class Coffee(Processor):
    u"""[mexican] shootout [between] <user> [and] <user>"""
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
        u'bang': (0.75, 100),
        u'kapow': (0.75, 110),
        u'pewpew': (0.75, 150),
        u'holyhanggrenadeofantioch': (1.0, 200),
    })

    timeout = IntOption('timeout', 'How long is a duel on for', 60)
    duels = []
    
    @match(r'^(?:mexican\s+)?(?:shootout|standoff|du[ae]l)\s+(?:between\s+)?(\S+)\s+(?:and\s+)?(\S+)$')
    def initiate(self, event, a, b):
        if not event.addressed:
            return
        for combatent in (a, b):
            if [True for duel in self.duels if combatent in duel]:
                event.addresponse(u"%s is already at war", combatent)
                return
        
        duel = {a: 100.0, b:100.0}
        self.duels.append(duel)
        sleep(self.timeout)
        self.duels.remove(duel)

        if duel[a] >= 0.0 or duel[b] >= 0.0:
            return

        if duel[a] > duel[b]:
            a, b = b, a

        if duel[a] == 100.0 and duel[b] == 100.0:
            event.addresponse(u"%(a)s and %(b)s shake hands and %(ending)s", {
                'a': a,
                'b': b,
                'ending': choice(self.happy_endings)
            })
        elif duel[a] < 50 and duel[b] < 50:
            event.addresponse(u"%(a)s and %(b)s bleed to death together", {'a': a, 'b': b})
        elif duel[a] < 50:
            event.addresponse(u"%s bleeds to death", a)
        elif duel[a] < 100.0 and duel[b] < 100.0:
            event.addresponse(u"%(a)s and %(b)s hobble off together", {'a': a, 'b': b})
        else:
            event.addresponse(u"%(loser)s hobbles off while %(winner)s looks victorious", {'loser': a, 'winner': b})
    
    def setup(self):
        self.fire.im_func.pattern = re.compile(r'^(%s)$' % '|'.join(self.weapons.keys()), re.I | re.DOTALL)

    @handler
    def fire(self, event, weapon):
        shooter = event.sender['nick']
        duel = [duel for duel in self.duels if shooter in duel]

        if len(duel) == 0:
            event.addresponse(choice((u"You aren't in a war", u'You are a non-combatant', u'You are a spectator')))
            return
        duel = duel[0]
        
        enemy = [name for name in duel.keys() if name != shooter][0]
        chance, power = self.weapons[weapon]

        if random() < chance:
            damage = gauss(power, power/2.0)
            if damage > 100.0:
                event.addresponse(choice((u'%(winner)s blows %(loser)s away', u'%(winner)s destroys %(loser)s')), {
                    'winner': shooter,
                    'loser': enemy,
                })
            elif duel[enemy] - damage < 0.0:
                event.addresponse(
                    choice((
                        u'%(winner)s kills %(loser)s with a shot to the %(part)s',
                        u'%(winner)s shoots %(loser) killing him with a fatal shot to the %(part)s',
                )), {
                    'winner': shooter,
                    'loser': enemy,
                    'part': choice(damage > 50 and self.vitals or self.extremities),
                })
            else:
                event.addresponse(
                    choice((
                        u'%(winner)s hits %(loser)s in the %(part)s, wounding him',
                        u'%(winner)s shoots %(loser)s in the %(part)s, but %(loser)s can still fight',
                )), {
                    'winner': shooter,
                    'loser': enemy,
                    'part': choice(damage > 50 and self.vitals or self.extremities),
                })
        else:
            event.addresponse(choice((u'%s misses', u'%s aims wide', u'%s is useless with a weapon')), shooter)

# vi: set et sta sw=4 ts=4:
