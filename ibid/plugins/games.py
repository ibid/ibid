from datetime import datetime, timedelta
import logging
from random import choice, gauss, random
import re

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option, IntOption, BoolOption, FloatOption
from ibid.utils import format_date

help = {}
log = logging.getLogger('plugins.games')

duels = {}

help['duel'] = u"Duel at dawn, between channel members"
class DuelInitiate(Processor):
    u"""
    I challenge <user> to a duel [over <something>]
    I demand satisfaction from <user> [over <something>]
    I throw the gauntlet down at <user>'s feet [over <something>]
    """

    feature = 'duel'

    accept_timeout = FloatOption('accept_timeout', 'How long do we wait for acceptance?', 60.0)
    start_delay = IntOption('start_delay', 'Time between acceptance and start of duel (rounded down to the highest minute)', 30)
    timeout = FloatOption('timeout', 'How long is a duel on for', 15.0)

    happy_endings = Option('happy_endings', 'Both survive', (
        u'walk off into the sunset', u'go for a beer', u'call it quits',
    ))

    class Duel(object):
        def stop(self):
            for callback in ('cancel', 'start', 'timeout'):
                callback += '_callback'
                if hasattr(self, callback) and getattr(self, callback).active():
                    getattr(self, callback).cancel()

    @match(r'^(?:I\s+)throw\s+(?:down\s+(?:the|my)\s+gauntlet|(?:the|my)\s+gauntlet\s+down)\s+'
            r'at\s+(\S+?)(?:\'s\s+feet)?(?:\s+(?:over|because|for)\s+.+)?$')
    def initiate_gauntlet(self, event, recipient):
        self.initiate(event, recipient)

    @match(r'^(?:I\s+)?demand\s+satisfaction\s+from\s+(\S+)(?:\s+(?:over|because|for)\s+.+)?$')
    def initiate_satisfaction(self, event, recipient):
        self.initiate(event, recipient)
    
    @match(r'^(?:I\s+)?challenge\s+(\S+)(?:\s+to\s+a\s+duel)?(?:\s+(?:over|because|for)\s+.+)?$')
    def initiate(self, event, recipient):
        if not event.public:
            event.addresponse(choice((
                u"All duels must take place in public places, by decree of the bot",
                u"How do you expect to fight %(recipient)s, when he is not present?",
                u"Your challenge must be made in public, Sir Knight",
            )), {
                'recipient': recipient
            })
            return

        if (event.source, event.channel) in duels:
            event.addresponse(choice((
                u"We already have a war in here. Take your fight outside",
                u"Isn't one fight enough? You may wait your turn",
            )))
            return

        aggressor = event.sender['nick']

        if recipient.lower() == aggressor.lower():
            # Yes I know schizophrenia isn't the same as DID, but this sounds better :P
            event.addresponse(choice((
                u"Are you schizophrenic?",
                u"Um, How exactly do you plan on fighting yourself?",
            )))
            return

        if recipient.lower() in [name.lower() for name in ibid.config.plugins['core']['names']]:
            event.addresponse(choice((
                u"I'm a peaceful bot",
                u"The ref can't take part in the battle",
                u"You just want me to die. No way",
            )))
            return

        duel = self.Duel()
        duels[(event.source, event.channel)] = duel

        duel.hp = {
                aggressor.lower(): 100.0,
                recipient.lower(): 100.0,
        }
        duel.names = {
                aggressor.lower(): aggressor,
                recipient.lower(): recipient,
        }
        duel.drawn = {
                aggressor.lower(): False,
                recipient.lower(): False,
        }

        duel.started = False
        duel.confirmed = False
        duel.aggressor = event.sender['nick'].lower()
        duel.recipient = recipient.lower()

        duel.cancel_callback = ibid.dispatcher.call_later(self.accept_timeout, self.cancel, event)

        event.addresponse({'reply': (u'%(recipient)s: ' + choice((
            u"The gauntlet has been thrown at your feet. Do you accept?",
            u"You have been challenged. Do you accept?",
            u"%(aggressor)s wishes to meet you at dawn on the field of honour. Do you accept?",
        ))) % {
            'recipient': recipient,
            'aggressor': event.sender['nick'],
        }})

    def cancel(self, event):
        duel = duels[(event.source, event.channel)]
        del duels[(event.source, event.channel)]

        event.addresponse(choice((
            u"%(recipient)s appears to have fled the country during the night",
            u"%(recipient)s refuses to meet your challenge and accepts dishonour",
            u"Your challenge was not met. I suggest anger management counselling",
        )), {
            'recipient': duel.names[duel.recipient],
        })

    @match(r'^.*\b(?:ok|yes|I\s+do|sure|accept|hit\s+me|bite\s+me|i\'m\s+game|bring\s+it|yebo)\b.*$')
    def confirm(self, event):
        if (event.source, event.channel) not in duels:
            return

        duel = duels[(event.source, event.channel)]

        confirmer = event.sender['nick'].lower()
        if confirmer not in duel.names or duel.confirmed or confirmer != duel.recipient:
            return

        # Correct capitalisation
        duel.names[confirmer] = event.sender['nick']

        duel.confirmed = True
        duel.cancel_callback.cancel()
        
        now = datetime.utcnow()
        starttime = now + timedelta(seconds=self.start_delay + ((30 - now.second) % 30))
        starttime = starttime.replace(microsecond=0)
        delay = starttime - now
        delay = delay.seconds + (delay.microseconds / 10.**6)

        duel.start_callback = ibid.dispatcher.call_later(delay, self.start, event)

        event.addresponse({'reply': (
            u"%(aggressor)s, %(recipient)s: "
            u"The duel shall begin on the stroke of %(starttime)s (in %(delay)s seconds). "
            + choice((
                u"You may clean your pistols.",
                u"Prepare yourselves.",
                u"Get ready",
            ))
        ) % {
            'aggressor': duel.names[duel.aggressor],
            'recipient': duel.names[duel.recipient],
            'starttime': format_date(starttime, 'time'),
            'delay': (starttime - now).seconds,
        }})

    def start(self, event):
        duel = duels[(event.source, event.channel)]

        duel.started = True
        duel.timeout_callback = ibid.dispatcher.call_later(self.timeout, self.end, event)

        event.addresponse({'reply':
            u"%s, %s: %s" % tuple(duel.names.values() + [choice((
            u'aaaand ... go!',
            u'5 ... 4 ... 3 ... 2 ... 1 ... fire!',
            u'match on!',
            u'ready ... aim ... fire!'
        ))])})

    def end(self, event):
        duel = duels[(event.source, event.channel)]
        del duels[(event.source, event.channel)]

        winner, loser = duel.names.keys()
        if duel.hp[winner] < duel.hp[loser]:
            winner, loser = loser, winner

        if duel.hp[loser] == 100.0:
            message = u"DRAW: %(winner)s and %(loser)s shake hands and %(ending)s"
        elif duel.hp[winner] < 50.0:
            message = u"DRAW: %(winner)s and %(loser)s bleed to death together"
        elif duel.hp[loser] < 50.0:
            message = u"VICTORY: %(loser)s bleeds to death"
        elif duel.hp[winner] < 100.0:
            message = u"DRAW: %(winner)s and %(loser)s hobble off together. Satisfaction is obtained"
        else:
            message = u"VICTORY: %(loser)s hobbles off while %(winner)s looks victorious"

        event.addresponse({'reply': message % { 
                'loser': duel.names[loser],
                'winner': duel.names[winner],
                'ending': choice(self.happy_endings),
        }})
    
class DuelDraw(Processor):
    u"""
    draw [my <weapon>]
    bam|pew|bang|kapow|pewpew|holyhandgrenadeofantioch
    """

    feature = 'duel'

    # Parameters for Processor:
    event_types = ('message', 'action')

    addressed = BoolOption('addressed', 'Must the bot be addressed?', True)

    # Game configurables:
    weapons = Option('weapons', 'Weapons that can be used: name: (chance, damage)', {
        u'bam': (0.75, 50),
        u'pew': (0.75, 50),
        u'fire': (0.75, 70),
        u'fires': (0.75, 70),
        u'bang': (0.75, 70),
        u'kapow': (0.75, 90),
        u'pewpew': (0.75, 110),
        u'holyhandgrenadeofantioch': (1.0, 200),
    })
    extremities = Option('extremities', u'Extremities that can be hit', (
        u'toe', u'foot', u'leg', u'thigh', u'finger', u'hand', u'arm',
        u'elbow', u'shoulder', u'ear', u'nose', u'stomach',
    ))
    vitals = Option('vitals', 'Vital parts of the body that can be hit', (
        u'head', u'groin', u'chest', u'heart', u'neck',
    ))

    draw_required = BoolOption('draw_required', 'Must you draw your weapon before firing?', True)
    extratime = FloatOption('extratime', 'How much more time to grant after every shot fired?', 1.0)

    @match(r'^draws?(?:\s+h(?:is|er)\s+.*|\s+my\s+.*)?$')
    def draw(self, event):
        if (event.source, event.channel) not in duels:
            if event.get('addressed', False):
                event.addresponse(choice((
                    u"We do not permit drawn weapons here",
                    u"You may only draw a weapon on the field of honour",
                )))
            return

        duel = duels[(event.source, event.channel)]

        shooter = event.sender['nick']
        if shooter.lower() not in duel.names:
            event.addresponse(choice((
                u"Spectators are not permitted to draw weapons",
                u"Do you think you are %(fighter)s?",
            )), {'fighter': choice(duel.names.values())})
            return

        if not duel.started:
            event.addresponse(choice((
                u"Now now, not so fast!",
                u"Did I say go yet?",
                u"Put that AWAY!",
            )))
            return

        duel.drawn[shooter.lower()] = True
        event.addresponse(True)
        
    def setup(self):
        self.fire.im_func.pattern = re.compile(
                r'^(%s)(?:[\s,.!:;].*)?$' % '|'.join(self.weapons.keys()),
                re.I | re.DOTALL)

    @handler
    def fire(self, event, weapon):
        shooter = event.sender['nick'].lower()
        if (event.source, event.channel) not in duels:
            return

        duel = duels[(event.source, event.channel)]

        if shooter not in duel.names:
            event.addresponse(choice((
                u"You aren't in a war",
                u'You are a non-combatant',
                u'You are a spectator',
            )))
            return

        enemy = set(duel.names.keys())
        enemy.remove(shooter)
        enemy = enemy.pop()

        if self.draw_required and not duel.drawn[shooter]:
            recipient = shooter
        else:
            recipient = enemy

        if not duel.started or not duel.confirmed:
            if self.draw_required:
                message = choice((
                    u"%(shooter)s tried to escape his duel by shooting himself in the foot. The duel has been cancelled, but his honour is forfeit",
                    u"%(shooter)s shot himself while preparing for his duel. The funeral will be held on the weekend",
                ))
            elif not duel.started:
                message = choice((
                    u"FOUL! %(shooter)s fired before my mark. Just as well you didn't hit anything. I refuse to referee under these conditions",
                    u"FOUL! %(shooter)s injures %(enemy)s before the match started and is marched away in handcuffs",
                    u"FOUL! %(shooter)s killed %(enemy)s before the match started and was shot by the referee before he could hurt anyone else",
                ))
            else:
                message = choice((
                    u"FOUL! The duel is not yet confirmed. %(shooter)s is marched away in handcuffs",
                    u"FOUL! Arrest %(shooter)s! Firing a weapon within city limits is not permitted",
                ))
            event.addresponse({'reply': message % {
                'shooter': duel.names[shooter],
                'enemy': duel.names[enemy],
            }})
            del duels[(event.source, event.channel)]
            duel.stop()
            return

        chance, power = self.weapons[weapon.lower()]

        if random() < chance:
            damage = max(gauss(power, power/2.0), 0)
            duel.hp[recipient] -= damage
            if duel.hp[recipient] <= 0.0:
                del duels[(event.source, event.channel)]
                duel.stop()
            else:
                duel.timeout_callback.delay(self.extratime)
            
            params = {
                    'shooter': duel.names[shooter],
                    'enemy': duel.names[enemy],
                    'part': u'foot',
            }
            if shooter == recipient:
                message = u"TRAGEDY: %(shooter)s shoots before drawing his weapon. "
                if damage > 100.0:
                    message += choice((
                        u"The explosion killed him",
                        u"There was little left of him",
                    ))
                elif duel.hp[recipient] <= 0.0:
                    message += choice((
                        u"Combined with his other injuries, he didn't stand a chance",
                        u"He died during field surgery",
                    ))
                else:
                    message += choice((
                        u"Luckily, it was only a flesh wound",
                        u"He narrowly missed his femoral artery",
                    ))

            elif damage > 100.0:
                message = u'VICTORY: ' + choice((
                        u'%(shooter)s blows %(enemy)s away',
                        u'%(shooter)s destroys %(enemy)s',
                ))
            elif duel.hp[enemy] <= 0.0:
                message = u'VICTORY: ' + choice((
                        u'%(shooter)s kills %(enemy)s with a shot to the %(part)s',
                        u'%(shooter)s shoots %(enemy)s killing him with a fatal shot to the %(part)s',
                ))
                params['part'] = choice(self.vitals)
            else:
                message = choice((
                        u'%(shooter)s hits %(enemy)s in the %(part)s, wounding him',
                        u'%(shooter)s shoots %(enemy)s in the %(part)s, but %(enemy)s can still fight',
                ))
                params['part'] = choice(self.extremities)

            event.addresponse({'reply': message % params})
            
        elif shooter == recipient:
            event.addresponse({'reply': choice((
                u"%s forget to draw his weapon. Luckily he missed his foot",
                u"%s fires a holstered weapon. Luckily it only put a hole in his jacket",
                u"%s won't win at this rate. He forgot to draw before firing. He missed himself too",
            )) % duel.names[shooter]})
        else:
            event.addresponse({'reply': choice((
                u'%s misses',
                u'%s aims wide',
                u'%s is useless with a weapon'
            )) % duel.names[shooter]})

class DuelFlee(Processor):
    feature = 'duel'
    addressed = False
    event_types = ('state',)

    @handler
    def dueller_fled(self, event):
        if event.state != 'offline':
            return

        fleer = event.sender['nick'].lower()
        for (source, channel), duel in duels.items():
            if source != event.source or fleer not in duel.names:
                continue

            if hasattr(event, 'othername'):
                newnamekey = event.othername.lower()
                for key in ('hp', 'names', 'drawn'):
                    getattr(duel, key)[newnamekey] = getattr(duel, key)[fleer]
                    del getattr(duel, key)[fleer]
                duel.names[newnamekey] = event.othername
                if duel.aggressor == fleer:
                    duel.aggressor = newnamekey
                else:
                    duel.recipient = newnamekey

                event.addresponse({
                    'target': channel,
                    'reply': choice((
                        "%s: Changing your identity won't help",
                        "%s: You think I didn't see that?",
                        "%s: There's no escape, you know",
                    )) % event.othername,
                })

            else:
                del duels[(source, channel)]
                duel.stop()
                event.addresponse({
                    'target': channel,
                    'reply': choice((
                            "VICTORY: %(winner)s: %(fleer)s has fled the country during the night",
                            "VICTORY: %(winner)s: The cowardly %(fleer)s has run for his life",
                        )) % {
                            'winner': duel.names[[name for name in duel.names if name != fleer][0]],
                            'fleer': duel.names[fleer],
                    },
                })

# vi: set et sta sw=4 ts=4:
