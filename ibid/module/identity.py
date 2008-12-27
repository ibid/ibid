from sqlalchemy.orm.exc import NoResultFound

import ibid
from ibid.module import Module
from ibid.decorators import *
from ibid.models import Person, Identity, Attribute

class People(Module):

    @addressed
    @notprocessed
    @match('^\s*add\s+person\s+(.+)\s*$')
    def process(self, event, username):
        session = ibid.databases.ibid()
        person = Person(username)
        session.add(person)
        session.commit()
        session.close()
        event.addresponse(u'Done')

class Identities(Module):

    @addressed
    @notprocessed
    @match('^\s*(I|.+?)\s+(?:is|am)\s+(.+)\s+on\s+(.+)\s*$')
    def process(self, event, username, identity, source):
        session = ibid.databases.ibid()
        if username.upper() == 'I':
            if 'user' not in event:
                event.addresponse(u"I don't know who you are")
                return
            username = event.user

        try:
            person = session.query(Person).filter_by(username=username).one()
        except NoResultFound:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first" % username)
            return

        person.identities.append(Identity(source, identity))
        session.add(person)
        session.commit()
        session.close()
        event.addresponse(u'Done')

class Attributes(Module):

    @addressed
    @notprocessed
    @match(r"^\s*(my|.+?)(?:\'s)?\s+(.+)\s+is\s+(.+)\s*$")
    def process(self, event, username, name, value):
        if username.lower() == 'my':
            if 'user' not in event:
                event.addresponse(u"I don't know who you are")
                return
            username = event.user

        session = ibid.databases.ibid()
        try:
            person = session.query(Person).filter_by(username=username).one()
        except NoResultFound:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first" % username)
            return

        person.attributes.append(Attribute(name, value))
        session.add(person)
        session.commit()
        session.close()
        event.addresponse(u'Done')

class Describe(Module):

    @addressed
    @notprocessed
    @match('^\s*who\s+(?:is|am)\s+(I|.+?)\s*$')
    def process(self, event, username):
        if username.upper() == 'I':
            if 'user' not in event:
                event.addresponse(u"I don't know who you are")
                return
            username = event.user

        session = ibid.databases.ibid()
        try:
            person = session.query(Person).filter_by(username=username).one()
        except NoResultFound:
            event.addresponse(u"%s doesn't exist. Please use 'add person' first" % username)
            return

        event.addresponse(str(person))
        for identity in person.identities:
            event.addresponse(str(identity))
        for attribute in person.attributes:
            event.addresponse(str(attribute))
        session.close()

class Identify(Module):

    def __init__(self, name):
        Module.__init__(self, name)
        self.cache = {}

    @message
    def process(self, event):
        if 'sender_id' in event:
            if event.sender in self.cache:
                event.user = self.cache[event.sender]
                return

            account = identify(event.sender_id, event.source)

            if account:
                event.user = account.username
                self.cache[event.sender] = event.user

def identify(user, source):

    session = ibid.databases.ibid()
    try:
        identity = session.query(Identity).filter_by(source=source).filter_by(identity=user).one()
        return identity.person
    except NoResultFound:
        return None
    finally:
        session.close()
        
# vi: set et sta sw=4 ts=4:
