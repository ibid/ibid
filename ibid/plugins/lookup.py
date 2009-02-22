from urllib2 import urlopen, Request
from urllib import urlencode, quote
from time import time
from datetime import datetime
from simplejson import loads
import re

import feedparser
from BeautifulSoup import BeautifulSoup

from ibid.plugins import Processor, match, handler
from ibid.config import Option
from ibid.utils import ago, decode_htmlentities

help = {}

class Bash(Processor):

    @match(r'^bash(?:\.org)?\s+(random|\d+)$')
    def bash(self, event, quote):
        f = urlopen('http://bash.org/?%s' % quote.lower())
        soup = BeautifulSoup(f.read(), convertEntities=BeautifulSoup.HTML_ENTITIES)
        f.close()

        quote = soup.find('p', attrs={'class': 'qt'})
        if not quote:
            event.addresponse(u"There's no such quote, but if you keep talking like that maybe there will be.")
        else:
            for line in quote.contents:
                if str(line) != '<br />':
                    event.addresponse(str(line).strip())

class LastFm(Processor):
    @match(r'^last\.?fm\s+for\s+(\S+?)\s*$')
    def listsongs(self, event, username):
        songs = feedparser.parse("http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.rss?%s" % (username, time()))
        if songs['bozo']:
            event.addresponse(u"No such user")
        else:
            event.addresponse(u', '.join(u'%s (%s ago)' % (e.title, ago(datetime.utcnow() - datetime.strptime(e.updated, '%a, %d %b %Y %H:%M:%S +0000'), 1)) for e in songs['entries']))

help['lotto'] = u"Gets the latest lotto results from the South African National Lottery"
class Lotto(Processor):
    """lotto"""
    feature = 'lotto'
    
    errors = {
      'open': 'Something went wrong getting to the Lotto site',
      'balls': 'I expected to get %s balls, but found %s. They were: %s',
    }
    
    za_url = 'http://www.nationallottery.co.za/'
    za_re = re.compile(r'images/balls/ball_(\d+).gif')
    za_text = 'Latest lotto results for South Africa, Lotto: '
    
    @match(r'lotto(\s+for\s+south\s+africa)?')
    def za(self, event, za):
        try:
            f = urlopen(self.za_url)
        except Exception, e:
            return event.addresponse(self.errors['open'])
        
        s = "".join(f)
        f.close()
        
        r = self.za_text
        
        balls = self.za_re.findall(s)
        
        if len(balls) != 14:
            return event.addresponse(self.errors['balls'] % \
                     (14, len(balls), ", ".join(balls)))
        
        r += " ".join(balls[:6])
        r += " (Bonus: %s), Lotto Plus: " % (balls[6], )
        r += " ".join(balls[7:13])
        r += " (Bonus: %s)" % (balls[13], )
        event.addresponse(r)

class FMyLife(Processor):

    def remote_get(self, id):
        f = urlopen('http://www.fmylife.com/' + str(id))
        soup = BeautifulSoup(f.read())
        f.close()

        quote = soup.find('div', id='wrapper').div.p
        return quote and u'"%s"' % (quote.contents[0],) or None

    @match(r'^(?:fml\s+|http://www\.fmylife\.com/\S+/)(\d+)$')
    def fml(self, event, id):
        event.addresponse(self.remote_get(int(id)) or u"No such quote")

class Twitter(Processor):

    default = { 'twitter': 'http://twitter.com/',
                'tweet': 'http://twitter.com/',
                'identica': 'http://identi.ca/api/',
                'identi.ca': 'http://identi.ca/api/',
              }
    services = Option('services', 'Micro blogging services', default)

    def setup(self):
        self.update.im_func.pattern = re.compile(r'^(%s)\s+(\d+)$' % ('|'.join(self.services.keys()),))
        self.latest.im_func.pattern = re.compile(r'^(?:latest|last)\s+(%s)\s+(?:update\s+)?(?:by\s+|from\s+)?(\S+)$' % ('|'.join(self.services.keys()),))

    def remote_update(self, service, id):
        f = urlopen('%sstatuses/show/%s.json' % (self.services[service], id))
        status = loads(f.read())
        f.close()

        return u'%s: "%s"' % (status['user']['screen_name'], status['text'])

    def remote_latest(self, service, user):
        f = urlopen('%sstatuses/user_timeline/%s.json?count=1' % (self.services[service], user))
        statuses = loads(f.read())
        f.close()

        return u'"%s"' % (statuses[0]['text'])

    @handler
    def update(self, event, service, id):
        event.addresponse(self.remote_update(service.lower(), int(id)))

    @handler
    def latest(self, event, service, user):
        event.addresponse(self.remote_latest(service.lower(), user))

    @match(r'^https?://(?:www\.)?twitter\.com/[^/ ]+/statuse?s?/(\d+)$')
    def twitter(self, event, id):
        event.addresponse(self.remote_update('twitter', int(id)))

    @match(r'^https?://(?:www\.)?identi.ca/notice/(\d+)$')
    def identica(self, event, id):
        event.addresponse(self.remote_update('identi.ca', int(id)))

class Currency(Processor):

    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.xe.com/'}
    currencies = []

    def _load_currencies(self):
        request = Request('http://www.xe.com/iso4217.php', '', self.headers)
        f = urlopen(request)
        soup = BeautifulSoup(f.read())
        f.close()

        self.currencies = []
        for tr in soup.find('table', attrs={'class': 'tbl_main'}).table.findAll('tr'):
            code, place = tr.findAll('td')
            place = ''.join(place.findAll(text=True))
            place, name = place.find(',') != -1 and place.split(',', 1) or place.split(' ', 1)
            self.currencies.append((code.string, place.strip(), name.strip()))

    @match(r'^(?:exchange|convert)\s+([0-9.]+)\s+(\S+)\s+(?:for|to|into)\s+(\S+)$')
    def exchange(self, event, amount, frm, to):
        data = {'Amount': amount, 'From': frm, 'To': to}
        request = Request('http://www.xe.com/ucc/convert.cgi', urlencode(data), self.headers)
        f = urlopen(request)
        soup = BeautifulSoup(f.read())
        f.close()

        event.addresponse(soup.findAll('span', attrs={'class': 'XEsmall'})[1].contents[0])

    @match(r'^(?:currency|currencies)\s+for\s+(?:the\s+)?(.+)$')
    def currency(self, event, place):
        if not self.currencies:
            self._load_currencies()

        search = re.compile(place, re.I)
        results = []
        for code, place, name in self.currencies:
            if search.search(place):
                results.append('%s uses %s (%s)' % (place, name, code))

        if results:
            event.addresponse(u', '.join(results))
        else:
            event.addresponse(u'No currencies found')

class Weather(Processor):

    defaults = {    'ct': 'Cape Town, South Africa',
                    'jhb': 'Johannesburg, South Africa',
                    'joburg': 'Johannesburg, South Africa',
               }
    places = Option('places', 'Alternate names for places', defaults)
    labels = ('temp', 'humidity', 'dew', 'wind', 'pressure', 'conditions', 'visibility', 'uv', 'clouds', 'ymin', 'ymax', 'ycool', 'sunrise', 'sunset', 'moonrise', 'moonset', 'moonphase', 'metar')
    whitespace = re.compile('\s+')

    def _text(self, string):
        if not isinstance(string, basestring):
            string = ''.join(string.findAll(text=True))
        string = self.whitespace.sub(' ', string).strip()
        return decode_htmlentities(string)

    def _get_page(self, place):
        if place.lower() in self.places:
            place = self.places[place.lower()]

        f = urlopen('http://m.wund.com/cgi-bin/findweather/getForecast?brand=mobile_metric&query=' + quote(place))
        soup = BeautifulSoup(f.read())
        f.close()

        return soup

    def remote_weather(self, place):
        soup = self._get_page(place)
        tds = soup.table.table.findAll('td')

        values = {'place': tds[0].findAll('b')[1].string, 'time': tds[0].findAll('b')[0].string}
        for index, td in enumerate(tds[2::2]):
            values[self.labels[index]] = self._text(td)

        return u'In %(place)s at %(time)s: %(temp)s; Humidity: %(humidity)s; Wind: %(wind)s; Conditions: %(conditions)s; Sunrise/set: %(sunrise)s/%(sunset)s; Moonrise/set: %(moonrise)s/%(moonset)s' % values

    def remote_forecast(self, place):
        soup = self._get_page(place)
        forecasts = []
        for td in soup.findAll('table')[2].findAll('td', align='left'):
            day = td.b.string
            forecast = td.contents[2]
            forecasts.append('%s: %s' % (day, self._text(forecast)))

        return forecasts

    @match(r'^weather\s+(?:(?:for|at|in)\s+)?(.+)$')
    def weather(self, event, place):
        event.addresponse(self.remote_weather(place))

    @match(r'^forecast\s+(?:for\s+)?(.+)$')
    def forecast(self, event, place):
        event.addresponse(u', '.join(self.remote_forecast(place)))

# vi: set et sta sw=4 ts=4:
