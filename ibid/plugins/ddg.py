# Copyright (c) 2008-2011, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from httplib import BadStatusLine

from ibid.config import Option
from ibid.plugins import Processor, match
from ibid.utils import decode_htmlentities, json_webservice

features = {'duckduckgo': {
    'description': u'Retrieves results from DuckDuckGo',
    'categories': ('lookup', 'web', 'calculate', ),
}}

default_user_agent = 'Mozilla/5.0'
default_referer = "http://ibid.omnia.za.net/"

class DDGAPISearch(Processor):
    usage = u"""ddg[.<tld>] [for] <term>"""

    features = ('duckduckgo',)

    referer = Option('referer', 'The referer string to use (API searches)', default_referer)

    def _ddg_api_search(self, query, resultsize="large", country=None):
        params = {
            'v': '1.0',
            'q': query,
            't': 'ibid',
            'rsz': resultsize,
            'format': 'json',
        }
        if country is not None:
            params['gl'] = country

        headers = {'referer': self.referer}
        return json_webservice('http://api.duckduckgo.com', params, headers)

    @match(r'^(ddg|duckduckgo(?:\.com?))?(?:\.([a-z]{2}))?\s+(?:for\s+)?(.+?)$')
    def search(self, event, key, country, query):
        try:
            items = self._ddg_api_search(query, country=country)
        except BadStatusLine:
            event.addresponse(u"DuckDuckGo appears to be broken (or more likely, my connection to it)")
            return

        results = []
        for item in items['RelatedTopics']:
            try:
                title = item['Text']
                results.append(u'"%s" %s' % (decode_htmlentities(title), item["FirstURL"]))
            except KeyError:
                pass

        if results:
            event.addresponse(u' :: '.join(results))
        else:
            event.addresponse(u"Wow! DuckDuckGo couldn't find anything")
# vi: set et sta sw=4 ts=4:
