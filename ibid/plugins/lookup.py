from urllib2 import urlopen
from urllib import urlencode, quote
from urlparse import urljoin
from time import time
from datetime import datetime
from simplejson import loads
from xml.dom.minidom import parse
import re

import feedparser

from ibid.plugins import Processor, match, handler
from ibid.config import Option
from ibid.utils import ago, decode_htmlentities, get_html_parse_tree, cacheable_download

help = {}

def get_country_codes():
    # The XML download doesn't include things like UK, so we consume this steaming pile of crud instead
    filename = cacheable_download('http://www.iso.org/iso/country_codes/iso_3166_code_lists/iso-3166-1_decoding_table.htm', 'lookup/iso-3166-1_decoding_table.htm')
    etree = get_html_parse_tree('file://' + filename, treetype='etree')
    table = [x for x in etree.getiterator('table')][2]

    countries = {}
    for tr in table.getiterator('tr'):
        abbr = [x.text for x in tr.getiterator('div')][0]
        eng_name = [x.text for x in tr.getchildren()][1]

        if eng_name and eng_name.strip():
            # Cleanup:
            if u',' in eng_name:
                eng_name = u' '.join(reversed(eng_name.split(',', 1)))
            eng_name = u' '.join(eng_name.split())

            countries[abbr.upper()] = eng_name.title()

    return countries

help['bash'] = u'Retrieve quotes from bash.org.'
class Bash(Processor):
    u"bash[.org] (random|<number>)"

    feature = 'bash'

    @match(r'^bash(?:\.org)?\s+(random|\d+)$')
    def bash(self, event, quote):
        soup = get_html_parse_tree('http://bash.org/?%s' % quote.lower())

        if quote.lower() == "random":
            number = u"".join(soup.find('p', 'quote').find('b').contents)
            event.addresponse(u'%s:', number)

        quote = soup.find('p', 'qt')
        if not quote:
            event.addresponse(u"There's no such quote, but if you keep talking like that maybe there will be")
        else:
            for line in quote.contents:
                if str(line) != '<br />':
                    event.addresponse(line.strip())

help['lastfm'] = u'Lists the tracks last listened to by the specified user.'
class LastFm(Processor):
    u"last.fm for <username>"

    feature = "lastfm"

    @match(r'^last\.?fm\s+for\s+(\S+?)\s*$')
    def listsongs(self, event, username):
        songs = feedparser.parse('http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.rss?%s' % (username, time()))
        if songs['bozo']:
            event.addresponse(u'No such user')
        else:
            event.addresponse(u', '.join(u'%s (%s ago)' % (e.title, ago(datetime.utcnow() - datetime.strptime(e.updated, '%a, %d %b %Y %H:%M:%S +0000'), 1)) for e in songs['entries']))

help['lotto'] = u"Gets the latest lotto results from the South African National Lottery."
class Lotto(Processor):
    u"""lotto"""

    feature = 'lotto'
    
    za_url = 'http://www.nationallottery.co.za/'
    za_re = re.compile(r'images/balls/ball_(\d+).gif')
    
    @match(r'^lotto(\s+for\s+south\s+africa)?$')
    def za(self, event, za):
        try:
            f = urlopen(self.za_url)
        except Exception, e:
            event.addresponse(u'Something went wrong getting to the Lotto site')
            return
        
        s = "".join(f)
        f.close()
        
        balls = self.za_re.findall(s)
        
        if len(balls) != 14:
            event.addresponse(u'I expected to get %(expected)s balls, but found %(found)s. They were: %(balls)s', {
                'expected': 14,
                'found': len(balls),
                'balls': u', '.join(balls),
            })
            return
        
        event.addresponse(u'Latest lotto results for South Africa, '
            u'Lotto: %(lottoballs)s (Bonus: %(lottobonus)s), Lotto Plus: %(plusballs)s (Bonus: %(plusbonus)s)', {
            'lottoballs': u" ".join(balls[:6]),
            'lottobonus': balls[6],
            'plusballs':  u" ".join(balls[7:13]),
            'plusbonus':  balls[13],
        })

help['fml'] = u'Retrieves quotes from fmylife.com.'
class FMyLife(Processor):
    u"""fml (<number> | [random] | <category> | flop | top | last)
    fml categories"""

    feature = "fml"

    api_url = Option('fml_api_url', 'FML API URL base', 'http://api.betacie.com/')
    api_key = Option('fml_api_key', 'FML API Key (optional)', 'readonly')
    fml_lang = Option('fml_lang', 'FML Lanugage', 'en')

    def remote_get(self, id):
        url = urljoin(self.api_url, 'view/%s?%s' % (
            id.isalnum() and id + '/nocomment' or quote(id),
            urlencode({'language': self.fml_lang, 'key': self.api_key}))
        )
        dom = parse(urlopen(url))

        if dom.getElementsByTagName('error'):
            return

        items = dom.getElementsByTagName('item')
        if items: 
            url = u"http://www.fmylife.com/%s/%s" % (
                items[0].getElementsByTagName('category')[0].childNodes[0].nodeValue,
                items[0].getAttribute('id'),
            )
            text = items[0].getElementsByTagName('text')[0].childNodes[0].nodeValue

            return u'%s : %s' % (url, text)

    def setup(self):
        url = urljoin(self.api_url, 'view/categories?' + urlencode({'language': self.fml_lang, 'key': self.api_key}))
        dom = parse(urlopen(url))
        self.categories = [cat.getAttribute('code') for cat in dom.getElementsByTagName('categorie')]

        self.fml.im_func.pattern = re.compile(r'^(?:fml\s+|http://www\.fmylife\.com/\S+/)(\d+|random|flop|top|last|%s)$' % (
            '|'.join(self.categories),
        ), re.I)

    @handler
    def fml(self, event, id):
        quote = self.remote_get(id)
        if quote:
            event.addresponse(quote)
        else:
            event.addresponse(u'No such quote')

    @match(r'^fml$')
    def fml_default(self, event):
        event.addresponse(self.remote_get('random'))

    @match(r'^fml\s+categories$')
    def list_categories(self, event):
        event.addresponse(u'Categories: %s', u', '.join(self.categories))

help["microblog"] = u"Looks up messages on microblogging services like twitter and identica."
class Twitter(Processor):
    u"""latest (tweet|identica) from <name>
    (tweet|identica) <number>"""

    feature = "microblog"

    default = { 'twitter': 'http://twitter.com/',
                'tweet': 'http://twitter.com/',
                'identica': 'http://identi.ca/api/',
                'identi.ca': 'http://identi.ca/api/',
              }
    services = Option('services', 'Micro blogging services', default)

    def setup(self):
        self.update.im_func.pattern = re.compile(r'^(%s)\s+(\d+)$' % ('|'.join(self.services.keys()),), re.I)
        self.latest.im_func.pattern = re.compile(r'^(?:latest|last)\s+(%s)\s+(?:update\s+)?(?:(?:by|from|for)\s+)?(\S+)$' % ('|'.join(self.services.keys()),), re.I)

    def remote_update(self, service, id):
        f = urlopen('%sstatuses/show/%s.json' % (self.services[service], id))
        status = loads(f.read())
        f.close()

        return {'screen_name': status['user']['screen_name'], 'text': decode_htmlentities(status['text'])}

    def remote_latest(self, service, user):
        service_url = self.services[service]
        f = urlopen('%sstatuses/user_timeline/%s.json?count=1' % (service_url, user))
        statuses = loads(f.read())
        f.close()
        latest = statuses[0]

        if "twitter" in service_url:
            url = "%s%s/status/%i" % (service_url, latest["user"]["screen_name"], latest["id"])
        elif service_url.endswith("/api/"):
            url = "%s/notice/%i" % (service_url[:-5], latest["id"])

        return {
            'text': decode_htmlentities(latest['text']),
            'ago': ago(datetime.utcnow() - datetime.strptime(latest["created_at"], '%a %b %d %H:%M:%S +0000 %Y'), 1),
            'url': url,
        }

    @handler
    def update(self, event, service, id):
        event.addresponse(u'%(screen_name)s: "%(text)s"', self.remote_update(service.lower(), int(id)))

    @handler
    def latest(self, event, service, user):
        event.addresponse(u'"%(text)s" %(ago)s ago, %(url)s', self.remote_latest(service.lower(), user))

    @match(r'^https?://(?:www\.)?twitter\.com/[^/ ]+/statuse?s?/(\d+)$')
    def twitter(self, event, id):
        event.addresponse(u'%(screen_name)s: "%(text)s"', self.remote_update('twitter', int(id)))

    @match(r'^https?://(?:www\.)?identi.ca/notice/(\d+)$')
    def identica(self, event, id):
        event.addresponse(u'%(screen_name)s: "%(text)s"', self.remote_update('identi.ca', int(id)))

help['currency'] = u'Converts amounts between currencies.'
class Currency(Processor):
    u"""exchange <amount> <currency> for <currency>
    currencies for <country>"""

    feature = "currency"

    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.xe.com/'}
    currencies = {}
    country_codes = {}
    strip_currency_re = re.compile(r'^[\.\s]*([\w\s]+?)s?$', re.UNICODE)

    def _load_currencies(self):
        etree = get_html_parse_tree('http://www.xe.com/iso4217.php', headers=self.headers, treetype='etree')

        tbl_main = [x for x in etree.getiterator('table') if x.get('class') == 'tbl_main'][0]

        self.currencies = {}
        for tbl_sub in tbl_main.getiterator('table'):
            if tbl_sub.get('class') == 'tbl_sub':
                for tr in tbl_sub.getiterator('tr'):
                    code, place = [x.text for x in tr.getchildren()]
                    name = u''
                    if not place:
                        place = u''
                    if u',' in place[1:-1]:
                        place, name = place.split(u',', 1)
                    place = place.strip()
                    if code in self.currencies:
                        currency = self.currencies[code]
                        # Are we using another country's currency?
                        if place != u'' and name != u'' and (currency[1] == u'' or currency[1].rsplit(None, 1)[0] in place
                                or (u'(also called' in currency[1] and currency[1].split(u'(', 1)[0].rsplit(None, 1)[0] in place)):
                            currency[0].insert(0, place)
                            currency[1] = name.strip()
                        else:
                            currency[0].append(place)
                    else:
                        self.currencies[code] = [[place], name.strip()]
        # Special cases for shared currencies:
        self.currencies['EUR'][0].insert(0, u'Euro Member Countries')
        self.currencies['XOF'][0].insert(0, u'Communaut\xe9 Financi\xe8re Africaine')
        self.currencies['XOF'][1] = u'Francs'


    def _resolve_currency(self, name):
        "Return the canonical name for a currency"

        if name.upper() in self.currencies:
            return name.upper()

        name = self.strip_currency_re.match(name).group(1).lower()

        # TLD -> country name
        if len(name) == 2 and name.upper() in self.country_codes:
           name = self.country_codes[name.upper()].lower()
        
        # Currency Name
        if name == u'dollar':
            return "USD"

        name_re = re.compile(r'^(.+\s+)?\(?%ss?\)?(\s+.+)?$' % name, re.I | re.UNICODE)
        for code, (places, currency) in self.currencies.iteritems():
            if name_re.match(currency) or [True for place in places if name_re.match(place)]:
                return code

        return False

    @match(r'^(exchange|convert)\s+([0-9.]+)\s+(.+)\s+(?:for|to|into)\s+(.+)$')
    def exchange(self, event, command, amount, frm, to):
        if not self.currencies:
            self._load_currencies()

        if not self.country_codes:
            self.country_codes = get_country_codes()

        canonical_frm = self._resolve_currency(frm)
        canonical_to = self._resolve_currency(to)
        if not canonical_frm or not canonical_to:
            if command.lower() == "exchange":
                event.addresponse(u"Sorry, I don't know about a currency for %s", (not canonical_frm and frm or to))
            return

        data = {'Amount': amount, 'From': canonical_frm, 'To': canonical_to}
        etree = get_html_parse_tree('http://www.xe.com/ucc/convert.cgi', urlencode(data), self.headers, 'etree')

        result = [tag.text for tag in etree.getiterator('h2')]
        if result:
            event.addresponse(u'%(fresult)s (%(fcountry)s %(fcurrency)s) = %(tresult)s (%(tcountry)s %(tcurrency)s)', {
                'fresult': result[0],
                'tresult': result[2],
                'fcountry': self.currencies[canonical_frm][0][0],
                'fcurrency': self.currencies[canonical_frm][1],
                'tcountry': self.currencies[canonical_to][0][0],
                'tcurrency': self.currencies[canonical_to][1],
            })
        else:
            event.addresponse(u"The bureau de change appears to be closed for lunch")

    @match(r'^(?:currency|currencies)\s+for\s+(?:the\s+)?(.+)$')
    def currency(self, event, place):
        if not self.currencies:
            self._load_currencies()

        search = re.compile(place, re.I)
        results = []
        for code, (place, name) in self.currencies.iteritems():
            if search.search(place):
                results.append(u'%s uses %s (%s)' % (place, name, code))

        if results:
            event.addresponse(u', '.join(results))
        else:
            event.addresponse(u'No currencies found')

help['tld'] = u"Resolve country TLDs (ISO 3166)"
class TLD(Processor):
    u""".<tld>
    tld for <country>"""
    feature = 'tld'

    country_codes = {}

    @match(r'^\.([a-zA-Z]{2})$')
    def tld_to_country(self, event, tld):
        if not self.country_codes:
            self.country_codes = get_country_codes()

        tld = tld.upper()

        if tld in self.country_codes:
            event.addresponse(u'%(tld)s is the TLD for %(country)s', {
                'tld': tld,
                'country': self.country_codes[tld],
            })
        else:
            event.addresponse(u"ISO doesn't know about any such TLD")

    @match(r'^tld\s+for\s+(.+)$')
    def country_to_tld(self, event, location):
        if not self.country_codes:
            self.country_codes = get_country_codes()

        for tld, country in self.country_codes.iteritems():
            if location.lower() in country.lower():
                event.addresponse(u'%(tld)s is the TLD for %(country)s', {
                    'tld': tld,
                    'country': country,
                })
                return

        event.addresponse(u"ISO doesn't know about any TLD for %s", location)

help['weather'] = u'Retrieves current weather and forecasts for cities.'
class Weather(Processor):
    u"""weather in <city>
    forecast for <city>"""

    feature = "weather"

    defaults = {    'ct': 'Cape Town, South Africa',
                    'jhb': 'Johannesburg, South Africa',
                    'joburg': 'Johannesburg, South Africa',
               }
    places = Option('places', 'Alternate names for places', defaults)
    labels = ('temp', 'humidity', 'dew', 'wind', 'pressure', 'conditions', 'visibility', 'uv', 'clouds', 'ymin', 'ymax', 'ycool', 'sunrise', 'sunset', 'moonrise', 'moonset', 'moonphase', 'metar')
    whitespace = re.compile('\s+')

    class WeatherException(Exception):
        pass

    class TooManyPlacesException(WeatherException):
        pass

    def _text(self, string):
        if not isinstance(string, basestring):
            string = ''.join(string.findAll(text=True))
        return self.whitespace.sub(' ', string).strip()

    def _get_page(self, place):
        if place.lower() in self.places:
            place = self.places[place.lower()]

        soup = get_html_parse_tree('http://m.wund.com/cgi-bin/findweather/getForecast?brand=mobile_metric&query=' + quote(place))

        if soup.body.center and soup.body.center.b.string == 'Search not found:':
            raise Weather.WeatherException(u'City not found')

        if soup.table.tr.th and soup.table.tr.th.string == 'Place: Temperature':
            places = []
            for td in soup.table.findAll('td'):
                places.append(td.find('a', href=re.compile('.*html$')).string)
            raise Weather.TooManyPlacesException(places)

        return soup

    def remote_weather(self, place):
        soup = self._get_page(place)
        tds = soup.table.table.findAll('td')

        # HACK: Some cities include a windchill row, but others don't
        if len(tds) == 39:
            del tds[3]
            del tds[4]

        values = {'place': tds[0].findAll('b')[1].string, 'time': tds[0].findAll('b')[0].string}
        for index, td in enumerate(tds[2::2]):
            values[self.labels[index]] = self._text(td)

        return values

    def remote_forecast(self, place):
        soup = self._get_page(place)
        forecasts = []

        for td in soup.findAll('table')[0].findAll('td', align='left'):
            day = td.b.string
            forecast = td.contents[2]
            forecasts.append(u'%s: %s' % (day, self._text(forecast)))

        return forecasts

    @match(r'^weather\s+(?:(?:for|at|in)\s+)?(.+)$')
    def weather(self, event, place):
        try:
            values = self.remote_weather(place)
            event.addresponse(u'In %(place)s at %(time)s: %(temp)s; Humidity: %(humidity)s; Wind: %(wind)s; Conditions: %(conditions)s; Sunrise/set: %(sunrise)s/%(sunset)s; Moonrise/set: %(moonrise)s/%(moonset)s', values)
        except Weather.TooManyPlacesException, e:
            event.addresponse(u'Too many places match %(place)s: %(exception)s', {
                'place': place,
                'exception': u'; '.join(e.args[0]),
            })
        except Weather.WeatherException, e:
            event.addresponse(unicode(e))

    @match(r'^forecast\s+(?:for\s+)?(.+)$')
    def forecast(self, event, place):
        try:
            event.addresponse(u', '.join(self.remote_forecast(place)))
        except Weather.TooManyPlacesException, e:
            event.addresponse(u'Too many places match %(place)s: %(exception)s', {
                'place': place,
                'exception': u'; '.join(e.args[0]),
            })
        except Weather.WeatherException, e:
            event.addresponse(unicode(e))

# vi: set et sta sw=4 ts=4:
