import re
from datetime import datetime
import logging
from urlparse import urljoin

from sqlalchemy import Column, Integer, Unicode, DateTime, UnicodeText, ForeignKey, Table
from sqlalchemy.sql import func
import feedparser
from html2text import html2text_file

from ibid.config import IntOption
from ibid.plugins import Processor, match, authorise, run_every
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
    Column('source', Unicode(32), index=True),
    Column('target', Unicode(32), index=True),
    useexisting=True)

    class FeedSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.name, unique=True)
            self.add_index(self.table.c.identity_id)
        def upgrade_2_to_3(self):
            from sqlalchemy import Column, Unicode
            self.add_column(Column('source', Unicode(32), index=True))
            self.add_column(Column('target', Unicode(32), index=True))

    __table__.versioned_schema = FeedSchema(__table__, 3)

    feed = None
    entries = None

    def __init__(self, name, url, identity_id, source=None, target=None):
        self.name = name
        self.url = url
        self.identity_id = identity_id
        self.source = source
        self.target = target
        self.time = datetime.utcnow()
        self.update()

    def update(self):
        feedfile = cacheable_download(self.url, "feeds/%s-%i.xml" % (re.sub(r'\W+', '_', self.name), self.identity_id))
        self.feed = feedparser.parse(feedfile)
        self.entries = self.feed['entries']

    def __unicode__(self):
        if self.source is not None and self.target is not None:
            return u'%s (Notify %s on %s)' % (
                    self.name, self.target, self.source)
        else:
            return self.name

class Manage(Processor):
    u"""
    add feed <url> as <name>
    remove <name> feed
    list feeds
    poll <name> feed notify <channel> on <source>
    stop polling <name> feed
    """
    feature = 'feeds'

    permission = u'feeds'

    @match(r'^add\s+feed\s+(.+?)\s+as\s+(.+?)$')
    @authorise
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
            event.addresponse(u'I know about: %s', human_join(sorted([
                unicode(feed) for feed in feeds])))
        else:
            event.addresponse(u"I don't know about any feeds")

    @match(r'^remove\s+(.+?)\s+feed$')
    @authorise
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

    @match(r'^(?:stop|don\'t)\s+poll(?:ing)?\s(.+)\s+feed$')
    @authorise
    def no_poll(self, event, name):
        feed = event.session.query(Feed) \
                .filter(func.lower(Feed.name) == name.lower()).first()

        if not feed:
            event.addresponse(u"I don't have the %s feed anyway", name)
        else:
            feed.source = None
            feed.target = None
            event.session.commit()
            log.info(u"Disabled polling on feed '%s' by %s/%s (%s)",
                    name, event.account, event.identity,
                    event.sender['connection'])
            event.addresponse(True)

    @match(r'^poll\s(.+)\s+feed\s+(?:to|notify)\s+(.+)\s+on\s+(.+)$')
    @authorise
    def enable_poll(self, event, name, target, source):
        feed = event.session.query(Feed) \
                .filter(func.lower(Feed.name) == name.lower()).first()

        if not feed:
            event.addresponse(u"I don't have the %s feed anyway", name)
        else:
            feed.source = source
            feed.target = target
            event.session.commit()
            log.info(u"Enabled polling on feed '%s' to %s on %s by %s/%s (%s)",
                    name, target, source, event.account, event.identity,
                    event.sender['connection'])
            event.addresponse(True)

class Retrieve(Processor):
    u"""latest [ <count> ] articles from <name> [ starting at <number> ]
    article ( <number> | /<pattern>/ ) from <name>"""
    feature = 'feeds'

    interval = IntOption('interval', 'Feed Poll interval (in seconds)', 300)

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

    last_seen = {}
    @run_every(config_key='interval')
    def poll(self, event):
        log.debug(u'Polling feeds')
        feeds = event.session.query(Feed) \
                .filter(Feed.source != None) \
                .filter(Feed.target != None).all()

        for feed in feeds:
            feed.update()
            if not feed.entries:
                log.warning(u'Error polling feed %s', feed.name)
                continue

            if feed.name not in self.last_seen:
                seen = {}
                for entry in feed.entries:
                    id = entry.get('id', entry.title)
                    seen[id] = entry.updated_parsed
                self.last_seen[feed.name] = seen
                continue

            old_seen = self.last_seen[feed.name]
            seen = {}
            for entry in reversed(feed.entries):
                id = entry.get('id', entry.title)
                seen[id] = entry.updated_parsed
                if entry.updated_parsed != old_seen.get(id):
                    event.addresponse(
                        u"%(status)s item in %(feed)s: %(title)s", {
                            'status': id in old_seen and u'Updated' or u'New',
                            'feed': feed.name,
                            'title': entry.title,
                        },
                        source=feed.source, target=feed.target, adress=False)
            self.last_seen[feed.name] = seen

# vi: set et sta sw=4 ts=4:
