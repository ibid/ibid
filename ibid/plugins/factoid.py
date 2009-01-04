from datetime import datetime
from random import choice
from time import localtime, strftime
import re

from sqlalchemy import Column, Integer, Unicode, DateTime, Table, MetaData
from sqlalchemy.orm import relation, mapper
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql import func

import ibid
from ibid.plugins import Processor, match, handler, authorise

metadata = MetaData()

name_table = Table('factoid_names', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode),
    Column('factoid_id', Integer),
    Column('identity', Unicode),
    Column('time', DateTime),
    )

class FactoidName(object):

    def __init__(self, name, identity, factoid_id=None):
        self.name = name
        self.factoid_id = factoid_id
        self.identity = identity
        self.time = datetime.now()

    def __repr__(self):
        return u'<FactoidName %s %s>' % (self.name, self.factoid_id)

value_table = Table('factoid_values', metadata,
    Column('id', Integer, primary_key=True),
    Column('value', Unicode),
    Column('factoid_id', Integer),
    Column('identity', Unicode),
    Column('time', DateTime),
    )

class FactoidValue(object):

    def __init__(self, value, identity, factoid_id=None):
        self.value = value
        self.factoid_id = factoid_id
        self.identity = identity
        self.time = datetime.now()

    def __repr__(self):
        return u'<FactoidValue %s %s>' % (self.factoid_id, self.value)

mapper(FactoidName, name_table, properties={'factoids': relation(FactoidValue, primaryjoin=value_table.c.factoid_id==name_table.c.factoid_id, foreign_keys=[value_table.c.factoid_id], cascade='')})
mapper(FactoidValue, value_table)

percent_escaped_re = re.compile(r'(?<!\\\\)\\%')
percent_re = re.compile(r'(?<!\\)%')
action_re = re.compile(r'^\s*<action>\s*')
reply_re = re.compile(r'^\s*<reply>\s*')
verbs = ('is', 'are', 'has', 'have', 'was', 'were', 'do', 'does', 'can', 'should', 'would')

def escape_name(name):
    return name.replace('%', '\\%').replace('_', '\\_').replace('$arg', '%')

class Utils(Processor):

    @match(r'^literal\s+(.+)$')
    def literal(self, event, name):

        session = ibid.databases.ibid()
        fact = session.query(FactoidName).filter(func.lower(FactoidName.name)==escape_name(name).lower()).first()
        values = []
        for factoid in fact.factoids:
            values.append(factoid.value)
        event.addresponse(', '.join(values))

        session.close()

    @match(r'^forget\s+(.+)$')
    @authorise(u'factoid')
    def forget(self, event, name):

        session = ibid.databases.ibid()
        fact = session.query(FactoidName).filter(func.lower(FactoidName.name)==escape_name(name).lower()).first()
        if fact:
            if session.query(FactoidName).filter_by(factoid_id=fact.factoid_id).count() == 1:
                for factoid in fact.factoids:
                    session.delete(factoid)
            session.delete(fact)
            session.commit()
            session.close()
            event.addresponse(True)
        else:
            event.addresponse(u"I didn't know about %s anyway" % name)

    @match(r'^(.+)\s+is\s+the\s+same\s+as\s+(.+)$')
    @authorise(u'factoid')
    def alias(self, event, target, source):

        session = ibid.databases.ibid()
        fact = session.query(FactoidName).filter(func.lower(FactoidName.name)==escape_name(source).lower()).first()
        if fact:
            new = FactoidName(escape_name(target), event.identity, fact.factoid_id)
            session.add(new)
            session.commit()
            session.close()
            event.addresponse(True)
        else:
            event.addresponse(u"I don't know about %s" % name)

class Get(Processor):

    verbs = verbs
    priority = 900
    interrogatives = ('what', 'wtf', 'where', 'when', 'who')

    def setup(self):
        self.get_factoid.im_func.pattern = re.compile('^(?:(?:%s)\s+(%s)\s+)?(.+)$' % ('|'.join(self.interrogatives), '|'.join(self.verbs)))

    @handler
    def get_factoid(self, event, verb, name):

        session = ibid.databases.ibid()
        fact = session.query(FactoidName).filter(":fact LIKE name ESCAPE '\\'").params(fact=name).first()
        if fact:
            reply = choice(fact.factoids).value
            pattern = percent_escaped_re.sub('(.*)', re.escape(fact.name)).replace('\\\\\\%', '%').replace('\\\\\\_', '_')

            position = 1
            for capture in re.match(pattern, name, re.I).groups():
                if capture.startswith('$arg'):
                    return
                reply = reply.replace('$%s' % position, capture)
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
                    reply = '%s %s' % (percent_re.sub('$arg', fact.name).replace('\\%', '%').replace('\\_', '_'), reply)
                    event.addresponse(reply)

        session.close()

class Set(Processor):

    verbs = verbs
    priority = 910
    
    def setup(self):
        self.set_factoid.im_func.pattern = re.compile('^(no[,.: ]\s*)?(.+?)\s+(?:=(\S+)=)?(?(3)|(%s))(\s+also)?\s+(.+?)$' % '|'.join(self.verbs))

    @handler
    @authorise(u'factoid')
    def set_factoid(self, event, correction, name, verb1, verb2, addition, value):
        verb = verb1 and verb1 or verb2

        session = ibid.databases.ibid()
        fact = session.query(FactoidName).filter(func.lower(FactoidName.name)==escape_name(name).lower()).first()
        if fact:
            if correction:
                for factoid in fact.factoids:
                    session.delete(factoid)
            elif not addition:
                event.addresponse(u"I already know stuff about %s" % name)
                return
        else:
            max = session.query(FactoidName).order_by(desc(FactoidName.factoid_id)).first()
            if max:
                next = max.factoid_id + 1
            else:
                next = 1
            fact = FactoidName(escape_name(name), event.identity, next)
            session.add(fact)
            session.commit()

        if not reply_re.match(value) and not action_re.match(value):
            value = '%s %s' % (verb, value)
        factoid = FactoidValue(value, event.identity, fact.factoid_id)
        session.add(factoid)
        session.commit()
        session.close()
        event.addresponse(True)

# vi: set et sta sw=4 ts=4:
