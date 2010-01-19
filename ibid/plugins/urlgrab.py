# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera, Jonathan Groll
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from datetime import datetime
from httplib import BadStatusLine
from urllib import urlencode
from urllib2 import urlopen, build_opener, HTTPError, HTTPBasicAuthHandler, \
        install_opener
import logging
import re

from pkg_resources import resource_exists, resource_stream

import ibid
from ibid.plugins import Processor, handler
from ibid.config import Option
from ibid.db import IbidUnicode, IbidUnicodeText, Integer, DateTime, \
                    Table, Column, ForeignKey, Base, VersionedSchema
from ibid.utils.html import get_html_parse_tree

help = {}

log = logging.getLogger('plugins.urlgrab')

help['url'] = u'Captures URLs seen in channel to database and/or to delicious, and shortens and lengthens URLs'

class URL(Base):
    __table__ = Table('urls', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('url', IbidUnicodeText, nullable=False),
    Column('channel', IbidUnicode(32, case_insensitive=True), nullable=False),
    Column('identity_id', Integer, ForeignKey('identities.id'),
           nullable=False, index=True),
    Column('time', DateTime, nullable=False),
    useexisting=True)

    class URLSchema(VersionedSchema):
        def upgrade_1_to_2(self):
            self.add_index(self.table.c.identity_id)
        def upgrade_2_to_3(self):
            self.alter_column(Column('url', IbidUnicodeText, nullable=False))
            self.alter_column(Column('channel',
                                     IbidUnicode(32, case_insensitive=True),
                                     nullable=False), force_rebuild=True)

    __table__.versioned_schema = URLSchema(__table__, 3)

    def __init__(self, url, channel, identity_id):
        self.url = url
        self.channel = channel
        self.identity_id = identity_id
        self.time = datetime.utcnow()

class Delicious(object):
    def add_post(self, username, password, event, url=None):
        "Posts a URL to delicious.com"

        date = datetime.utcnow()
        try:
            title = self._get_title(url)
        except HTTPError:
            return

        con_re = re.compile(r'!n=|!')
        connection_body = con_re.split(event.sender['connection'])
        if len(connection_body) == 1:
            connection_body.append(event.sender['connection'])

        ip_re  = re.compile(r'\.IP$|unaffiliated')
        if ip_re.search(connection_body[1]) != None:
            connection_body[1] = ''

        if ibid.sources[event.source].type == 'jabber':
            obfusc_conn = ''
            obfusc_chan = event.channel.replace('@', '^')
        else:
            at_re  = re.compile(r'@\S+?\.')
            obfusc_conn = at_re.sub('^', connection_body[1])
            obfusc_chan = at_re.sub('^', event.channel)

        tags = u' '.join((event.sender['nick'], obfusc_conn, obfusc_chan, event.source))

        data = {
            'url' : url.encode('utf-8'),
            'description' : title.encode('utf-8'),
            'tags' : tags.encode('utf-8'),
            'replace' : 'yes',
            'dt' : date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'extended' : event.message['raw'].encode('utf-8'),
            }

        self._set_auth(username, password)
        posturl = 'https://api.del.icio.us/v1/posts/add?' + urlencode(data)

        try:
            resp = urlopen(posturl).read()
            if 'done' in resp:
                log.debug(u"Posted url '%s' to delicious, posted in %s on %s by %s/%i (%s)",
                         url, event.channel, event.source, event.account, event.identity, event.sender['connection'])
            else:
                log.error(u"Error posting url '%s' to delicious: %s", url, resp)
        except BadStatusLine, e:
            log.error(u"Error posting url '%s' to delicious: %s", url, unicode(e))

    def _get_title(self, url):
        "Gets the title of a page"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            etree = get_html_parse_tree(url, None, headers, 'etree')
            title = etree.findtext('head/title')
            return title or url
        except HTTPError, e:
            raise
        except Exception, e:
            log.debug(u"Error determining title for %s: %s", url, unicode(e))
            return url

    def _set_auth(self, username, password):
        "Provides HTTP authentication on username and password"
        auth_handler = HTTPBasicAuthHandler()
        auth_handler.add_password('del.icio.us API', 'https://api.del.icio.us', username, password)
        opener = build_opener(auth_handler)
        install_opener(opener)

class Grab(Processor):
    addressed = False
    processed = True

    username  = Option('delicious_username', 'delicious account name')
    password  = Option('delicious_password', 'delicious account password')
    delicious = Delicious()

    def setup(self):
        if resource_exists(__name__, '../data/tlds-alpha-by-domain.txt'):
            tlds = [tld.strip().lower() for tld
                    in resource_stream(__name__, '../data/tlds-alpha-by-domain.txt')
                        .readlines()
                    if not tld.startswith('#')
            ]

        else:
            log.warning(u"Couldn't open TLD list, falling back to minimal default")
            tlds = 'com.org.net.za'.split('.')

        self.grab.im_func.pattern = re.compile((
            r'(?:[^@./]\b(?!\.)|\A)('       # Match a boundary, but not on an e-mail address
            r'(?:\w+://|(?:www|ftp)\.)\S+?' # Match an explicit URL or guess by www.
            r'|[^@\s:/]+\.(?:%s)(?:/\S*?)?' # Guess at the URL based on TLD
            r')[\[>)\]"\'.,;:]*(?:\s|\Z)'   # End boundary
        ) % '|'.join(tlds), re.I | re.DOTALL)

    @handler
    def grab(self, event, url):
        if url.find('://') == -1:
            if url.lower().startswith('ftp'):
                url = 'ftp://%s' % url
            else:
                url = 'http://%s' % url

        u = URL(url, event.channel, event.identity)
        event.session.save_or_update(u)

        if self.username != None:
            self.delicious.add_post(self.username, self.password, event, url)


# vi: set et sta sw=4 ts=4:
