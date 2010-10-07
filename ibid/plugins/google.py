# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from httplib import BadStatusLine
import re
from urllib import urlencode

from ibid.compat import ElementTree
from ibid.config import Option
from ibid.plugins import Processor, match
from ibid.utils import decode_htmlentities, json_webservice
from ibid.utils.html import get_html_parse_tree

features = {'google': {
    'description': u'Retrieves results from Google and Google Calculator.',
    'categories': ('lookup', 'web', 'calculate', ),
}}

default_user_agent = 'Mozilla/5.0'
default_referer = "http://ibid.omnia.za.net/"

class GoogleAPISearch(Processor):
    usage = u"""google[.<tld>] [for] <term>
    googlefight [for] <term> and <term>"""

    features = ('google',)

    api_key = Option('api_key', 'Your Google API Key (optional)', None)
    referer = Option('referer', 'The referer string to use (API searches)', default_referer)

    def _google_api_search(self, query, resultsize="large", country=None):
        params = {
            'v': '1.0',
            'q': query,
            'rsz': resultsize,
        }
        if country is not None:
            params['gl'] = country
        if self.api_key:
            params['key'] = self.api_key

        headers = {'referer': self.referer}
        return json_webservice('http://ajax.googleapis.com/ajax/services/search/web', params, headers)

    @match(r'^google(?:\.com?)?(?:\.([a-z]{2}))?\s+(?:for\s+)?(.+?)$')
    def search(self, event, country, query):
        try:
            items = self._google_api_search(query, country=country)
        except BadStatusLine:
            event.addresponse(u"Google appears to be broken (or more likely, my connection to it)")
            return

        results = []
        for item in items["responseData"]["results"]:
            title = item["titleNoFormatting"]
            results.append(u'"%s" %s' % (decode_htmlentities(title), item["unescapedUrl"]))

        if results:
            event.addresponse(u' :: '.join(results))
        else:
            event.addresponse(u"Wow! Google couldn't find anything")

    @match(r'^(?:rank|(?:google(?:fight|compare|cmp)))\s+(?:for\s+)?(.+?)\s+and\s+(.+?)$')
    def googlefight(self, event, term1, term2):
        try:
            count1 = int(self._google_api_search(term1, "small")["responseData"]["cursor"].get("estimatedResultCount", 0))
            count2 = int(self._google_api_search(term2, "small")["responseData"]["cursor"].get("estimatedResultCount", 0))
        except BadStatusLine:
            event.addresponse(u"Google appears to be broken (or more likely, my connection to it)")
            return

        event.addresponse(u'%(firstterm)s wins with %(firsthits)i hits, %(secondterm)s had %(secondhits)i hits',
            (count1 > count2 and {
                'firstterm':  term1,
                'firsthits':  count1,
                'secondterm': term2,
                'secondhits': count2,
            } or {
                'firstterm':  term2,
                'firsthits':  count2,
                'secondterm': term1,
                'secondhits': count1,
            }))

# Unfortunatly google API search doesn't support all of google search's
# features.
# Dear Google: We promise we don't bite.
class GoogleScrapeSearch(Processor):
    usage = u"""gcalc <expression>
    gdefine <term>"""

    features = ('google',)

    user_agent = Option('user_agent', 'HTTP user agent to present to Google (for non-API searches)', default_user_agent)

    def _google_scrape_search(self, query, country=None):
        params = {'q': query.encode('utf-8')}
        if country:
            params['cr'] = u'country' + country.upper()

        return get_html_parse_tree(
                'http://www.google.com/search?' + urlencode(params),
                headers={'user-agent': self.user_agent},
                treetype='etree')

    @match(r'^gcalc\s+(.+)$')
    def calc(self, event, expression):
        tree = self._google_scrape_search(expression)

        nodes = [node for node in tree.findall('.//h2/b')]
        if len(nodes) == 1:
            # ElementTree doesn't support inline tags:
            # May return ASCII unless an encoding is specified.
            # "utf8" will result in an xml header
            node = ElementTree.tostring(nodes[0], encoding='utf-8')
            node = node.decode('utf-8')
            node = re.sub(r'^<b>(.*)</b>$', lambda x: x.group(1), node)
            node = re.sub(r'<sup>(.*?)</sup>',
                          lambda x: u'^' + x.group(1), node)
            node = decode_htmlentities(node)
            event.addresponse(node)
        else:
            event.addresponse(u'No result')

    @match(r'^gdefine\s+(.+)$')
    def define(self, event, term):
        tree = self._google_scrape_search("define:%s" % term)

        definitions = []
        for li in tree.findall('.//li'):
            definitions.append(li.text)

        if definitions:
            event.addresponse(u' :: '.join(definitions))
        else:
            event.addresponse(u'Are you making up words again?')

# vi: set et sta sw=4 ts=4:
