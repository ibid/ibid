from datetime import datetime
from urllib import urlencode
from urllib2 import urlopen, HTTPRedirectHandler, build_opener, HTTPError, HTTPBasicAuthHandler, install_opener
import logging
import re

from sqlalchemy import Column, Integer, Unicode, DateTime, UnicodeText, ForeignKey, Table

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option
from ibid.models import Base, VersionedSchema
from ibid.utils  import get_html_parse_tree

help = {'url': u'Captures URLs seen in channel to database and/or to delicious, and shortens and lengthens URLs'}

log = logging.getLogger('plugins.url')

class URL(Base):
    __table__ = Table('urls', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('url', UnicodeText, nullable=False),
    Column('channel', Unicode(32), nullable=False),
    Column('identity_id', Integer, ForeignKey('identities.id'), nullable=False),
    Column('time', DateTime, nullable=False),
    useexisting=True)

    __table__.versioned_schema = VersionedSchema(__table__, 1)

    def __init__(self, url, channel, identity_id):
        self.url = url
        self.channel = channel
        self.identity_id = identity_id
        self.time = datetime.now()

class Delicious():

    at_re  = re.compile(r'@\S+?\.')
    ip_re  = re.compile(r'\.IP$|unaffiliated')
    con_re = re.compile(r'!n=|!')

    def add_post(self, username, password, event, url=None):
        "Posts a URL to delicious.com"

        date  = datetime.now()
        title = self._get_title(url)

        connection_body = self.con_re.split(event.sender['connection'])
        if len(connection_body) == 1:
            connection_body.append(event.sender['connection'])

        if self.ip_re.search(connection_body[1]) != None:
            connection_body[1] = ''

        if ibid.sources[event.source].type == 'jabber':
            obfusc_conn = ''
            obfusc_chan = event.channel.replace('@', '^')
        else:
            obfusc_conn = self.at_re.sub('^', connection_body[1])
            obfusc_chan = self.at_re.sub('^', event.channel)


        tags = u' '.join((event.sender['nick'], obfusc_conn, obfusc_chan, event.source))

        data = {
            'url' : url,
            'description' : title,
            'tags' : tags,
            'replace' : u'yes',
            'dt' : date,
            'extended' : event.message['raw'],
            }

        self._set_auth(username,password)
        posturl = 'https://api.del.icio.us/v1/posts/add?' + urlencode(data, 'utf-8')
        resp = urlopen(posturl).read()
        if 'done' in resp:
            log.info(u"Successfully posted url %s to delicious, posted in channel %s by nick %s at time %s",
                     url, event.channel, event.sender['nick'], date)
        else:
            log.error(u"Error posting url %s to delicious: %s", url, resp)

    def _get_title(self, url):
        "Gets the title of a page"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            etree = get_html_parse_tree(url, None, headers, 'etree')
            title = etree.findtext('head/title')
            return title
        except Exception:
            log.exception(u"Delicious logic - error determining the title for url %s", url)
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

    @match(r'((?:\S+://|(?:www|ftp)\.)\S+|\S+\.(?:com|org|net|za)\S*)')
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
    u"""<url>"""
    feature = 'url'

    services = Option('services', 'List of URL prefixes of URL shortening services', (
        'http://is.gd/', 'http://tinyurl.com/', 'http://ff.im/',
        'http://shorl.com/', 'http://icanhaz.com/', 'http://url.omnia.za.net/',
        'http://snipurl.com/', 'http://tr.im/', 'http://snipr.com/'
    ))

    def setup(self):
        self.lengthen.im_func.pattern = re.compile(r'^((?:%s)\S+)$' % '|'.join([re.escape(service) for service in self.services]), re.I)

    @handler
    def lengthen(self, event, url):
        opener = build_opener(NullRedirect())
        try:
            f = opener.open(url)
        except HTTPError, e:
            if e.code in (301, 302, 303, 307):
                event.addresponse(u'That expands to: %s', e.hdrs['location'])
                return

        f.close()
        event.addresponse(u"No redirect")

# vi: set et sta sw=4 ts=4:
