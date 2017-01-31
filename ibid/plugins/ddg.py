# Copyright (c) 2016, Kyle Robbertze
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from httplib import BadStatusLine

from ibid.plugins import Processor, match
from ibid.utils import json_webservice

features = {'duckduckgo': {
    'description': u'Retrieves results from DuckDuckGo',
    'categories': ('lookup', 'web', 'calculate', ),
}}


class DDGAPISearch(Processor):
    usage = u"""ddg[.<tld>] [for] <term>"""
    features = ('duckduckgo',)

    def _ddg_api_search(self, query, resultsize="large", country=None):
        params = {
            'q': query,
            't': 'ibid',
            'format': 'json',
        }
        if country is not None:
            params['gl'] = country

        return json_webservice('https://api.duckduckgo.com', params)

    @match(r'^ddg(?:\.com?)?(?:\.([a-z]{2}))?\s+(?:for\s+)?(.+?)$')
    def search(self, event, country, query):
        try:
            items = self._ddg_api_search(query, country=country)
        except BadStatusLine:
            event.addresponse(
                u'DuckDuckGo appears to be broken (or more likely, '
                u'my connection to it)')
            return

        results = []
        for item in items['Results']:
            title = item['Text']
            url = item['FirstURL']
            results.append(u'"%s" %s' % (title, url))

        for item in items['RelatedTopics'][:5]:
            if 'Text' in item:
                title = item['Text']
                url = item['FirstURL']
                results.append(u'"%s" %s' % (title, url))

        if results:
            event.addresponse(u' :: '.join(results))
            event.addresponse(u'(Results from DuckDuckGo)')
        else:
            event.addresponse(
                u'Uhh... DuckDuckGo has no Instant Answer on that')

# vi: set et sta sw=4 ts=4:
