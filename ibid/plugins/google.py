import htmlentitydefs
import re
import simplejson
from urllib import quote
from urllib2 import urlopen, Request

from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import ibid_version

help = {'google': u'Retrieves results from Google and Google Calculator.'}

user_agent = 'Mozilla/5.0'

class GoogleAPISearch(Processor):
    u"""google [for] <term>
    googlefight [for] <term> and <term>"""

    feature = 'google'

    api_key = Option('api_key', 'Your Google API Key (optional)', None)
    referrer = Option('referrer', 'The referrer string to use (API searches)', "http://ibid.omnia.za.net/")

    google_api_url = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=%s"

    def _google_api_search(self, query, resultsize="large"):
        url = self.google_api_url % quote(query)
        url += "&rsz=%s" % resultsize
        if self.api_key:
            url += '&key=%s' % quote(key)
        req = Request(url, headers={
            'user-agent': "Ibid/%s" % ibid_version() or "dev",
            'referrer': self.referrer,
        })
        f = urlopen(req)
        result = f.readlines()
        f.close()
        result = "".join(result)
        result = simplejson.loads(result)
        return result

    @match(r'^google\s+(?:for\s+)?(.+?)$')
    def search(self, event, query):
        items = self._google_api_search(query)
        results = []
        for item in items["responseData"]["results"]:

            title = item["titleNoFormatting"]

            replace = lambda match: unichr(int(match.group(1)))
            title = re.sub("&#(\d+);", replace, title)

            replace = lambda match: unichr(htmlentitydefs.name2codepoint[match.group(1)])
            title = re.sub("&(\w+);", replace, title)

            results.append(u'"%s" %s' % (title, item["unescapedUrl"]))
            
        if results:
            event.addresponse(u', '.join(results))
        else:
            event.addresponse(u"Wow! Google couldn't find anything.")

    @match(r'^(?:rank|(?:google(?:fight|compare|cmp)))\s+(?:for\s+)?(.+?)\s+and\s+(.+?)$')
    def googlefight(self, event, term1, term2):
        count1 = int(self._google_api_search(term1, "small")["responseData"]["cursor"].get("estimatedResultCount", 0))
        count2 = int(self._google_api_search(term2, "small")["responseData"]["cursor"].get("estimatedResultCount", 0))
        event.addresponse(u'%s wins with %i hits, %s had %i hits' % 
            (count1 > count2 and (term1, count1, term2, count2) or (term2, count2, term1, count1))
        )

class GoogleScrapeSearch(Processor):
    u"""gcalc <expression>
    gdefine <term>"""

    feature = 'google'

    user_agent = Option('user_agent', 'HTTP user agent to present to Google (for non-API searches)', user_agent)
    google_scrape_url = "http://www.google.com/search?num=1&q=%s"

    def _google_scrape_search(self, query):
        f = urlopen(Request(self.google_scrape_url % quote(query), headers={'user-agent': self.user_agent}))
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
            definitions.append(li.contents[0].strip())

        if definitions:
            event.addresponse(u' :: '.join(definitions))
        else:
            event.addresponse(u"Are you making up words again?")

# vi: set et sta sw=4 ts=4:
