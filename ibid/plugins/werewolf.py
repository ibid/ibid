from collections import defaultdict
import logging
from random import shuffle, choice

import ibid
from ibid.config import IntOption, BoolOption
from ibid.plugins import Processor, match, handler

log = logging.getLogger('plugins.werewolf')

def _ (arg):
    return unicode(arg)

games = []

class WerewolfGame (Processor):
    feature = 'werewolf'
    state = None

    player_limit = IntOption('min_players',
                            'the minimum number of players',
                            5)
    addressed = BoolOption('addressed',
                            'messages must be addressed to bot',
                            False)
    players_per_wolf = IntOption('players_per_wolf',
                                'number of players to each wolf/seer',
                                4)
    seer_delay = IntOption('seer_delay',
                          'number of players between extra wolf and extra seer',
                          4)

    event_types = ('message', 'action')

    @match(r"^(?:start|play|begin)s?\b.*werewolf$")
    def prestart (self, event):
        """Initiate a game.

        This is the state from initiation to start of game. Next state is start.
        """

        if self.state:
            log.debug("Not starting game: already in state %s." % self.state)
            return

        if not event.public:
            log.debug("Event is not public.")
            event.addresponse(_("you must start the game in public."))
            return

        self.state = self.prestart
        self.channel = event.channel
        
        log.debug("Starting game.")

        games.append(self)

        starter = event.sender['nick']
        self.players = set((starter,))
        event.addresponse(_("you have started a game of Werewolf. "
            "Everybody has 60 seconds to join the game."))

        self.timed_goto(event, 60, self.start)

    @match(r"^joins?\b")
    def join (self, event):
        if self.state != self.prestart:
            log.debug("Not joining: already in state %s." % self.state)
            return
        
        if event.sender['nick'] not in self.players:
            self.players.add(event.sender['nick'])
            event.addresponse({'reply': _("%(player)s has joined "
                                        "(%(num)i players).") %
                                        {'num': len(self.players),
                                        'player': event.sender['nick']},
                                'target': self.channel})
        else:
            event.addresponse(_("you have already joined the game."))

    def start (self, event):
        """Start game.

        Players are assigned their roles. The next state is night."""
        
        self.state = self.start

        if len(self.players) < self.player_limit:
            event.addresponse(_("Not enough players. Try again later."))
            self.state = None
            return

        event.addresponse(_("%(num)i players joined. "
            "Please wait while I assign roles.") %
            {'num': len(self.players)})

        self.players = list(self.players)
        shuffle(self.players)

        nwolves = max(1, len(self.players)//self.players_per_wolf)
        nseers = max(1,
                    (len(self.players)-self.seer_delay)//self.players_per_wolf)
        self.wolves = set(self.players[:nwolves])
        self.seers = set(self.players[nwolves:nwolves+nseers])

        self.roles = dict((player, 'villager') for player in self.players)
        del self.players

        for player in self.wolves:
            self.roles[player] = 'wolf'

        for player in self.seers:
            self.roles[player] = 'seer'
        
        for player, role in self.roles.iteritems():
            event.addresponse({'reply': _("%(name)s, you are a %(role)s.") %
                                    {'name': player, 'role': _(role)},
                                'target': player,
                                'notice': True})

        if nwolves > 1:
            event.addresponse(_("This game has %(wolves)i wolves.") %
                                {'wolves': nwolves})
        if nseers > 1:
            event.addresponse(_("This game has %(seers)i seers.") %
                                {'wolves': nseers})

        self.timed_goto(event, 10, self.night)

    def night (self, event):
        """Start of night.

        Tell seer and werewolf to act.

        This state lasts for the whole night. The next state is dawn."""

        self.state = self.night
        event.addresponse(_("Night falls... most villagers are sleeping, "
                            "but outside, something stirs."))
        event.addresponse(_("Werewolf, to kill somebody, "
                             "use the KILL command."))
        event.addresponse(_("Seer, to discover somebody's true form, "
                             "use the SEE command."))
        self.say_survivors(event)

        self.wolf_targets = {}
        self.seer_targets = {}

        self.timed_goto(event, 60, self.dawn)

    @match(r"^(?:kill|see|eat)s?\s+(\S+)$")
    def kill_see (self, event, target_nick):
        """Kill or see a player.

        Only works for seers and wolves."""

        if (self.state != self.night or
            event.public
            or event.sender['nick'] not in self.roles):
            return

        sender = event.sender['nick']
        target = self.identify(target_nick)
        if target is None:
            event.addresponse({'reply': _("%(nick)s is not playing.") %
                                    {'nick': target_nick},
                                'target': event.sender['id'],
                                'notice': True})
        elif self.roles[sender] == 'wolf':
            event.addresponse({'reply': _("You have chosen %(nick)s "
                                        "for your feast tonight.") %
                                        {'nick': target_nick},
                                'target': event.sender['id'],
                                'notice': True})
            self.wolf_targets[sender] = target
        elif self.roles[sender] == 'seer':
            event.addresponse({'reply': _("You will discover %(nick)s's "
                                        "role at dawn tomorrow.") %
                                        {'nick': target_nick},
                                'target': event.sender['id'],
                                'notice': True})
            self.seer_targets[sender] = target

    def dawn (self, event):
        """Start of day.

        During this state, villagers discover what happened overnight and
        discuss who to lynch. The next state is noon."""

        self.state = self.dawn

        eaten = frozenset(self.wolf_targets.itervalues())
        if eaten:
            victim = choice(list(eaten))
            msg = (_("The village awakes to find that werewolves have "
                    "devoured %(nick)s the %(role)s in the night.") %
                    {'nick': victim, 'role': _(self.roles[victim])})
            self.death(victim)
        else:
            msg = _("The werewolves were abroad last night.")
        event.addresponse(msg)
        self.wolf_targets = {}

        for seer in self.seers:
            target = self.seer_targets.get(seer)
            if target is not None:
                # seer saw somebody
                if target in self.roles:
                    # that somebody is alive
                    msg = (_("%(nick)s is a %(role)s") %
                            {'nick': target,
                            'role': _(self.roles[target])})
                else:
                    msg = (_("The wolves also had %(nick)s "
                            "in mind last night.") %
                            {'nick': target})
                
                event.addresponse({'reply': msg,
                                    'target': seer,
                                    'notice': True})
        self.seer_targets = {}

        if not self.endgame(event):
            event.addresponse(_("Villagers, you have 60 seconds "
                                "to discuss suspicions and cast accusations."))
            self.say_survivors(event)

            self.timed_goto(event, 60, self.noon)

    def noon (self, event):
        """Start of voting.

        Next state is dusk."""

        self.state = self.noon
        event.addresponse(_("Villagers, you have 60 seconds to cast "
                            "your vote to lynch somebody."))

        self.votes = {}

        self.timed_goto(event, 60, self.dusk)

    @match(r"^(?:lynch(?:es)?|votes?)\s+(?:for\s+|against\s+)(\S+)$")
    def vote (self, event, target_nick):
        """Vote to lynch a player."""

        if (self.state != self.noon or
            event.sender['nick'] not in self.roles):
            return
        
        target = self.identify(target_nick)
        if target is None:
            event.addresponse(_("%(nick)s is not playing.") %
                                {'nick': target_nick})
        else:
            self.votes[event.sender['nick']] = target
            event.addresponse({'reply': _("%(voter)s voted for %(target)s.") %
                                        {'target': target,
                                        'voter': event.sender['nick']},
                                'target': self.channel})

    def dusk (self, event):
        """Counting of votes and lynching.

        Next state is night."""

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
                event.addresponse(_("The votes are tied. Picking randomly..."))
            victim = choice(list(victims))
            msg = (_("The ballots are in, "
                     "and %(nick)s the %(role)s has been lynched.") %
                    {'nick': victim, 'role': _(self.roles[victim])})
            self.death(victim)
        else:
            msg = _("Nobody voted.")
        event.addresponse(msg)
            
        if not self.endgame(event):
            self.timed_goto(event, 10, self.night)

    def say_survivors (self, event):
        """Name surviving players."""

        event.addresponse(_("The surviving villagers are: %(villagers)s.") %
                            {'villagers': ', '.join(sorted(player
                                    for player in self.roles.iterkeys()))})

    def identify (self, nick):
        """Find the identity (correctly-capitalised nick) of a player.

        Returns None if nick is not playing."""

        for player in self.roles.iterkeys():
            if player.lower() == nick.lower():
                return player
        else:
            return None

    def death (self, player):
        """Remove player from game."""

        if self.state == self.prestart:
            self.players.remove(player)
        elif self.state is not None:
            del self.roles[player]

            for role in (self.wolves, self.seers):
                try:
                    role.remove(player)
                except ValueError:
                    pass

    def endgame (self, event):
        """Check if the game is over.

        If the game is over, announce the winners and return True. Otherwise
        return False."""

        if 2*len(self.wolves) >= len(self.roles):
            # werewolves win
            event.addresponse(_("The werewolves devour the remaining "
                                "villagers and win. OM NOM NOM."))
            event.addresponse(_("The winning werewolves were: %(wolves)s") %
                                {'wolves': ', '.join(self.wolves)})
        elif not self.wolves:
            # villagers win
            event.addresponse(_("The villagers have defeated the werewolves. "
                                "Vigilantism FTW."))
            event.addresponse(_("The surviving villagers were: %(villagers)s") %
                                {'villagers': ', '.join(self.roles)})
        else:
            return False

        self.state = None
        games.remove(self)
        return True

    def timed_goto(self, event, delay, target):
        """Like call_later, but does nothing if state has changed."""

        from_state = self.state
        log.debug("Going from state %s to %s in %i seconds." %
                    (from_state, target, delay))
        def goto (evt):
            """Change state if it hasn't already changed."""
            if self.state == from_state:
                target(evt)

        ibid.dispatcher.call_later(delay, goto, event)

    def rename (self, oldnick, newnick):
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

    def state_change (self, event):
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
                event.addresponse({'reply': 
                                   _("%(nick)s has fled the game in terror.") %
                                            {'nick': nick},
                                   'target': self.channel})
                self.death(nick)

class StateProcessor (Processor):
    event_types = ('state',)

    @handler
    def state_change (self, event):
        for game in self.games:
            game.state_change(event)
