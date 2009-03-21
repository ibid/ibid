from datetime import datetime
from urllib import urlencode
from urllib2 import urlopen, HTTPRedirectHandler, build_opener, HTTPError, HTTPBasicAuthHandler, install_opener
from BeautifulSoup import BeautifulSoup
import htmlentitydefs
import logging, pydb
import re

from sqlalchemy import Column, Integer, Unicode, DateTime, UnicodeText, ForeignKey, Table

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option
from ibid.models import Base

help = {'url': u'Captures URLs seen in channel to database and/or to delicious, and shortens and lengthens URLs'}

log            = logging.getLogger('plugins.url')
at_re          = re.compile('@\S+?\.')
exclamation_re = re.compile('!')

class URL(Base):
    __table__ = Table('urls', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('url', UnicodeText, nullable=False),
    Column('channel', Unicode(32), nullable=False),
    Column('identity_id', Integer, ForeignKey('identities.id'), nullable=False),
    Column('time', DateTime, nullable=False),
    useexisting=True)

    def __init__(self, url, channel, identity_id):
        self.url = url
        self.channel = channel
        self.identity_id = identity_id
        self.time = datetime.now()

class Delicious(Processor):

    def add_post(self,username,password,url=None):
        "Posts a URL to delicious.com"

        date  = datetime.now()
        title = self._get_title(url)
        pydb.debugger()

        connection_body = exclamation_re.split(event.sender['connection'])
        if len(connection_body) == 1:
            connection_body.append(event.sender['connection'])
        obfusc = at_re.sub('^', connection_body[1])
        tags =  event.sender['nick'] + " " + obfusc + " " + event.channel

        data = {
            'url' : url,
            'description' : title,
            'tags' : tags,
            'replace' : u"yes",
            'dt' : date,
            }

        self._set_auth(username,password)
        posturl = "https://api.del.icio.us/v1/posts/add?"+urlencode(data)
        resp = urlopen(posturl).read()
        if 'done' in resp:
            log.info(u"Successfully posted url %s posted in channel %s by nick %s at time %s", url, channel, nick, date)
        else:
            log.error(u"Error posting url %s: %s", url, response)

    def _get_title(self,url):
        "Gets the title of a page"
        try:
            soup = BeautifulSoup(urlopen(url))
            title = soup.title.string
             ## doing a de_entity results in > 'ascii' codec can't encode character u'\xab' etc.
             ## leaving this code here in case someone works out how to get urllib2 to post unicode?
             #final_title = self._de_entity(title)
            return title
        except Exception, e:
            log.error(u"Error determining the title for url %s: %s", url, e.message)
            return url

    def _set_auth(self,username,password):
        "Provides HTTP authentication on username and password"
        auth_handler = HTTPBasicAuthHandler()
        auth_handler.add_password('del.icio.us API', 'https://api.del.icio.us', username, password)
        opener = build_opener(auth_handler)
        install_opener(opener)

    def _de_entity(self,text):
        "Remove HTML entities, and replace with their characters"
        replace = lambda match: unichr(int(match.group(1)))
        text = re.sub("&#(\d+);", replace, text)

        replace = lambda match: unichr(htmlentitydefs.name2codepoint[match.group(1)])
        text = re.sub("&(\w+);", replace, text)
        return text

class Grab(Processor):

    addressed = False
    processed = True
    username   = Option('username', 'delicious account name')
    password   = Option('password', 'delicious account password')
    delicious = Delicious()

    @match(r'((?:\S+://|(?:www|ftp)\.)\S+|\S+\.(?:com|org|net|za)\S*)')
    def grab(self, event, url):
        if url.find('://') == -1:
            if url.lower().startswith('ftp'):
                url = 'ftp://%s' % url
            else:
                url = 'http://%s' % url

        session = ibid.databases.ibid()
        u = URL(url, event.channel, event.identity)
        session.save_or_update(u)
        session.flush()
        session.close()

        if self.username != "":
            self.delicious.add_post(self.username, self.password, url)

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
