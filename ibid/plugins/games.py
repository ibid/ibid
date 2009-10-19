from collections import defaultdict
from datetime import timedelta
import logging
from random import choice, gauss, random, shuffle
import re

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import IntOption, BoolOption, FloatOption, ListOption, DictOption
from ibid.utils import format_date, human_join, plural

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

    happy_endings = ListOption('happy_endings', 'Both survive', (
        u'walk off into the sunset', u'go for a beer', u'call it quits',
    ))

    class Duel(object):
        def stop(self):
            for callback in ('cancel', 'start', 'timeout'):
                callback += '_callback'
                if hasattr(self, callback) and getattr(self, callback).active():
                    getattr(self, callback).cancel()

    def shutdown(self):
        for duel in duels:
            duel.stop()

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

        starttime = event.time + timedelta(
                seconds=self.start_delay + ((30 - event.time.second) % 30))
        starttime = starttime.replace(microsecond=0)
        delay = starttime - event.time
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
            'delay': (starttime - event.time).seconds,
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
    weapons = DictOption('weapons', 'Weapons that can be used: name: (chance, damage)', {
        u'bam': (0.75, 50),
        u'pew': (0.75, 50),
        u'fire': (0.75, 70),
        u'fires': (0.75, 70),
        u'bang': (0.75, 70),
        u'kapow': (0.75, 90),
        u'pewpew': (0.75, 110),
        u'holyhandgrenadeofantioch': (1.0, 200),
    })
    extremities = ListOption('extremities', u'Extremities that can be hit', (
        u'toe', u'foot', u'leg', u'thigh', u'finger', u'hand', u'arm',
        u'elbow', u'shoulder', u'ear', u'nose', u'stomach',
    ))
    vitals = ListOption('vitals', 'Vital parts of the body that can be hit', (
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

werewolf_games = []

help['werewolf'] = (u'Play the werewolf game. '
    u'Channel becomes a village containing a werewolf, seer and villagers. '
    u'Every night, the werewolf can kill a villager, and the seer can test '
    u'a villager for werewolf symptoms. '
    u'Villagers then vote to lynch a wolf during the day.')
class WerewolfGame(Processor):
    u"""
    start a game of werewolf
    join
    ( kill | see | eat ) <villager>
    vote for <villager>
    """

    feature = 'werewolf'
    state = None

    player_limit = IntOption('min_players', 'The minimum number of players', 5)
    start_delay = IntOption('start_delay',
            'How long to wait before starting, in seconds', 60)
    day_length = IntOption('day_length', 'Length of day / night, in seconds',
            60)
    addressed = BoolOption('addressed', 'Messages must be addressed to bot',
            True)
    players_per_wolf = IntOption('players_per_wolf',
            'Number of players to each wolf/seer', 4)
    seer_delay = IntOption('seer_delay',
            'Number of players between extra wolf and extra seer', 4)

    event_types = ('message', 'action')

    @match(r'^(?:start|play|begin)s?\b.*werewolf$')
    def prestart(self, event):
        """Initiate a game.

        This is the state from initiation to start of game.
        Next state is start.
        """
        if self.state:
            log.debug(u'Not starting game: already in state %s.',
                    self.state_name())
            return

        if not event.public:
            log.debug(u'Event is not public.')
            event.addresponse(u'You must start the game in public.')
            return

        self.state = self.prestart
        self.channel = event.channel

        log.debug(u'Starting game.')

        werewolf_games.append(self)

        starter = event.sender['nick']
        self.players = set((starter,))
        event.addresponse(u'You have started a game of Werewolf. '
            u'Everybody has %i seconds to join the game.'
            % self.start_delay)

        self.timed_goto(event, self.start_delay, self.start)

    @match(r'^joins?\b')
    def join(self, event):
        if self.state != self.prestart:
            log.debug(u'Not joining: already in state %s.',
                    self.state_name())
            return

        if event.sender['nick'] not in self.players:
            self.players.add(event.sender['nick'])
            event.addresponse({
                'reply': u'%(player)s has joined (%(num)i players).' % {
                        'num': len(self.players),
                        'player': event.sender['nick']
                    },
                'target': self.channel,
            })
        else:
            event.addresponse(u'You have already joined the game.')

    def start(self, event):
        """Start game.

        Players are assigned their roles. The next state is night.
        """
        self.state = self.start

        if len(self.players) < self.player_limit:
            event.addresponse(u'Not enough players. Try again later.')
            self.state = None
            return

        event.addresponse(
            u'%i players joined. Please wait while I assign roles.',
            len(self.players))

        self.players = list(self.players)
        shuffle(self.players)

        nwolves = max(1, len(self.players) // self.players_per_wolf)
        nseers = max(1, (len(self.players) - self.seer_delay) //
                        self.players_per_wolf)
        self.wolves = set(self.players[:nwolves])
        self.seers = set(self.players[nwolves:nwolves + nseers])

        self.roles = dict((player, 'villager') for player in self.players)
        del self.players

        for player in self.wolves:
            self.roles[player] = 'wolf'

        for player in self.seers:
            self.roles[player] = 'seer'

        for player, role in self.roles.iteritems():
            event.addresponse({
                'reply': u'%(name)s, you are a %(role)s.' % {
                    'name': player,
                    'role': role,
                },
                'target': player,
            })

        if nwolves > 1 and nseers > 1:
            event.addresponse(
                u'This game has %(seers)i seers and %(wolves)i wolves.', {
                    'seers': nseers,
                    'wolves': nwolves,
            })
        elif nwolves > 1:
            event.addresponse(u'This game has %i wolves.', nwolves)
        elif nseers > 1:
            event.addresponse(u'This game has %i seers.', nseers)

        self.timed_goto(event, 10, self.night)

    def night(self, event):
        """Start of night.

        Tell seer and werewolf to act.

        This state lasts for the whole night. The next state is dawn.
        """
        self.state = self.night
        event.addresponse(u'Night falls... most villagers are sleeping, '
                            'but outside, something stirs.')
        event.addresponse(plural(len(self.wolves),
                u'Werewolf, you may kill somebody.',
                u'Werewolves, you may kill somebody.'))
        event.addresponse(plural(len(self.seers),
                u"Seer, you may discover somebody's true form.",
                u"Seers, you may discover somebody's true form."))
        self.say_survivors(event)

        self.wolf_targets = {}
        self.seer_targets = {}

        self.timed_goto(event, self.day_length, self.dawn)

    @match(r'^(?:kill|see|eat)s?\s+(\S+)$')
    def kill_see(self, event, target_nick):
        """Kill or see a player.

        Only works for seers and wolves.
        """
        if (self.state != self.night or event.public
                or event.sender['nick'] not in self.roles):
            return

        sender = event.sender['nick']
        target = self.identify(target_nick)
        if target is None:
            event.addresponse(u'%s is not playing.', target_nick)
        elif self.roles[sender] == 'wolf':
            event.addresponse(u'You have chosen %s for your feast tonight.',
                    target_nick)
            self.wolf_targets[sender] = target
        elif self.roles[sender] == 'seer':
            event.addresponse(u"You will discover %s's role at dawn tomorrow.",
                    target_nick)
            self.seer_targets[sender] = target

    def dawn(self, event):
        """Start of day.

        During this state, villagers discover what happened overnight and
        discuss who to lynch. The next state is noon.
        """
        self.state = self.dawn

        eaten = frozenset(self.wolf_targets.itervalues())
        if eaten:
            victim = choice(list(eaten))
            event.addresponse(
                u'The village awakes to find that werewolves have '
                u'devoured %(nick)s the %(role)s in the night.', {
                    'nick': victim,
                    'role': self.roles[victim],
            })
            self.death(victim)
        else:
            event.addresponse(u'The werewolves were abroad last night.')
        self.wolf_targets = {}

        for seer in self.seers:
            target = self.seer_targets.get(seer)
            if target is not None:
                # seer saw somebody
                if target in self.roles:
                    # that somebody is alive
                    msg = u'%(nick)s is a %(role)s' % {
                        'nick': target,
                        'role': self.roles[target],
                    }
                else:
                    msg = u'The wolves also had %s in mind last night.' \
                        % target

                event.addresponse({
                    'reply': msg,
                    'target': seer,
                })
        self.seer_targets = {}

        if not self.endgame(event):
            event.addresponse(u'Villagers, you have %i seconds '
                    u'to discuss suspicions and cast accusations.'
                    % self.day_length)
            self.say_survivors(event)

            self.timed_goto(event, self.day_length, self.noon)

    def noon(self, event):
        """Start of voting.

        Next state is dusk.
        """
        self.state = self.noon
        event.addresponse(u'Villagers, you have %i seconds to cast '
                u'your vote to lynch somebody.'
                % self.day_length)

        self.votes = {}

        self.timed_goto(event, self.day_length, self.dusk)

    @match(r'^(?:lynch(?:es)?|votes?)\s+(?:for|against)\s+(\S+)$')
    def vote(self, event, target_nick):
        """Vote to lynch a player."""

        if (self.state != self.noon or event.sender['nick'] not in self.roles):
            return

        target = self.identify(target_nick)
        if target is None:
            event.addresponse(u'%s is not playing.', target_nick)
        else:
            self.votes[event.sender['nick']] = target
            event.addresponse({
                'reply': u'%(voter)s voted for %(target)s.' % {
                    'target': target,
                    'voter': event.sender['nick'],
                },
                'target': self.channel,
            })

    def dusk(self, event):
        """Counting of votes and lynching.

        Next state is night.
        """
        self.state = self.dusk
        vote_counts = defaultdict(int)
        for vote in self.votes.values():
            vote_counts[vote] += 1
        self.votes = {}

        victims = []
        victim_votes = 0
        for player, votes in vote_counts.iteritems():
            if votes > victim_votes:
                victims = [player]
                victim_votes = votes
            elif votes == victim_votes:
                victims.append(player)

        if victims:
            if len(victims) > 1:
                event.addresponse(u'The votes are tied. Picking randomly...')
            victim = choice(victims)
            event.addresponse(u'The ballots are in, '
                u'and %(nick)s the %(role)s has been lynched.', {
                    'nick': victim,
                    'role': self.roles[victim],
            })
            self.death(victim)
        else:
            event.addresponse(u'Nobody voted.')

        if not self.endgame(event):
            self.timed_goto(event, 10, self.night)

    def say_survivors(self, event):
        """Name surviving players."""

        event.addresponse(u'The surviving villagers are: %s.',
                human_join(self.roles))

    def identify(self, nick):
        """Find the identity (correctly-capitalised nick) of a player.

        Returns None if nick is not playing.
        """
        for player in self.roles.iterkeys():
            if player.lower() == nick.lower():
                return player
        return None

    def death(self, player):
        """Remove player from game."""

        if self.state == self.prestart:
            self.players.remove(player)
        elif self.state is not None:
            del self.roles[player]

            for role in (self.wolves, self.seers):
                try:
                    role.remove(player)
                except KeyError:
                    pass

    def endgame(self, event):
        """Check if the game is over.

        If the game is over, announce the winners and return True. Otherwise
        return False.
        """

        if 2 * len(self.wolves) >= len(self.roles):
            # werewolves win
            event.addresponse(u'The werewolves devour the remaining '
                    u'villagers and win. OM NOM NOM.')
            event.addresponse(u'The winning werewolves were: %s',
                    human_join(self.wolves))
        elif not self.wolves:
            # villagers win
            event.addresponse(u'The villagers have defeated the werewolves. '
                    'Vigilantism FTW.')
            event.addresponse(u'The surviving villagers were: %s',
                    human_join(self.roles))
        else:
            return False

        self.state = None
        werewolf_games.remove(self)
        return True

    def timed_goto(self, event, delay, target):
        """Like call_later, but does nothing if state has changed."""

        from_state = self.state
        log.debug(u'Going from state %s to %s in %i seconds.',
                self.state_name(), target.__name__, delay)
        def goto (evt):
            """Change state if it hasn't already changed."""
            if self.state == from_state:
                target(evt)

        ibid.dispatcher.call_later(delay, goto, event)

    def rename(self, oldnick, newnick):
        """Rename a player."""

        for playerset in ('players', 'wolves', 'seers'):
            if hasattr(self, playerset):
                playerset = getattr(self, playerset)
                if oldnick in playerset:
                    playerset.remove(oldnick)
                    playerset.add(newnick)

        if hasattr(self, 'roles') and oldnick in self.roles:
            self.roles[newnick] = self.roles[oldnick]
            del self.roles[oldnick]

    def state_change(self, event):
        if self.state is None:
            return

        if not hasattr(event, 'state'):
            return

        if event.state != 'online':
            nick = event.sender['nick']
            if hasattr(event, 'othername'):
                self.rename(event.othername, nick)
            elif ((self.state == self.prestart and nick in self.players) or
                nick in self.roles):
                event.addresponse({
                    'reply': u'%s has fled the game in terror.' % nick,
                    'target': self.channel,
                })
                self.death(nick)

    def state_name(self):
        "Return a printable version of the current state"
        if self.state is None:
            return 'stopped'
        return self.__name__

class WerewolfState(Processor):
    feature = 'werewolf'
    event_types = ('state',)

    @handler
    def state_change(self, event):
        for game in werewolf_games:
            game.state_change(event)
