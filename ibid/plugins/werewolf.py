from random import shuffle
from ibid.plugins import Processor, handler, match, authorise
from ibid.config import Option

def _ (arg):
    return arg

class WerewolfGame (Processor):
    feature = 'werewolf'

    def __init__ (self, starter):
        self.state = None

    def prestart (self, event):
        """Initiate a game.

        This is the state from initiation to start of game. Next state is start."""

        if self.state:
            return

        self.state = self.prestart

        self.players = []
        event.addresponse(_("%{starter}s has started a game of Werewolf. "
            "You have %{time}i seconds to join the game.") %
            {starter: self.players[0], self.time)
        self.timed_goto(60, self.start)

    def join (self, event):
        if self.state != self.prestart:
            return
        
        self.players.append(event.sender)
        event.addresponse(_("%{num}i. %{player}s has joined.") %
            {'num': len(self.players), 'player': event.sender['nick']}))

    def start (self, event):
        """Start game.

        This state doesn't actually last any time. The next state is night."""

        self.state = self.start

        event.addresponse(_("%{num}i players joined."
            "Please wait while I assign roles.") %
            {'num': len(self.players)})

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
            event.addresponse({'reply': _("""%{name}s, you are a %{role}s.""" %
                                    {'name': player['nick'], 'role': role},
                                'target': player['id']})

        self.timed_goto(30, self.night)

    def night (self, event):
        self.state = self.night
        event.addresponse(_("Night falls... most villagers are sleeping, "
                            "but outside, something stirs."))
        event.addresponse(_("Werewolf, to kill somebody, "
                             "use the KILL command"))
        event.addresponse(_("Seer, to discover somebody's true form, "
                             "use the SEE command"))
        self.say_survivors(event)

        self.timed_goto(60, self.dawn)

    def kill (self, event):
        if self.state != self.night:
            return

    def say_survivors (self, event):
        event.addresponse(_("The surviving villagers are: %{villagers}s.") %
                            {'villagers': ', '.join(sorted(
                                player['nick']
                                    for player in self.roles.iterkeys())))
