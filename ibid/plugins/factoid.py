from datetime import datetime
from random import choice
from time import localtime, strftime
import re

from sqlalchemy import Column, Integer, Unicode, DateTime, Table, MetaData
from sqlalchemy.orm import relation, mapper
from sqlalchemy.sql.expression import desc

import ibid
from ibid.plugins import Processor, match, handler

metadata = MetaData()

name_table = Table('factoid_names', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode),
    Column('verb', Unicode),
    Column('factoid_id', Integer),
    Column('who', Unicode),
    Column('time', DateTime),
    )

class Fact(object):

    def __init__(self, name, verb, factoid_id, who=None):
        self.name = name
        self.verb = verb
        self.factoid_id = factoid_id
        self.who = who
        self.time = datetime.now()

    def __repr__(self):
        return u'<Fact %s %s %s>' % (self.name, self.verb, self.factoid_id)

value_table = Table('factoid_values', metadata,
    Column('id', Integer, primary_key=True),
    Column('value', Unicode),
    Column('factoid_id', Integer),
    Column('who', Unicode),
    Column('time', DateTime),
    )

class Factoid(object):

    def __init__(self, value, who, factoid_id=None):
        self.value = value
        self.factoid_id = factoid_id
        self.who = who
        self.time = datetime.now()

    def __repr__(self):
        return u'<Factoid %s %s>' % (self.factoid_id, self.value)

mapper(Fact, name_table, properties={
    'factoids': relation(Factoid, primaryjoin=value_table.c.factoid_id==name_table.c.factoid_id, foreign_keys=[value_table.c.factoid_id])})
mapper(Factoid, value_table, properties={
    'facts': relation(Fact, primaryjoin=value_table.c.factoid_id==name_table.c.factoid_id, foreign_keys=[name_table.c.factoid_id])})

percent_escaped_re = re.compile(r'(?<!\\\\)\\%')
percent_re = re.compile(r'(?<!\\)%')
args = ('$one', '$two', '$three', '$four', '$five', '$six', '$seven', '$eight', '$nine', '$ten')
action_re = re.compile(r'\s*<action>\s*')
reply_re = re.compile(r'\s*<reply>\s*')
verbs = ('is', 'are', 'has', 'have', 'was', 'were', 'do', 'does', 'can', 'should', 'would')

class Literal(Processor):

    @match(r'literal\s+(.+)')
    def literal(self, event, name):

        session = ibid.databases.ibid()
        facts = session.query(Fact).filter_by(name=name.replace('%', '\\%').replace('_', '\\_').replace('$arg', '%')).all()
        if facts:
            replies = []
            for fact in facts:
                values = []
                for factoid in fact.factoids:
                    values.append(factoid.value)
                replies.append('%s =%s= %s' % (percent_re.sub('$arg', fact.name).replace('\\%', '%').replace('\\_', '_'), fact.verb, ', '.join(values)))
            event.addresponse('; '.join(replies))

        session.close()

class Get(Processor):

    verbs = verbs
    priority = 900
    interrogatives = ('what', 'wtf', 'where', 'when', 'who')

    def setup(self):
        self.get_factoid.im_func.pattern = re.compile('^(?:(?:%s)\s+(%s)\s+)?(.+)$' % ('|'.join(self.interrogatives), '|'.join(self.verbs)))

    @handler
    def get_factoid(self, event, verb, name):

        session = ibid.databases.ibid()
        fact = session.query(Fact).filter(":fact LIKE name ESCAPE '\\'").params(fact=name).first()
        if fact:
            reply = choice(fact.factoids).value
            pattern = percent_escaped_re.sub('(.*)', re.escape(fact.name)).replace('\\\\\\%', '%').replace('\\\\\\_', '_')

            position = 0
            for capture in re.match(pattern, name, re.I).groups():
                reply = reply.replace(args[position], capture)
                position = position + 1

            reply = reply.replace('$who', event.who)
            reply = reply.replace('$channel', event.channel)
            now = localtime()
            reply = reply.replace('$year', str(now[0]))
            reply = reply.replace('$month', str(now[1]))
            reply = reply.replace('$day', str(now[2]))
            reply = reply.replace('$hour', str(now[3]))
            reply = reply.replace('$minute', str(now[4]))
            reply = reply.replace('$second', str(now[5]))
            reply = reply.replace('$date', strftime('%Y/%m/%d', now))
            reply = reply.replace('$time', strftime('%H:%M:%S', now))
            reply = reply.replace('$dow', strftime('%A', now))

            (reply, count) = action_re.subn('', reply)
            if count:
                event.addresponse({'action': True, 'reply': reply})
            else:
                (reply, count) = reply_re.subn('', reply)
                if count:
                    event.addresponse({'reply': reply})
                else:
                    reply = '%s %s %s' % (percent_re.sub('$arg', fact.name).replace('\\%', '%').replace('\\_', '_'), fact.verb, reply)
                    event.addresponse(reply)

        session.close()

class Set(Processor):

    verbs = verbs
    priority = 910
    
    def setup(self):
        verbs = '|'.join(self.verbs)
        self.set_factoid.im_func.pattern = re.compile('^(no[,.: ]\s*)?(.+?)\s+(?:=(%s)=)?(?(3)|(%s))(\s+also)?\s+([^=]+?)$' % (verbs, verbs))

    @handler
    def set_factoid(self, event, correction, name, verb1, verb2, addition, value):
        verb = verb1 and verb1 or verb2

        session = ibid.databases.ibid()
        name_escaped = name.replace('%', '\\%').replace('_', '\\_').replace('$arg', '%')
        fact = session.query(Fact).filter_by(name=name_escaped).first()
        if fact:
            if correction:
                while len(fact.factoids) > 0:
                    del fact.factoids[0]
                session.commit()
            elif not addition:
                event.addresponse(u"I already know stuff about %s" % name)
                return
        else:
            max = session.query(Fact).order_by(desc(Fact.factoid_id)).first()
            fact = Fact(name_escaped, verb, max.factoid_id+1)

        factoid = Factoid(value, event.sender_id)
        fact.factoids.append(factoid)
        session.add(fact)
        session.commit()
        session.close()
        event.addresponse(True)

# vi: set et sta sw=4 ts=4:
