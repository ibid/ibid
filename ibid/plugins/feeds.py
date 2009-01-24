import re
from datetime import datetime
import logging

from sqlalchemy import Column, Integer, Unicode, DateTime, UnicodeText
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import feedparser
from html2text import html2text_file

import ibid
from ibid.plugins import Processor, match, authorise

Base = declarative_base()

log = logging.getLogger('plugins.feeds')

class Feed(Base):
    __tablename__ = 'feeds'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(32), unique=True, nullable=False)
    url = Column(UnicodeText, nullable=False)
    identity = Column(Integer, nullable=False)
    time = Column(DateTime, nullable=False)

    def __init__(self, name, url, identity):
        self.name = name
        self.url = url
        self.identity = identity
        self.time = datetime.now()

class Manage(Processor):

    permission = u'feeds'

    @match(r'^add\s+feed\s+(.+?)\s+as\s+(.+?)$')
    @authorise
    def add(self, event, url, name):
        session = ibid.databases.ibid()
        feed = session.query(Feed).filter(func.lower(Feed.name)==name.lower()).first()

        if feed:
            event.addresponse(u"I already have the %s feed" % name)
        else:
            feed = Feed(unicode(name), unicode(url), event.identity)
            session.save(feed)
            session.flush()
            event.addresponse(True)
            log.info(u"Added feed '%s' by %s/%s (%s): %s", name, event.account, event.identity, event.sender, url)

        session.close()

    @match(r'^list\s+feeds$')
    def list(self, event):
        session = ibid.databases.ibid()
        feeds = session.query(Feed).all()
        event.addresponse(', '.join([feed.name for feed in feeds]))

    @match(r'^remove\s+(.+?)\s+feed$')
    @authorise
    def remove(self, event, name):
        session = ibid.databases.ibid()
        feed = session.query(Feed).filter(func.lower(Feed.name)==name.lower()).first()

        if not feed:
            event.addresponse(u"I don't have the %s feed anyway" % name)
        else:
            session.delete(feed)
            log.info(u"Deleted feed '%s' by %s/%s (%s): %s", name, event.account, event.identity, event.sender, feed.url)
            session.flush()
            event.addresponse(True)

        session.close()

class Retrieve(Processor):

    @match(r'^(?:latest|last)\s+(?:(\d+)\s+)?articles\s+from\s+(.+?)(?:\s+start(?:ing)?\s+(?:at\s+|from\s+)?(\d+))?$')
    def list(self, event, number, name, start):
        number = number and int(number) or 10
        start = start and int(start) or 0

        session = ibid.databases.ibid()
        feed = session.query(Feed).filter(func.lower(Feed.name)==name.lower()).first()
        session.close()

        if not feed:
            event.addresponse(u"I don't know about the %s feed" % name)
            return

        feed = feedparser.parse(feed.url)
        event.addresponse(', '.join(['%s: "%s"' % (feed.entries.index(entry), entry.title) for entry in feed.entries[start:number+start]]))

    @match(r'^article\s+(?:(\d+)|/(.+?)/)\s+from\s+(.+?)$')
    def article(self, event, number, pattern, name):
        session = ibid.databases.ibid()
        feed = session.query(Feed).filter(func.lower(Feed.name)==name.lower()).first()
        session.close()

        if not feed:
            event.addresponse(u"I don't know about the %s feed" % name)
            return

        feed = feedparser.parse(feed.url)
        article = None

        if number:
            if int(number) >= len(feed.entries):
                event.addresponse(u"That's old news dude")
                return
            article = feed.entries[int(number)]

        else:
            pattern = re.compile(pattern)
            for entry in feed.entries:
                if pattern.search(entry.title):
                    article = entry
                    break

            if not article:
                event.addresponse(u"Are you making up news again?")
                return

        if 'summary' in article:
            summary = article.summary
        else:
            if article.content[0].type in ('application/xhtml+xml', 'text/html'):
                summary = html2text_file(article.content[0].value, None)
            else:
                summary = article.content[0].value

        event.addresponse(u'"%s" %s : %s' % (article.title, article.link, summary))

# vi: set et sta sw=4 ts=4:
