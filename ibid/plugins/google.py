from urllib import quote
from urllib2 import urlopen, Request
from BeautifulSoup import BeautifulSoup

import ibid
from ibid.plugins import Processor, match

help = {'google': 'Retrieves results from Google and Google Calculator.'}

class Search(Processor):
    """google [for] <term>"""
    feature = 'google'

    @match(r'^google\s+(?:(za)\s+)?(?:for\s+)?(.+?)$')
    def search(self, event, country, query):
        url = 'http://www.google.com/search?num=3&q=%s' % quote(query)
        if country:
            url = url + '&meta=cr%%3Dcountry%s' % country.upper()

        f = urlopen(Request(url, headers={'user-agent': 'Mozilla/4.5'}))
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

    @match(r'^gcalc\s+(.+)$')
    def calc(self, event, expression):
        f = urlopen(Request('http://www.google.com/search?num=1&q=%s' % quote(expression), headers={'user-agent': 'Mozilla/5.0'}))
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

    @match(r'^gdefine\s+(.+)$')
    def define(self, event, term):
        f = urlopen(Request('http://www.google.com/search?num=1&q=define:%s' % quote(term), headers={'user-agent': 'Mozilla/5.0'}))
        soup = BeautifulSoup(f.read())
        f.close()

        definitions = []
        for li in soup.findAll('li'):
            definitions.append('"%s"' % li.contents[0])

        if definitions:
            event.addresponse(', '.join(definitions))
        else:
            event.addresponse(u"Are you making up words again?")

# vi: set et sta sw=4 ts=4:
