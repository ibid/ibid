from cgi import parse_qs
from httplib import BadStatusLine
from urllib import quote
from urllib2 import urlopen, Request
from urlparse import urlparse

from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import decode_htmlentities, ibid_version, json_webservice

help = {'google': u'Retrieves results from Google and Google Calculator.'}

default_user_agent = 'Mozilla/5.0'
default_referrer = "http://ibid.omnia.za.net/"

class GoogleAPISearch(Processor):
    u"""google [for] <term>
    googlefight [for] <term> and <term>"""

    feature = 'google'

    api_key = Option('api_key', 'Your Google API Key (optional)', None)
    referrer = Option('referrer', 'The referrer string to use (API searches)', default_referrer)

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

        headers={
            'user-agent': "Ibid/%s" % ibid_version() or "dev",
            'referrer': self.referrer,
        }
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

            results.append(u'%s <%s>' % (decode_htmlentities(title), item["unescapedUrl"]))

        if results:
            event.addresponse(u', '.join(results))
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
    u"""gcalc <expression>
    gdefine <term>
    google.<TLD> [for] <terms>"""

    feature = 'google'

    user_agent = Option('user_agent', 'HTTP user agent to present to Google (for non-API searches)', default_user_agent)
    google_scrape_url = "http://www.google.com/search?q=%s"

    def _google_scrape_search(self, query, country=None):
        url = self.google_scrape_url
        if country:
            url += "&cr=country%s" % country.upper()
        f = urlopen(Request(url % quote(query), headers={'user-agent': self.user_agent}))
        soup = BeautifulSoup(f.read())
        f.close()
        return soup

    @match(r'^gcalc\s+(.+)$')
    def calc(self, event, expression):
        soup = self._google_scrape_search(expression)

        font = soup.find('font', size='+1')
        if not font:
            event.addresponse(u'No result')
        else:
            event.addresponse(font.b.string)

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
