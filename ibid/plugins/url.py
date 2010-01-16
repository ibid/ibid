from urllib import urlencode
from urllib2 import urlopen, build_opener, HTTPError, HTTPRedirectHandler
import logging
import re

from ibid.plugins import Processor, handler, match
from ibid.config import ListOption

help = {}

log = logging.getLogger('plugins.url')

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
