from random import shuffle, choice
import ibid
import logging
from ibid.plugins import Processor, handler, match, authorise
from ibid.config import Option
from collections import defaultdict

log = logging.getLogger('plugins.werewolf')

def _ (arg):
    return arg

class WerewolfGame (Processor):
    feature = 'werewolf'
    state = None

    player_limit = IntOption('min_players', 'the minimum number of players', 5)
    addressed = BoolOption('addressed', 'messages must be addressed to bot', False)

    @match(r"^(?:start|play|begin)\s+werewolf$")
    def prestart (self, event):
        """Initiate a game.

        This is the state from initiation to start of game. Next state is start."""

        if self.state:
            log.debug("Not starting game: already in state %s." % self.state)
            return

        if not event.public:
            log.debug("Event is not public.")
            event.addresponse(_("you must start the game in public."))
            return

        self.state = self.prestart
        self.channel = event.channel

        starter = event.sender['nick']
        self.players = set((starter,))
        event.addresponse(_("you have started a game of Werewolf. "
            "Everybody has 60 seconds to join the game."))

        log.debug("Starting game.")
        self.timed_goto(event, 60, self.start)

    @match(r"^join$")
    def join (self, event):
        if self.state != self.prestart:
            log.debug("Not joining: already in state %s." % self.state)
            return
        
        if event.sender['nick'] not in self.players:
            self.players.add(event.sender['nick'])
            event.addresponse({'reply': _("Player %(player)s has joined "
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

        if players < self.player_limit:
            event.addresponse(_("Not enough players. Try again later."))
            self.state = None
            return

        event.addresponse(_("%(num)i players joined. "
            "Please wait while I assign roles.") %
            {'num': len(self.players)})

        self.players = list(self.players)
        shuffle(self.players)
        self.wolves = self.players[:1]
        self.seers = self.players[1:2]

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

    @match(r"^(?:kill|see)\s+(\S+)$")
    def kill_see (self, event, target_nick):
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
                
                event.addresponse({'reply': msg, 'target': seer})
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

    @match(r"^(?:lynch|vote)\s+(\S+)$")
    def vote (self, event, target_nick):
        if (self.state != self.noon or
            event.sender['nick'] not in self.roles or
            event.public):
            return
        
        target = self.identify(target_nick)
        if target is None:
            event.addresponse(_("%(nick)s is not playing.") %
                                {'nick': target_nick})
        else:
            self.votes[event.sender['nick']] = target
            event.addresponse({'reply': _("%(voter)s have voted for %(target)s.") %
                                        {'target': target,
                                        'voter': event.sender['nick']},
                                'target': self.channel})

    def dusk (self, event):
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
            msg = (_("The ballots are in, and %(nick)s the %(role)s has been lynched.") %
                    {'nick': victim, 'role': _(self.roles[victim])})
            self.death(victim)
        else:
            msg = _("Nobody voted.")
        event.addresponse(msg)
            
        if not self.endgame(event):
            self.timed_goto(event, 10, night)

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
        del self.roles[player]

        for role in (self.wolves, self.seers):
            try: role.remove(player)
            except ValueError: pass

    def endgame (self, event):
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
        return True

    def timed_goto(self, event, delay, target):
        from_state = self.state
        def go (evt):
            if self.state == from_state:
                # only change state if it hasn't already changed
                target(evt)

        ibid.dispatcher.call_later(delay, go, event)
