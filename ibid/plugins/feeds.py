# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from datetime import datetime
import logging
import re
from threading import Lock
from urllib2 import URLError
from urlparse import urljoin

import feedparser
from html2text import html2text_file

from ibid.config import IntOption, FloatOption
from ibid.db import IbidUnicode, IbidUnicodeText, Integer, DateTime, \
                    Table, Column, ForeignKey, Base, VersionedSchema
from ibid.plugins import Processor, match, authorise, periodic
from ibid.utils import cacheable_download, human_join
from ibid.utils.html import get_html_parse_tree

features = {'feeds': {
    'description': u'Displays articles from RSS and Atom feeds',
    'categories': ('lookup', 'web',),
}}

log = logging.getLogger('plugins.feeds')

class Feed(Base):
    __table__ = Table('feeds', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', IbidUnicode(32, case_insensitive=True),
           unique=True, nullable=False, index=True),
    Column('url', IbidUnicodeText, nullable=False),
    Column('identity_id', Integer, ForeignKey('identities.id'),
           nullable=False, index=True),
    Column('time', DateTime, nullable=False),
    Column('source', IbidUnicode(32, case_insensitive=True), index=True),
    Column('target', IbidUnicode(32, case_insensitive=True), index=True),
    useexisting=True)

    class FeedSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.name)
            self.add_index(self.table.c.identity_id)
        def upgrade_2_to_3(self):
            from ibid.db import IbidUnicode, Column
            self.add_column(Column('source', IbidUnicode(32), index=True))
            self.add_column(Column('target', IbidUnicode(32), index=True))
        def upgrade_3_to_4(self):
            self.drop_index(self.table.c.name)
            self.drop_index(self.table.c.source)
            self.drop_index(self.table.c.target)
            self.alter_column(Column('name',
                                     IbidUnicode(32, case_insensitive=True),
                                     unique=True, nullable=False, index=True),
                              force_rebuild=True)
            self.alter_column(Column('url', IbidUnicodeText, nullable=False),
                              force_rebuild=True)
            self.alter_column(Column('source',
                                     IbidUnicode(32, case_insensitive=True),
                                     index=True), force_rebuild=True)
            self.alter_column(Column('target',
                                     IbidUnicode(32, case_insensitive=True),
                                     index=True), force_rebuild=True)
            self.add_index(self.table.c.name)
            self.add_index(self.table.c.source)
            self.add_index(self.table.c.target)

    __table__.versioned_schema = FeedSchema(__table__, 4)

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

    def update(self, max_age=None):
        headers = {}
        if max_age:
            headers['Cache-Control'] = 'max-age=%i' % max_age

        feedfile = cacheable_download(self.url, "feeds/%s-%i.xml" % (
                re.sub(r'\W+', '_', self.name), self.identity_id), headers)
        self.feed = feedparser.parse(feedfile)
        self.entries = self.feed['entries']

    def __unicode__(self):
        if self.source is not None and self.target is not None:
            string = u'%s (notify %s on %s)' % (
                    self.name, self.target, self.source)
            if self.name in broken_feeds:
                string += ' [broken]'
            return string
        else:
            return self.name

class Manage(Processor):
    usage = u"""
    add feed <url> as <name>
    remove <name> feed
    list feeds
    poll <name> feed notify <channel> on <source>
    stop polling <name> feed
    """
    features = ('feeds',)

    permission = u'feeds'

    @match(r'^add\s+feed\s+(.+?)\s+as\s+(.+?)$')
    @authorise()
    def add(self, event, url, name):
        feed = event.session.query(Feed).filter_by(name=name).first()

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
            event.addresponse(u'Sorry, I could not add the %(name)s feed. '
                u'%(url)s is not a valid feed', {
                    'name': name,
                    'url': url,
                })
            return

        feed = Feed(unicode(name), unicode(url), event.identity)
        event.session.save(feed)
        event.session.commit()
        event.addresponse(True)
        log.info(u"Added feed '%s' by %s/%s (%s): %s (Found %s entries)",
                name, event.account, event.identity,
                event.sender['connection'], url, len(feed.entries))

    @match(r'^(?:list\s+)?feeds$')
    def list(self, event):
        feeds = event.session.query(Feed).all()
        if feeds:
            event.addresponse(u'I know about: %s', human_join(sorted([
                unicode(feed) for feed in feeds])))
        else:
            event.addresponse(u"I don't know about any feeds")

    @match(r'^remove\s+(.+?)\s+feed$')
    @authorise()
    def remove(self, event, name):
        feed = event.session.query(Feed).filter_by(name=name).first()

        if not feed:
            event.addresponse(u"I don't have the %s feed anyway", name)
        else:
            event.session.delete(feed)
            event.session.commit()
            log.info(u"Deleted feed '%s' by %s/%s (%s): %s", name,
                    event.account, event.identity,
                    event.sender['connection'], feed.url)
            event.addresponse(True)

    @match(r'^(?:stop|don\'t)\s+poll(?:ing)?\s(.+)\s+feed$')
    @authorise()
    def no_poll(self, event, name):
        feed = event.session.query(Feed).filter_by(name=name).first()

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
    @authorise(fallthrough=False)
    def enable_poll(self, event, name, target, source):
        feed = event.session.query(Feed).filter_by(name=name).first()

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

    @match(r'retry (?:broken )?feeds')
    @authorise(fallthrough=False)
    def unwedge(self, event):
        broken_lock.acquire()
        broken_feeds.clear()
        broken_lock.release()
        event.addresponse("I'll check them out next time I update my feeds")

# broken_feeds[name] = (last_exception, fetch_interval, time_since_fetch)
# fetches_skipped is the number of intervals in which we *haven't* tried to
# fetch this feed. Feeds are removed whenever they are successfully loaded.
broken_feeds = {}
broken_lock = Lock()

class Retrieve(Processor):
    usage = u"""latest [ <count> ] articles from <name> [ starting at <number> ]
    article ( <number> | /<pattern>/ ) from <name>"""
    features = ('feeds',)

    interval = IntOption('interval', 'Feed Poll interval (in seconds)', 300)
    max_interval = IntOption('max_interval',
        'Maximum feed poll interval for broken feeds (in seconds)', 86400)
    backoff_ratio = FloatOption('backoff',
        'The slowdown ratio to back off from broken feeds', 2.0)


    @match(r'^(?:latest|last)\s+(?:(\d+)\s+)?articles\s+from\s+(.+?)'
           r'(?:\s+start(?:ing)?\s+(?:at\s+|from\s+)?(\d+))?$')
    def list(self, event, number, name, start):
        number = number and int(number) or 10
        start = start and int(start) or 0

        feed = event.session.query(Feed).filter_by(name=name).first()

        if not feed:
            event.addresponse(u"I don't know about the %s feed", name)
            return

        feed.update()
        if not feed.entries:
            event.addresponse(u"I can't access that feed")
            return

        articles = feed.entries[start:number+start]
        articles = [u'%s: "%s"' % (feed.entries.index(entry) + 1,
                                   html2text_file(entry.title, None).strip())
                    for entry in articles]
        event.addresponse(u', '.join(articles))

    @match(r'^article\s+(?:(\d+)|/(.+?)/)\s+from\s+(.+?)$')
    def article(self, event, number, pattern, name):
        feed = event.session.query(Feed).filter_by(name=name).first()

        if not feed:
            event.addresponse(u"I don't know about the %s feed", name)
            return

        feed.update()
        if not feed.entries:
            event.addresponse(u"I can't access that feed")
            return
        article = None

        if number:
            if int(number) > len(feed.entries) or 1 > int(number):
                event.addresponse(u"That's old news dude")
                return
            article = feed.entries[int(number) - 1]

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
            if article.content[0].type in \
                    ('application/xhtml+xml', 'text/html'):
                summary = html2text_file(article.content[0].value, None)
            else:
                summary = article.content[0].value

        event.addresponse(u'"%(title)s"%(link)s : %(summary)s', {
            'title': html2text_file(article.title, None).strip(),
            'link': get_link(article),
            'summary': summary,
        })

    last_seen = {}
    @periodic(config_key='interval')
    def poll(self, event):
        feeds = event.session.query(Feed) \
                .filter(Feed.source != None) \
                .filter(Feed.target != None).all()

        for feed in feeds:
            try:
                broken_lock.acquire()
                if feed.name in broken_feeds:
                    last_exc, interval, time_since_fetch = broken_feeds[feed.name]
                    time_since_fetch += self.interval
                    if time_since_fetch < interval:
                        broken_feeds[feed.name] = \
                                last_exc, interval, time_since_fetch
                        continue
                else:
                    last_exc = None
                    interval = time_since_fetch = self.interval

                try:
                    feed.update(max_age=time_since_fetch)
                except Exception, e:
                    if type(e) != type(last_exc):
                        if isinstance(e, URLError):
                            log.warning(u'Exception "%s" occured while polling '
                                        u'feed %s from %s', e, feed, feed.url)
                        else:
                            log.exception(u'Exception "%s" occured while polling '
                                          u'feed %s from %s', e, feed, feed.url)
                    broken_feeds[feed.name] = e, self.backoff(interval), 0
                    continue
                else:
                    if feed.name in broken_feeds:
                        del broken_feeds[feed.name]
            finally:
                broken_lock.release()

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
                        u"%(status)s item in %(feed)s: %(title)s%(link)s", {
                            'status': id in old_seen and u'Updated' or u'New',
                            'feed': feed.name,
                            'title': entry.title,
                            'link': get_link(entry),
                        },
                        source=feed.source, target=feed.target, adress=False)
            self.last_seen[feed.name] = seen

    def backoff(self, interval):
        return min(self.max_interval, interval*self.backoff_ratio)

def get_link(entry):
    if hasattr(entry, 'link'):
        return u' ' + entry.link
    else:
        return u''

# vi: set et sta sw=4 ts=4:
