# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from httplib import BadStatusLine
from urllib import quote
from urllib2 import urlopen, Request

from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import decode_htmlentities, json_webservice

features = {'google': {
    'description': u'Retrieves results from Google and Google Calculator.',
    'categories': ('lookup', 'web', 'calculate', ),
}}

default_user_agent = 'Mozilla/5.0'
default_referer = "http://ibid.omnia.za.net/"

class GoogleAPISearch(Processor):
    usage = u"""google[.<tld>] [for] <term>
    googlefight [for] <term> and <term>"""

    feature = ('google',)

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

    feature = ('google',)

    user_agent = Option('user_agent', 'HTTP user agent to present to Google (for non-API searches)', default_user_agent)
    google_scrape_url = "http://www.google.com/search?q=%s"

    def _google_scrape_search(self, query, country=None):
        url = self.google_scrape_url
        if country:
            url += "&cr=country%s" % country.upper()
        f = urlopen(Request(url % quote(query.encode('utf-8')),
                            headers={'user-agent': self.user_agent}))
        soup = BeautifulSoup(f.read())
        f.close()
        return soup

    @match(r'^gcalc\s+(.+)$')
    def calc(self, event, expression):
        soup = self._google_scrape_search(expression)

        container = soup.find('h2', 'r')
        if not container:
            event.addresponse(u'No result')
        else:
            event.addresponse(container.b.string)

    @match(r'^gdefine\s+(.+)$')
    def define(self, event, term):
        soup = self._google_scrape_search("define:%s" % term)

        definitions = []
        for li in soup.findAll('li'):
            definitions.append(decode_htmlentities(li.contents[0].strip()))

        if definitions:
            event.addresponse(u' :: '.join(definitions))
        else:
            event.addresponse(u'Are you making up words again?')

# vi: set et sta sw=4 ts=4:
