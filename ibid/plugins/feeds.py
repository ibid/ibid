import re
from datetime import datetime
import logging
from urlparse import urljoin

from sqlalchemy import Column, Integer, Unicode, DateTime, UnicodeText, ForeignKey, Table
from sqlalchemy.sql import func
import feedparser
from html2text import html2text_file

from ibid.plugins import Processor, match, authorise
from ibid.models import Base, VersionedSchema
from ibid.utils import cacheable_download, get_html_parse_tree, human_join

help = {'feeds': u'Displays articles from RSS and Atom feeds'}

log = logging.getLogger('plugins.feeds')

class Feed(Base):
    __table__ = Table('feeds', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode(32), unique=True, nullable=False, index=True),
    Column('url', UnicodeText, nullable=False),
    Column('identity_id', Integer, ForeignKey('identities.id'), nullable=False, index=True),
    Column('time', DateTime, nullable=False),
    useexisting=True)

    class FeedSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.name, unique=True)
            self.add_index(self.table.c.identity_id)

    __table__.versioned_schema = FeedSchema(__table__, 2)

    feed = None
    entries = None

    def __init__(self, name, url, identity_id):
        self.name = name
        self.url = url
        self.identity_id = identity_id
        self.time = datetime.utcnow()
        self.update()

    def update(self):
        feedfile = cacheable_download(self.url, "feeds/%s-%i.xml" % (re.sub(r'\W+', '_', self.name), self.identity_id))
        self.feed = feedparser.parse(feedfile)
        self.entries = self.feed['entries']

class Manage(Processor):
    u"""add feed <url> as <name>
    list feeds
    remove <name> feed"""
    feature = 'feeds'

    permission = u'feeds'

    @match(r'^add\s+feed\s+(.+?)\s+as\s+(.+?)$')
    @authorise()
    def add(self, event, url, name):
        feed = event.session.query(Feed) \
                .filter(func.lower(Feed.name) == name.lower()).first()

        if feed:
            event.addresponse(u"I already have the %s feed", name)
            return

        valid = bool(feedparser.parse(url)["version"])

        if not valid:
            try:
                soup = get_html_parse_tree(url)
                for alternate in soup.findAll('link', {'rel': 'alternate',
                        'type': re.compile(r'^application/(atom|rss)\+xml$'),
                        'href': re.compile(r'.+')}):
                    newurl = urljoin(url, alternate["href"])
                    valid = bool(feedparser.parse(newurl)["version"])

                    if valid:
                        url = newurl
                        break
            except:
                pass

        if not valid:
            event.addresponse(u"Sorry, I could not add the %(name)s feed. %(url)s is not a valid feed", {
                'name': name,
                'url': url,
            })
            return

        feed = Feed(unicode(name), unicode(url), event.identity)
        event.session.save(feed)
        event.session.commit()
        event.addresponse(True)
        log.info(u"Added feed '%s' by %s/%s (%s): %s (Found %s entries)", name, event.account, event.identity, event.sender['connection'], url, len(feed.entries))

    @match(r'^(?:list\s+)?feeds$')
    def list(self, event):
        feeds = event.session.query(Feed).all()
        if feeds:
            event.addresponse(u'I know about: %s', human_join(sorted([feed.name for feed in feeds])))
        else:
            event.addresponse(u"I don't know about any feeds")

    @match(r'^remove\s+(.+?)\s+feed$')
    @authorise()
    def remove(self, event, name):
        feed = event.session.query(Feed) \
                .filter(func.lower(Feed.name) == name.lower()).first()

        if not feed:
            event.addresponse(u"I don't have the %s feed anyway", name)
        else:
            event.session.delete(feed)
            event.session.commit()
            log.info(u"Deleted feed '%s' by %s/%s (%s): %s", name, event.account, event.identity, event.sender['connection'], feed.url)
            event.addresponse(True)

class Retrieve(Processor):
    u"""latest [ <count> ] articles from <name> [ starting at <number> ]
    article ( <number> | /<pattern>/ ) from <name>"""
    feature = 'feeds'

    @match(r'^(?:latest|last)\s+(?:(\d+)\s+)?articles\s+from\s+(.+?)(?:\s+start(?:ing)?\s+(?:at\s+|from\s+)?(\d+))?$')
    def list(self, event, number, name, start):
        number = number and int(number) or 10
        start = start and int(start) or 0

        feed = event.session.query(Feed) \
                .filter(func.lower(Feed.name) == name.lower()).first()

        if not feed:
            event.addresponse(u"I don't know about the %s feed", name)
            return

        feed.update()
        if not feed.entries:
            event.addresponse(u"I can't access that feed")
            return

        articles = feed.entries[start:number+start]
        articles = [u'%s: "%s"' % (feed.entries.index(entry), html2text_file(entry.title, None).strip()) for entry in articles]
        event.addresponse(u', '.join(articles))

    @match(r'^article\s+(?:(\d+)|/(.+?)/)\s+from\s+(.+?)$')
    def article(self, event, number, pattern, name):
        feed = event.session.query(Feed) \
                .filter(func.lower(Feed.name) == name.lower()).first()

        if not feed:
            event.addresponse(u"I don't know about the %s feed", name)
            return

        feed.update()
        if not feed.entries:
            event.addresponse(u"I can't access that feed")
            return
        article = None

        if number:
            if int(number) >= len(feed.entries):
                event.addresponse(u"That's old news dude")
                return
            article = feed.entries[int(number)]

        else:
            pattern = re.compile(pattern, re.I)
            for entry in feed.entries:
                if pattern.search(entry.title):
                    article = entry
                    break

            if not article:
                event.addresponse(u'Are you making up news again?')
                return

        if 'summary' in article:
            summary = html2text_file(article.summary, None)
        else:
            if article.content[0].type in ('application/xhtml+xml', 'text/html'):
                summary = html2text_file(article.content[0].value, None)
            else:
                summary = article.content[0].value

        event.addresponse(u'"%(title)s" %(link)s : %(summary)s', {
            'title': html2text_file(article.title, None).strip(),
            'link': article.link,
            'summary': summary,
        })

# vi: set et sta sw=4 ts=4:
