from datetime import datetime
from urllib2 import urlopen, HTTPRedirectHandler, build_opener, HTTPError
import re

from sqlalchemy import Column, Integer, Unicode, DateTime, UnicodeText, ForeignKey, Table

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option
from ibid.models import Base

help = {'url': 'Captures URLs seen in channel, and shortens and lengthens URLs'}

class URL(Base):
    __table__ = Table('urls', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('url', UnicodeText, nullable=False),
    Column('channel', Unicode(32), nullable=False),
    Column('identity', Integer, ForeignKey('identities.id'), nullable=False),
    Column('time', DateTime, nullable=False),
    useexisting=True)

    def __init__(self, url, channel, identity):
        self.url = url
        self.channel = channel
        self.identity = identity
        self.time = datetime.now()

class Grab(Processor):

    addressed = False
    processed = True

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

class Shorten(Processor):
    """shorten <url>"""
    feature = 'url'

    @match(r'^shorten\s+(\S+\.\S+)$')
    def shorten(self, event, url):
        f = urlopen('http://is.gd/api.php?longurl=%s' % url)
        shortened = f.read()
        f.close()

        event.addresponse(shortened)

class NullRedirect(HTTPRedirectHandler):

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None

class Lengthen(Processor):
    """<url>"""
    feature = 'url'

    services = Option('services', 'List of URL prefixes of URL shortening services', ('http://is.gd/', 'http://tinyurl.com/', 'http://ff.im/', 'http://shorl.com/', 'http://icanhaz.com/', 'http://url.omnia.za.net/', 'http://snipurl.com/', 'http://tr.im/', 'http://snipr.com/'))

    def setup(self):
        self.lengthen.im_func.pattern = re.compile(r'^((?:%s)\S+)$' % '|'.join([re.escape(service) for service in self.services]), re.I)
    
    @handler
    def lengthen(self, event, url):
        opener = build_opener(NullRedirect())
        try:
            f = opener.open(url)
        except HTTPError, e:
            if e.code in (301, 302, 303, 307):
                event.addresponse(e.hdrs['location'])
                return

        f.close()
        event.addresponse(u"No redirect")
                
# vi: set et sta sw=4 ts=4:
