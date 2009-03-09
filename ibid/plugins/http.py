from httplib import HTTPConnection, HTTPSConnection
from urllib import getproxies_environment
from urlparse import urlparse
import re

from ibid.plugins import Processor, match
from ibid.config import IntOption

help = {}

title = re.compile(r'<title>(.*)<\/title>', re.I+re.S)

help['get'] = u'Retrieves a URL and returns the HTTP status and optionally the HTML title.'
class HTTP(Processor):
    u"""(get|head) <url>"""
    feature = 'get'

    max_size = IntOption('max_size', 'Only request this many bytes', 500)

    @match(r'^(get|head)\s+(.+)$')
    def handler(self, event, action, url):
        if not url.lower().startswith("http://") and not url.lower().startswith("https://"):
            url = "http://" + url
        if url.count("/") < 3:
            url += "/"

        action = action.upper()

        scheme, host = urlparse(url)[:2]
        scheme = scheme.lower()
        proxies = getproxies_environment()
        if scheme in proxies:
            scheme, host = urlparse(proxies[scheme])[:2]
            scheme = scheme.lower()

        if scheme == "https":
            conn = HTTPSConnection(host)
        else:
            conn = HTTPConnection(host)

        headers={}
        if action == 'GET':
            headers['Range'] = 'bytes=0-%s' % self.max_size
        conn.request(action.upper(), url, headers=headers)

        response = conn.getresponse()
        reply = u'%s %s' % (response.status, response.reason)

        data = response.read()
        conn.close()

        if action == 'GET':
            match = title.search(data)
            if match:
                reply += u' "%s"' % match.groups()[0].strip()

        event.addresponse(u'%s', reply)

# vi: set et sta sw=4 ts=4:
