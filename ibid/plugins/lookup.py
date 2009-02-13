from urllib2 import urlopen
from time import time
from datetime import datetime

import feedparser
from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match
from ibid.utils import ago

class Bash(Processor):

    @match(r'^bash(?:\.org)?\s+(random|\d+)$')
    def bash(self, event, quote):
        f = urlopen('http://bash.org/?%s' % quote.lower())
        soup = BeautifulSoup(f.read(), convertEntities=BeautifulSoup.HTML_ENTITIES)
        f.close()

        quote = soup.find('p', attrs={'class': 'qt'})
        if not quote:
            event.addresponse(u"There's no such quote, but if you keep talking like that maybe there will be.")
        else:
            for line in quote.contents:
                if str(line) != '<br />':
                    event.addresponse(str(line).strip())

class LastFm(Processor):
    @match(r'^last\.?fm\s+for\s+(\S+?)\s*$')
    def listsongs(self, event, username):
        songs = feedparser.parse("http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.rss?%s" % (username, time()))
        if songs['bozo']:
            event.addresponse(u"No such user")
        else:
            event.addresponse(u', '.join(u'%s (%s ago)' % (e.title, ago(datetime.utcnow() - datetime.strptime(e.updated, '%a, %d %b %Y %H:%M:%S +0000'), 1)) for e in songs['entries']))

# vi: set et sta sw=4 ts=4:
