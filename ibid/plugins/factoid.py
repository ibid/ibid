from datetime import datetime
from random import choice
from time import localtime, strftime
import re

from sqlalchemy import Column, Integer, Unicode, DateTime, Table, MetaData
from sqlalchemy.orm import relation, mapper

import ibid
from ibid.plugins import Processor, match

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

    def __init__(self, value, factoid_id, who=None):
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

sub_percent = re.compile(r'(?<!\\\\)\\%')
args = ['$one', '$two', '$three', '$four', '$five', '$six', '$seven', '$eight', '$nine', '$ten']
actionre = re.compile(r'\s*<action>\s*')
replyre = re.compile(r'\s*<reply>\s*')

class Get(Processor):

    @match(r'(.*)')
    def get_factoid(self, event, name):

        session = ibid.databases.ibid()
        fact = session.query(Fact).filter(":fact LIKE name ESCAPE '\\'").params(fact=name).first()
        if fact:
            reply = choice(fact.factoids).value
            pattern = sub_percent.sub('(.*)', re.escape(fact.name)).replace('\\\\\\%', '%')

            position = 0
            for capture in re.match(pattern, name).groups():
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

            (reply, count) = actionre.subn('', reply)
            if count:
                event.addresponse({'action': True, 'reply': reply})
            else:
                (reply, count) = replyre.subn('', reply)
                if not count:
                    reply = '%s %s %s' % (fact.name, fact.verb, reply)
                event.addresponse(reply)

# vi: set et sta sw=4 ts=4:
