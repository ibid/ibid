# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.
#
# The youtube Processor uses code from youtube-dl:
#   Copyright (c) 2006-2008 Ricardo Garcia Gonzalez
#   Released under MIT Licence

from urllib import urlencode
from urllib2 import urlopen, build_opener, HTTPError, HTTPRedirectHandler, HTTPCookieProcessor
import logging
import re

from ibid.plugins import Processor, handler, match
from ibid.config import ListOption

default_user_agent = 'Mozilla/5.0'
default_referer = "http://ibid.omnia.za.net/"

features = {}

log = logging.getLogger('plugins.url')

features['tinyurl'] = {
    'description': u'Shorten and lengthen URLs',
    'categories': ('lookup', 'web',),
}
class Shorten(Processor):
    usage = u'shorten <url>'
    features = ('tinyurl',)

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
    usage = u"""<url>
    expand <url>"""
    features = ('tinyurl',)

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

features['youtube'] = {
    'description': u'Determine the title and a download URL for a Youtube Video',
    'categories': ('lookup', 'web',),
}
class Youtube(Processor):
    usage = u'<Youtube URL>'

    features = ('youtube',)

    @match(r'^(?:youtube(?:\.com)?\s+)?'
        r'(?:http://)?(?:\w+\.)?youtube\.com/'
        r'(?:v/|(?:watch(?:\.php)?)?\?(?:.+&)?v=)'
        r'([0-9A-Za-z_-]+)(?(1)[&/].*)?$')
    def youtube(self, event, id):
        url = 'http://www.youtube.com/watch?v=' + id
        opener = build_opener(HTTPCookieProcessor())
        opener.addheaders = [('User-Agent', default_user_agent)]
        video_webpage = opener.open(url).read()
        title = re.search(r'<title>\s*YouTube\s+-\s+([^<]*)</title>',
                video_webpage, re.M | re.I | re.DOTALL).group(1).strip()
        t = re.search(r', "t": "([^"]+)"', video_webpage).group(1)
        event.addresponse(u'%(title)s: %(url)s', {
            'title': title,
            'url': 'http://www.youtube.com/get_video?video_id=%s&t=%s' % (id, t),
        })

# vi: set et sta sw=4 ts=4:
