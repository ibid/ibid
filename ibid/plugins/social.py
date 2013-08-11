# Copyright (c) 2008-2011, Michael Gorven, Stefano Rivera, Jonathan Hitchcock
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from urllib2 import HTTPError
from time import time
from datetime import datetime
import logging

import feedparser

from ibid.config import Option
from ibid.plugins import Processor, match
from ibid.utils import ago, decode_htmlentities, json_webservice, parse_timestamp

log = logging.getLogger('plugins.social')
features = {}

features['lastfm'] = {
    'description': u'Lists the tracks last listened to by the specified user.',
    'categories': ('lookup', 'web',),
}


class LastFm(Processor):
    usage = u'last.fm for <username>'

    features = ('lastfm',)

    @match(r'last\.?fm for {username:chunk}')
    def listsongs(self, event, username):
        songs = feedparser.parse('http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.rss?%s' % (username, time()))
        if songs['bozo']:
            event.addresponse(u'No such user')
        else:
            event.addresponse(u', '.join(u'%s (%s ago)' % (
                e.title,
                ago(event.time - parse_timestamp(e.updated))
            ) for e in songs['entries']))

features['twitter'] = {
    'description': u'Looks up messages on twitter.',
    'categories': ('lookup', 'web',),
}


class Twitter(Processor):
    usage = u"""latest tweet from <name>
    tweet <number>"""

    features = ('twitter',)

    twitter_key = Option('twitter_key', 'Your Twitter app\'s consumer key', None)
    twitter_secret = Option('twitter_secret', 'Your Twitter app\'s consumer secret', None)

    _access_token = None

    def access_token(self):
        if self._access_token is None:
            auth = ('%s:%s' % (self.twitter_key, self.twitter_secret)).encode('base64').replace('\n', '')
            auth_header = {'Authorization': 'Basic %s' % auth}
            token_response = json_webservice('https://api.twitter.com/oauth2/token',
                                             headers=auth_header, data={'grant_type':
                                                                        'client_credentials'})
            self._access_token = token_response['access_token']
        return self._access_token

    @match(r'^tweet\s+(\d+)$')
    def update(self, event, id):
        try:
            access_token = self.access_token()
            status = json_webservice('https://api.twitter.com/1.1/statuses/show.json',
                                     headers={'Authorization': 'Bearer %s' % access_token},
                                     params={'id': id})
            text = decode_htmlentities(status['text'])
            for url in status.get('entities', {}).get('urls', []):
                if url['url'] in text:
                    text = text.replace(url['url'], url['expanded_url'])

            params = {
                'screen_name': status['user']['screen_name'],
                'ago': ago(datetime.utcnow() -
                           parse_timestamp(status['created_at'])),
                'text': text
            }
            event.addresponse(u'%(screen_name)s: "%(text)s" %(ago)s ago', params)
        except HTTPError, e:
            if e.code in (401, 403):
                event.addresponse(u'That tweet is private')
            elif e.code == 404:
                event.addresponse(u'No such tweet')
            else:
                log.debug(u'Twitter raised %s', unicode(e))
                event.addresponse(u'I can only see the Fail Whale')

    @match(r'^(?:latest|last)\s+tweet\s+(?:(?:by|from|for)\s+)?@?(\S+)$')
    def latest(self, event, user):
        try:
            access_token = self.access_token()
            timeline = json_webservice('https://api.twitter.com/1.1/statuses/user_timeline.json',
                                       headers={'Authorization': 'Bearer %s' % access_token},
                                       params={'screen_name': user,
                                               'include_rts': 'false',
                                               'exclude_replies': 'true'})
            if not timeline:
                event.addresponse(u'It appears that %(user)s has never tweeted',
                                  {'user': user, })
                return
            tweet = timeline[0]
            text = decode_htmlentities(tweet['text'])
            for url in tweet.get('entities', {}).get('urls', []):
                if url['url'] in text:
                    text = text.replace(url['url'], url['expanded_url'])

            params = {
                'text': text,
                'ago': ago(datetime.utcnow() -
                           parse_timestamp(tweet['created_at'])),
                'url': 'https://twitter.com/%s/status/%s' % (user, tweet['id']),
            }
            event.addresponse(u'"%(text)s" %(ago)s ago, %(url)s', params)
        except HTTPError, e:
            if e.code in (401, 403):
                event.addresponse(u"Sorry, %s's feed is private", user)
            elif e.code == 404:
                event.addresponse(u'No such user')
            else:
                log.debug(u'Twitter raised %s', unicode(e))
                event.addresponse(u'I can only see the Fail Whale')

    @match(r'^https?://(?:www\.)?twitter\.com/(?:#!/)?[^/ ]+/statuse?s?/(\d+)$',
           simple=False)
    def twitter(self, event, id):
        self.update(event, id)

# vi: set et sta sw=4 ts=4:
