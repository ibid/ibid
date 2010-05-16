# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from unicodedata import normalize
from random import choice, random, randrange
import re
from threading import Lock

from nickometer import nickometer

import ibid
from ibid.db import IbidUnicodeText, Boolean, Integer, Table, Column, \
                    ForeignKey, Base, VersionedSchema, relation
from ibid.db.models import Identity
from ibid.plugins import Processor, match
from ibid.config import IntOption, ListOption
from ibid.utils import human_join, indefinite_article, identity_name

features = {}

features['nickometer'] = {
    'description': u'Calculates how lame a nick is.',
    'categories': ('fun', 'calculate',),
}
class Nickometer(Processor):
    usage = u'nickometer [<nick>] [with reasons]'
    features = ('nickometer',)

    @match(r'^(?:nick|lame)-?o-?meter(?:(?:\s+for)?\s+(.+?))?(\s+with\s+reasons)?$')
    def handle_nickometer(self, event, nick, wreasons):
        nick = nick or event.sender['nick']
        if u'\ufffd' in nick:
            score, reasons = 100., ((u'Not UTF-8 clean', u'infinite'),)
        else:
            score, reasons = nickometer(normalize('NFKD', nick).encode('ascii', 'ignore'))

        event.addresponse(u'%(nick)s is %(score)s%% lame', {
            'nick': nick,
            'score': score,
        })
        if wreasons:
            if not reasons:
                reasons = ((u'A good, traditional nick', 0),)
            event.addresponse(u'Because: %s', u', '.join(['%s (%s)' % reason for reason in reasons]))

features['choose'] = {
    'description': u'Choose one of the given options.',
    'categories': ('fun', 'decide',),
}
class Choose(Processor):
    usage = u'choose <choice> or <choice>...'
    features = ('choose',)

    choose_re = re.compile(r'(?:\s*,\s*(?:or\s+)?)|(?:\s+or\s+)', re.I)

    @match(r'^(?:choose|choice|pick)\s+(.+)$')
    def choose(self, event, choices):
        event.addresponse(u'I choose %s', choice(self.choose_re.split(choices)))

features['coffee'] = {
    'description': u'Times coffee brewing and reserves cups for people',
    'categories': ('fun', 'monitor',),
}
class Coffee(Processor):
    usage = u'coffee (on|please)'
    features = ('coffee',)

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

features['insult'] = {
    'description': u'Slings verbal abuse at someone',
    'categories': ('fun',),
}
class Insult(Processor):
    usage = u"""(flame | insult) <person>
    (swear | cuss | explete) [at <person>]"""
    features = ('insult',)

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

    swearlength = IntOption('swearlength', 'Number of expletives to swear with',
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

object_pat = r"(?:(his|her|their|its|my|our|\S+(?:'s|s')|" \
            r"the|a|an|this|these|that|those|some)\s+)?(.*)"

features['bucket'] = {
    'description': u'Exchanges objects with people',
    'categories': ('fun',),
}

class EmptyBucketException(Exception): pass

class Item(Base):
    __table__ = Table('bucket_items',
        Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('description', IbidUnicodeText, nullable=False, index=True),
        Column('determiner', IbidUnicodeText, index=True),
        Column('carried', Boolean, nullable=False, index=True),
        Column('giver_id', Integer, ForeignKey('identities.id'), nullable=False),
        useexisting=True)

    __table__.versioned_schema = VersionedSchema(__table__, 1)

    giver = relation('Identity')

    def __init__(self, description, determiner, giver):
        self.description = description
        self.determiner = determiner
        self.carried = True
        self.giver_id = giver

    @classmethod
    def carried_items(cls, session):
        return session.query(cls).filter_by(carried=True)

    @classmethod
    def take_item(cls, session):
        items = cls.carried_items(session)
        num = items.count()
        if num:
            item = items[randrange(0, num)]
        else:
            raise EmptyBucketException

        item.carried = False
        session.save_or_update(item)

        return item

    def __unicode__(self):
        if self.determiner:
            return self.determiner + u' ' + self.description
        else:
            return self.description

class ExchangeAction(Processor):
    features = ('bucket',)
    event_types = (u'action',)

    addressed = False

    @match(r"^(?:gives|hands)\s+(\S+)\s+" + object_pat + "$")
    def give(self, event, addressee, determiner, object):
        if addressee in ibid.config.plugins['core']['names']:
            return exchange(event, determiner, object)

class ExchangeMessage(Processor):
    usage = u"""(have|take) <object>
    what are you carrying?"""
    features = ('bucket',)

    @match(r"^(?:have|take)\s+" + object_pat + "$")
    def have(self, event, determiner, object):
        if determiner in ('his', 'her', 'their', 'its'):
            event.addresponse("I don't know whose %s you're talking about",
                                object)
        else:
            return exchange(event, determiner, object)

    @match(r'^(?:what\s+(?:are|do)\s+you\s+)?(?:carrying|have)$')
    def query_carrying(self, event):
        items = Item.carried_items(event.session).all()
        if items:
            event.addresponse(u"I'm carrying %s",
                                human_join(map(unicode, items)))
        else:
            event.addresponse(u"I'm not carrying anything")

    @match(r'^(?:who\s+gave\s+you|where\s+did\s+you\s+get)\s+'
                + object_pat + '$')
    def query_giver(self, event, determiner, object):
        items = Item.carried_items(event.session) \
                .filter_by(description=object).all()
        if items:
            event.addresponse(u'I got ' +
                human_join(u'%(item)s from %(giver)s' %
                                {'item': item,
                                'giver': identity_name(event, item.giver)}
                            for item in items))
        else:
            event.addresponse("There's nothing like that in my bucket.")

def exchange(event, determiner, object):
    who = event.sender['nick']

    if determiner is None:
        determiner = ''

    detl = determiner.lower()

    # determine how to refer to the giver in the genitive case
    if detl in ('their', 'our') and who[-1] in 'sS':
        # giver's name is a plural ending in 's'
        genitive = who + "'"
    elif detl.endswith("s'") or detl.endswith("'s"):
        genitive = determiner
    else:
        genitive = who + "'s"

    if detl == 'the':
        taken = u'the ' + object
    else:
        taken = genitive + u' ' + object

    try:
        event.addresponse(u'hands %(who)s %(carrying)s '
                            u'in exchange for %(taken)s',
                            {'who': who,
                             'carrying': Item.take_item(event.session),
                             'taken': taken},
                            action=True)
    except EmptyBucketException:
        event.addresponse(u'takes %s but has nothing to give in exchange',
                            taken, action=True)

    # determine which determiner we will use when talking about this object in
    # the future -- we only want to refer to it by the giver's name if the giver
    # implied that it was theirs, and we don't want to use demonstratives
    if detl in ('this', 'that'):
        # object is definitely singular
        determiner = indefinite_article(object)
    elif detl in ('my', 'our', 'his', 'her', 'its', 'their'):
        determiner = genitive
    elif detl in ('these', 'those'):
        determiner = u'some'

    if determiner:
        item = Item(object, determiner, event.identity)
    else:
        item = Item(object, None, event.identity)

    event.session.save_or_update(item)

# vi: set et sta sw=4 ts=4:
