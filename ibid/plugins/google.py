from urllib import quote
from urllib2 import urlopen, Request
from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match
from ibid.config import Option

help = {'google': 'Retrieves results from Google and Google Calculator.'}

user_agent = 'Mozilla/5.0'

class Search(Processor):
    """google [for] <term>"""
    feature = 'google'

    user_agent = Option('user_agent', 'HTTP user agent to present to Google', user_agent)

    @match(r'^google\s+(?:(za)\s+)?(?:for\s+)?(.+?)$')
    def search(self, event, country, query):
        url = 'http://www.google.com/search?num=3&q=%s' % quote(query)
        if country:
            url = url + '&meta=cr%%3Dcountry%s' % country.upper()

        f = urlopen(Request(url, headers={'user-agent': self.user_agent}))
        soup = BeautifulSoup(f.read())
        f.close()

        results = []
        paras = soup.findAll('p')[:10]
        for para in paras:
            try:
                url = para.a['href']
                title = ''.join([e.string for e in para.a.contents])
                results.append('"%s" %s' % (title, url))
            except Exception:
                pass

        event.addresponse(', '.join(results))

class Calc(Processor):
    """gcalc <expression>"""
    feature = 'google'

    user_agent = Option('user_agent', 'HTTP user agent to present to Google', user_agent)

    @match(r'^gcalc\s+(.+)$')
    def calc(self, event, expression):
        f = urlopen(Request('http://www.google.com/search?num=1&q=%s' % quote(expression), headers={'user-agent': self.user_agent}))
        soup = BeautifulSoup(f.read())
        f.close()

        font = soup.find('font', size='+1')
        if not font:
            event.addresponse(u'No result')
        else:
            event.addresponse(font.b.string)

class Define(Processor):
    """gdefine <term>"""
    feature = 'google'

    user_agent = Option('user_agent', 'HTTP user agent to present to Google', user_agent)

    @match(r'^gdefine\s+(.+)$')
    def define(self, event, term):
        f = urlopen(Request('http://www.google.com/search?num=1&q=define:%s' % quote(term), headers={'user-agent': self.user_agent}))
        soup = BeautifulSoup(f.read())
        f.close()

        definitions = []
        for li in soup.findAll('li'):
            definitions.append('"%s"' % li.contents[0])

        if definitions:
            event.addresponse(', '.join(definitions))
        else:
            event.addresponse(u"Are you making up words again?")

class Compare(Processor):
    """google cmp [for] <term> and <term>"""
    feature = 'google'

    user_agent = Option('user_agent', 'HTTP user agent to present to Google', user_agent)


    def results(self, term):
        f = urlopen(Request('http://www.google.com/search?num=1&q=%s' % quote(term), headers={'user-agent': self.user_agent}))
        soup = BeautifulSoup(f.read())
        f.close()

        noresults = soup.findAll('div', attrs={'class': 'med'})
        if noresults and len(noresults) > 1 and noresults[1].find('did not match any documents') != -1:
            return 0
        else:
            results = soup.find('div', id='prs').nextSibling.contents[5].string.replace(',', '')
            if results:
                return int(results)

    @match(r'^google\s+cmp\s+(?:for\s+)?(.+?)\s+and\s+(.+?)$')
    def compare(self, event, term1, term2):
        count1 = self.results(term1)
        count2 = self.results(term2)
        event.addresponse(u'%s wins with %s hits, %s had %s hits' % (count1 > count2 and term1 or term2, count1 > count2 and count1 or count2, count1 > count2 and term2 or term1, count1 > count2 and count2 or count1))

# vi: set et sta sw=4 ts=4:
