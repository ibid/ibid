# Copyright (c) 2009-2010, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import logging
from urllib2 import HTTPError

from ibid.config import DictOption, IntOption
from ibid.plugins import Processor, match, periodic
from ibid.utils import human_join
from ibid.utils.html import get_html_parse_tree

log = logging.getLogger('plugins.icecast')

features = {'icecast': {
    'description': u'Follows an ICECast stream',
    'categories': ('monitor',),
}}
class ICECast(Processor):
    u"""
    what's playing [on <stream>]?
    """
    feature = ('icecast',)

    interval = IntOption('interval',
            'Interval between checking for song changes', 60)
    streams = DictOption('streams',
            'Dictionary of Stream names to base URL (include trailing /)', {})

    last_checked = None
    last_songs = {}

    def scrape_status(self, stream):
        tree = get_html_parse_tree(self.streams[stream]['url'] + 'status.xsl',
                treetype='etree')
        main_table = tree.findall('.//table')[2]
        status = {}
        for row in main_table.findall('.//tr'):
            key, value = [x.text for x in row.findall('td')]
            status[key[:-1]] = value
        return status

    @match(r'^what(?:\'|\s+i)s\s+playing(?:\s+on\s+(.+))?$')
    def playing(self, event, stream):
        if not event.get('addressed', False):
            return

        if len(self.streams) == 0:
            event.addresponse(u"Sorry, I don't know about any streams")
            return
        elif stream is None and len(self.streams) == 1:
            stream = self.streams.keys()[0]
        elif stream is not None and stream not in self.streams:
            for name in self.streams.iterkeys():
                if name.lower() == stream.lower():
                    stream = name
                    break
            else:
                stream = None
        if stream is None:
            event.addresponse(
                    u'Sorry, I only know about the following streams, '
                    u'please choose one: %s',
                    human_join(self.streams.keys()))
            return

        try:
            status = self.scrape_status(stream)
            event.addresponse(u'Currently Playing on %(stream)s: '
                u'%(song)s - %(description)s (Listeners: %(listeners)s)', {
                    'stream': stream,
                    'song': status['Current Song'],
                    'description': status['Stream Description'],
                    'listeners': status['Current Listeners'],
                })
        except HTTPError:
            event.addresponse(u'The stream must be down, back to the MP3 collection for you')

    @periodic(config_key='interval')
    def check(self, event):
        for name, stream in self.streams.iteritems():
            if 'source' in stream and 'channel' in stream:
                log.debug(u'Probing %s', name)
                status = self.scrape_status(name)
                if self.last_songs.get(name, '') != status['Current Song']:
                    self.last_songs[name] = status['Current Song']
                    event.addresponse(u'Now Playing on %(stream)s: '
                        u'%(song)s - %(description)s '
                        u'(Listeners: %(listeners)s)', {
                            'stream': name,
                            'song': status['Current Song'],
                            'description': status['Stream Description'],
                            'listeners': status['Current Listeners'],
                        }, source=stream['source'],
                        target=stream['channel'],
                        topic=(stream.get('topic', 'False').lower()
                            in ('yes', 'true')),
                        address=False,
                    )

# vi: set et sta sw=4 ts=4:
