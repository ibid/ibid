from datetime import datetime
from httplib import BadStatusLine
from urllib import urlencode
from urllib2 import urlopen, HTTPRedirectHandler, build_opener, HTTPError, \
                    HTTPBasicAuthHandler
import logging
import re

from pkg_resources import resource_exists, resource_stream

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option, ListOption
from ibid.db import IbidUnicode, IbidUnicodeText, Integer, DateTime, \
                    Table, Column, ForeignKey, Base, VersionedSchema
from ibid.utils.html import get_html_parse_tree

help = {'url': u'Captures URLs seen in channel to database and/or to '
               u'delicious/faves, and shortens and lengthens URLs'}

log = logging.getLogger('plugins.url')

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

class Grab(Processor):
    addressed = False
    processed = True

    username  = Option('urlgrab_username', 'Account name for URL posting')
    password  = Option('urlgrab_password', 'Password for URL Posting')
    service   = Option('urlgrab_service',
                       'URL Posting Service (delicious/faves)', 'delicious')

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

        if self.service != None and self.username != None:
            self._post_url(event, url)

    def _post_url(self, event, url=None):
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

        tags = u' '.join((event.sender['nick'], obfusc_conn, obfusc_chan,
                          event.source))

        data = {
            'url' : url.encode('utf-8'),
            'description' : title.encode('utf-8'),
            'tags' : tags.encode('utf-8'),
            'replace' : 'yes',
            'dt' : date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'extended' : event.message['raw'].encode('utf-8'),
            }

        if self.service.lower() == 'delicious':
            service = ('del.icio.us API', 'https://api.del.icio.us')
        elif self.service.lower() == 'faves':
            service = ('Faves', 'https://secure.faves.com')
        else:
            log.error(u'Unknown social bookmarking service: %s', self.service)
            return
        auth_handler = HTTPBasicAuthHandler()
        auth_handler.add_password(*service,
                                  user=self.username, passwd=self.password)
        opener = build_opener(auth_handler)

        posturl = service[1] + '/v1/posts/add?' + urlencode(data)

        try:
            resp = opener.open(posturl).read()
            if 'done' in resp:
                log.debug(u"Posted url '%s' to %s, posted in %s on %s "
                          u"by %s/%i (%s)",
                          url, self.service, event.channel, event.source,
                          event.account, event.identity,
                          event.sender['connection'])
            else:
                log.error(u"Error posting url '%s' to %s: %s",
                          url, self.service, resp)
        except HTTPError, e:
            if e.code == 401:
                log.error(u"Incorrect password for %s, couldn't post",
                          self.service)
            print e.hdrs
        except BadStatusLine, e:
            log.error(u"Error posting url '%s' to %s: %s",
                      url, self.service, unicode(e))

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

class Shorten(Processor):
    u"""shorten <url>"""
    feature = 'url'

    @match(r'^shorten\s+(\S+\.\S+)$')
    def shorten(self, event, url):
        f = urlopen('http://is.gd/api.php?%s' % urlencode({'longurl': url}))
        shortened = f.read()
        f.close()

        event.addresponse(u'That reduces to: %s', shortened)

class NullRedirect(HTTPRedirectHandler):

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None

class Lengthen(Processor):
    u"""<url>
    expand <url>"""
    feature = 'url'

    services = ListOption('services', 'List of URL prefixes of URL shortening services', (
        'http://is.gd/', 'http://tinyurl.com/', 'http://ff.im/',
        'http://shorl.com/', 'http://icanhaz.com/', 'http://url.omnia.za.net/',
        'http://snipurl.com/', 'http://tr.im/', 'http://snipr.com/',
        'http://bit.ly/', 'http://cli.gs/', 'http://zi.ma/', 'http://twurl.nl/',
        'http://xrl.us/', 'http://lnk.in/', 'http://url.ie/', 'http://ne1.net/',
        'http://turo.us/', 'http://301url.com/', 'http://u.nu/', 'http://twi.la/',
        'http://ow.ly/', 'http://su.pr/', 'http://tiny.cc/', 'http://ur1.ca/',
    ))

    def setup(self):
        self.lengthen.im_func.pattern = re.compile(r'^(?:((?:%s)\S+)|(?:lengthen\s+|expand\s+)(http://\S+))$' % '|'.join([re.escape(service) for service in self.services]), re.I|re.DOTALL)

    @handler
    def lengthen(self, event, url1, url2):
        url = url1 or url2
        opener = build_opener(NullRedirect())
        try:
            f = opener.open(url)
            f.close()
        except HTTPError, e:
            if e.code in (301, 302, 303, 307):
                event.addresponse(u'That expands to: %s', e.hdrs['location'])
                return
            raise

        event.addresponse(u"No redirect")

# vi: set et sta sw=4 ts=4:
