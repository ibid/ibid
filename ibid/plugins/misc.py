import logging
from random import choice, random

import ibid
from ibid.plugins import Processor, match
from ibid.config import IntOption, ListOption
from ibid.utils import ibid_version, human_join

help = {}
log = logging.getLogger('plugins.misc')

help['coffee'] = u"Times coffee brewing and reserves cups for people"
class Coffee(Processor):
    u"""coffee (on|please)"""
    feature = 'coffee'

    pots = {}

    time = IntOption('coffee_time', u'Brewing time in seconds', 240)
    cups = IntOption('coffee_cups', u'Maximum number of cups', 4)

    def coffee_announce(self, event):
        event.addresponse(u"Coffee's ready for %s!",
                human_join(self.pots[(event.source, event.channel)]))
        del self.pots[(event.source, event.channel)]

    @match(r'^coffee\s+on$')
    def coffee_on(self, event):
        if (event.source, event.channel) in self.pots:
            if len(self.pots[(event.source, event.channel)]) >= self.cups:
                event.addresponse(u"There's already a pot on, and it's all reserved")
            elif event.sender['nick'] in self.pots[(event.source, event.channel)]:
                event.addresponse(u"You already have a pot on the go")
            else:
                event.addresponse(u"There's already a pot on. If you ask nicely, maybe you can have a cup")
            return

        self.pots[(event.source, event.channel)] = [event.sender['nick']]
        ibid.dispatcher.call_later(self.time, self.coffee_announce, event)

        event.addresponse(choice((
                u'puts the kettle on',
                u'starts grinding coffee',
                u'flips the salt-timer',
                u'washes some mugs',
            )), action=True)

    @match('^coffee\s+(?:please|pls)$')
    def coffee_accept(self, event):
        if (event.source, event.channel) not in self.pots:
            event.addresponse(u"There isn't a pot on")

        elif len(self.pots[(event.source, event.channel)]) >= self.cups:
            event.addresponse(u"Sorry, there aren't any more cups left")

        elif event.sender['nick'] in self.pots[(event.source, event.channel)]:
            event.addresponse(u"Now now, we don't want anyone getting caffeine overdoses")

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

help['insult'] = u"Slings verbal abuse at someone"
class Insult(Processor):
    u"""
    (flame | insult) <person>
    (swear | cuss | explete) [at <person>]
    """
    feature = 'insult'

    adjectives = ListOption('adjectives', 'List of adjectives', (
        u'acidic', u'antique', u'artless', u'base-court', u'bat-fowling',
        u'bawdy', u'beef-witted', u'beetle-headed', u'beslubbering',
        u'boil-brained', u'bootless', u'churlish', u'clapper-clawed',
        u'clay-brained', u'clouted', u'cockered', u'common-kissing',
        u'contemptible', u'coughed-up', u'craven', u'crook-pated',
        u'culturally-unsound', u'currish', u'dankish', u'decayed',
        u'despicable', u'dismal-dreaming', u'dissembling', u'dizzy-eyed',
        u'doghearted', u'dread-bolted', u'droning', u'earth-vexing',
        u'egg-sucking', u'elf-skinned', u'errant', u'evil', u'fat-kidneyed',
        u'fawning', u'fen-sucked', u'fermented', u'festering', u'flap-mouthed',
        u'fly-bitten', u'fobbing', u'folly-fallen', u'fool-born', u'foul',
        u'frothy', u'froward', u'full-gorged', u'fulminating', u'gleeking',
        u'goatish', u'gorbellied', u'guts-griping', u'hacked-up', u'halfbaked',
        u'half-faced', u'hasty-witted', u'headless', u'hedge-born',
        u'hell-hated', u'horn-beat', u'hugger-muggered', u'humid',
        u'idle-headed', u'ill-borne', u'ill-breeding', u'ill-nurtured',
        u'imp-bladdereddle-headed', u'impertinent', u'impure', u'industrial',
        u'inept', u'infected', u'infectious', u'inferior', u'it-fowling',
        u'jarring', u'knotty-pated', u'left-over', u'lewd-minded',
        u'loggerheaded', u'low-quality', u'lumpish', u'malodorous',
        u'malt-wormy', u'mammering', u'mangled', u'measled', u'mewling',
        u'milk-livered', u'motley-mind', u'motley-minded', u'off-color',
        u'onion-eyed', u'paunchy', u'penguin-molesting', u'petrified',
        u'pickled', u'pignutted', u'plume-plucked', u'pointy-nosed', u'porous',
        u'pottle-deep', u'pox-marked', u'pribbling', u'puking', u'puny',
        u'railing', u'rank', u'reeky', u'reeling-ripe', u'roguish',
        u'rough-hewn', u'rude-growing', u'rude-snouted', u'rump-fed',
        u'ruttish', u'salty', u'saucy', u'saucyspleened', u'sausage-snorfling',
        u'shard-borne', u'sheep-biting', u'spam-sucking', u'spleeny',
        u'spongy', u'spur-galled', u'squishy', u'surly', u'swag-bellied',
        u'tardy-gaited', u'tastless', u'tempestuous', u'tepid', u'thick',
        u'tickle-brained', u'toad-spotted', u'tofu-nibbling', u'tottering',
        u'uninspiring', u'unintelligent', u'unmuzzled', u'unoriginal',
        u'urchin-snouted', u'vain', u'vapid', u'vassal-willed', u'venomed',
        u'villainous', u'warped', u'wayward', u'weasel-smelling',
        u'weather-bitten', u'weedy', u'wretched', u'yeasty',
    ))

    collections = ListOption('collections', 'List of collective nouns', (
        u'accumulation', u'ass-full', u'assload', u'bag', u'bucket',
        u'coagulation', u'enema-bucketful', u'gob', u'half-mouthful', u'heap',
        u'mass', u'mound', u'ooze', u'petrification', u'pile', u'plate',
        u'puddle', u'quart', u'stack', u'thimbleful', u'tongueful',
    ))

    nouns = ListOption('nouns', u'List of singular nouns', (
        u'apple-john', u'baggage', u'barnacle', u'bladder', u'boar-pig',
        u'bugbear', u'bum-bailey', u'canker-blossom', u'clack-dish',
        u'clotpole', u'coxcomb', u'codpiece', u'death-token', u'dewberry',
        u'flap-dragon', u'flax-wench', u'flirt-gill', u'foot-licker',
        u'fustilarian', u'giglet', u'gudgeon', u'haggard', u'harpy',
        u'hedge-pig', u'horn-beast', u'hugger-mugger', u'jolthead',
        u'lewdster', u'lout', u'maggot-pie', u'malt-worm', u'mammet',
        u'measle', u'minnow', u'miscreant', u'moldwarp', u'mumble-news',
        u'nut-hook', u'pigeon-egg', u'pignut', u'puttock', u'pumpion',
        u'ratsbane', u'scut', u'skainsmate', u'strumpet', u'varlet', u'vassal',
        u'whey-face', u'wagtail',
    ))

    plnouns = ListOption('plnouns', u'List of plural nouns', (
        u'anal warts', u'armadillo snouts', u'bat toenails', u'bug spit',
        u'buzzard gizzards', u'cat bladders', u'cat hair', u'cat-hair-balls',
        u'chicken piss', u'cold sores', u'craptacular carpet droppings',
        u'dog balls', u'dog vomit', u'dung', u'eel ooze', u'entrails',
        u"fat-woman's stomach-bile", u'fish heads', u'guano', u'gunk',
        u'jizzum', u'pods', u'pond scum', u'poop', u'poopy', u'pus',
        u'rat-farts', u'rat retch', u'red dye number-9', u'seagull puke',
        u'slurpee-backwash', u'snake assholes', u'snake bait', u'snake snot',
        u'squirrel guts', u'Stimpy-drool', u'Sun IPC manuals', u'toxic waste',
        u'urine samples', u'waffle-house grits', u'yoo-hoo',
    ))

    @match(r'^(?:insult|flame)\s+(.+)$')
    def insult(self, event, insultee):
        articleadj = choice(self.adjectives)
        articleadj = (articleadj[0] in u'aehiou' and u'an ' or u'a ') + articleadj

        event.addresponse(choice((
            u'%(insultee)s, thou %(adj1)s, %(adj2)s %(noun)s',
            u'%(insultee)s is nothing but %(articleadj)s %(collection)s of %(adj1)s %(plnoun)s',
        )), {
            'insultee': insultee,
            'adj1': choice(self.adjectives),
            'adj2': choice(self.adjectives),
            'articleadj': articleadj,
            'collection': choice(self.collections),
            'noun': choice(self.nouns),
            'plnoun': choice(self.plnouns),
        }, address=False)

    loneadjectives = ListOption('loneadjectives',
        'List of stand-alone adjectives for swearing', (
            'bloody', 'damn', 'fucking', 'shitting', 'sodding', 'crapping',
            'wanking', 'buggering',
    ))

    swearadjectives = ListOption('swearadjectives',
        'List of adjectives to be combined with swearnouns', (
            'reaming', 'lapping', 'eating', 'sucking', 'vokken', 'kak',
            'donder', 'bliksem', 'fucking', 'shitting', 'sodding', 'crapping',
            'wanking', 'buggering',
    ))

    swearnouns = ListOption('swearnouns',
        'List of nounes to be comined with swearadjectives', (
            'shit', 'cunt', 'hell', 'mother', 'god', 'maggot', 'father', 'crap',
            'ball', 'whore', 'goat', 'dick', 'cock', 'pile', 'bugger', 'poes',
            'hoer', 'kakrooker', 'ma', 'pa', 'naiier', 'kak', 'bliksem',
            'vokker', 'kakrooker',
    ))

    swearlength = IntOption('swearlength', 'Number of explitives to swear with',
                            15)

    @match(r'^(?:swear|cuss|explete)(?:\s+at\s+(?:the\s+)?(.*))?$')
    def swear(self, event, insultee):
        swearage = []
        for i in range(self.swearlength):
            if random() > 0.7:
                swearage.append(choice(self.loneadjectives))
            else:
                swearage.append(choice(self.swearnouns)
                                + choice(self.swearadjectives))
        if insultee is not None:
            swearage.append(insultee)
        else:
            swearage.append(choice(self.swearnouns))

        event.addresponse(u' '.join(swearage) + u'!', address=False)

# vi: set et sta sw=4 ts=4:
