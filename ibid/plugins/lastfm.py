import re
from datetime import datetime

import feedparser
import time
import ibid
from ibid.plugins import Processor, match, authorise

class LastFm(Processor):
    @match(r'^last\.?fm\s+for\s+(\S+?)\s*$')
    def listsongs(self, event, username):
        songs = feedparser.parse("http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.rss?%s" % (username, time.time()))
        if songs['bozo']:
            event.addresponse(u"No such user")
        else:
            event.addresponse(", ".join(["%s (%s)" % (e.title, e.updated) for e in songs['entries']]))

# vi: set et sta sw=4 ts=4:
