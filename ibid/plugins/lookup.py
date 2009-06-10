from urllib2 import urlopen, HTTPError
from urllib import urlencode, quote
from httplib import BadStatusLine
from urlparse import urljoin
from time import time, strptime, strftime
from datetime import datetime
from random import choice
from simplejson import loads
from xml.etree.cElementTree import parse
import re
import logging

import feedparser

from ibid.plugins import Processor, match, handler
from ibid.config import Option
from ibid.utils import ago, decode_htmlentities, get_html_parse_tree, cacheable_download

log = logging.getLogger('plugins.lookup')

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
                line = unicode(line).strip()
                if line != u'<br />':
                    event.addresponse(line)

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
class FMLException(Exception):
    pass

class FMyLife(Processor):
    u"""fml (<number> | [random] | <category> | flop | top | last)
    fml categories"""

    feature = "fml"

    api_url = Option('fml_api_url', 'FML API URL base', 'http://api.betacie.com/')
    api_key = Option('fml_api_key', 'FML API Key (optional)', 'readonly')
    fml_lang = Option('fml_lang', 'FML Lanugage', 'en')

    failure_messages = (
            u'Today, I tried to get a quote for %(nick)s but failed. FML',
            u'Today, FML is down. FML',
            u"Sorry, it's broken, the FML admins must having a really bad day",
    )

    def remote_get(self, id):
        url = urljoin(self.api_url, 'view/%s?%s' % (
            id.isalnum() and id + '/nocomment' or quote(id),
            urlencode({'language': self.fml_lang, 'key': self.api_key}))
        )
        tree = parse(urlopen(url))

        if tree.find('.//error'):
            raise FMLException(tree.findtext('.//error'))

        item = tree.find('.//item')
        if item:
            url = u"http://www.fmylife.com/%s/%s" % (
                item.findtext('category'),
                item.get('id'),
            )
            text = item.find('text').text

            return u'%s : %s' % (url, text)

    def setup(self):
        url = urljoin(self.api_url, 'view/categories?' + urlencode({'language': self.fml_lang, 'key': self.api_key}))
        tree = parse(urlopen(url))
        self.categories = [x.get('code') for x in tree.findall('.//categorie')]

        self.fml.im_func.pattern = re.compile(r'^(?:fml\s+|http://www\.fmylife\.com/\S+/)(\d+|random|flop|top|last|%s)$' % (
            '|'.join(self.categories),
        ), re.I)

    @handler
    def fml(self, event, id):
        try:
            quote = self.remote_get(id)
        except FMLException:
            event.addresponse(choice(self.failure_messages) % event.sender)
            return
        except HTTPError:
            event.addresponse(choice(self.failure_messages) % event.sender)
            return
        except BadStatusLine:
            event.addresponse(choice(self.failure_messages) % event.sender)
            return

        if quote:
            event.addresponse(quote)
        else:
            event.addresponse(u'No such quote')

    @match(r'^fml$')
    def fml_default(self, event):
        try:
            event.addresponse(self.remote_get('random'))
        except FMLException:
            event.addresponse(choice(self.failure_messages) % event.sender)
        except HTTPError:
            event.addresponse(choice(self.failure_messages) % event.sender)
        except BadStatusLine:
            event.addresponse(choice(self.failure_messages) % event.sender)

    @match(r'^fml\s+categories$')
    def list_categories(self, event):
        event.addresponse(u'Categories: %s', u', '.join(self.categories))

help["microblog"] = u"Looks up messages on microblogging services like twitter and identica."
class Twitter(Processor):
    u"""latest (tweet|identica) from <name>
    (tweet|identica) <number>"""

    feature = "microblog"

    default = {
        'twitter':   {'endpoint': 'http://twitter.com/',   'api': 'twitter',  'name': 'tweet', 'user': 'twit'},
        'tweet':     {'endpoint': 'http://twitter.com/',   'api': 'twitter',  'name': 'tweet', 'user': 'twit'},
        'identica':  {'endpoint': 'http://identi.ca/api/', 'api': 'laconica', 'name': 'dent',  'user': 'denter'},
        'identi.ca': {'endpoint': 'http://identi.ca/api/', 'api': 'laconica', 'name': 'dent',  'user': 'denter'},
        'dent':      {'endpoint': 'http://identi.ca/api/', 'api': 'laconica', 'name': 'dent',  'user': 'denter'},
    }
    services = Option('services', 'Micro blogging services', default)

    def setup(self):
        self.update.im_func.pattern = re.compile(r'^(%s)\s+(\d+)$' % '|'.join(self.services.keys()), re.I)
        self.latest.im_func.pattern = re.compile(r'^(?:latest|last)\s+(%s)\s+(?:update\s+)?(?:(?:by|from|for)\s+)?(\S+)$'
                % '|'.join(self.services.keys()), re.I)

    def remote_update(self, service, id):
        f = urlopen('%sstatuses/show/%s.json' % (service['endpoint'], id))
        status = loads(f.read())
        f.close()

        return {'screen_name': status['user']['screen_name'], 'text': decode_htmlentities(status['text'])}

    def remote_latest(self, service, user):
        f = urlopen('%sstatuses/user_timeline/%s.json?count=1' % (service['endpoint'], user))
        statuses = loads(f.read())
        f.close()
        latest = statuses[0]

        if service['api'] == 'twitter':
            url = '%s%s/status/%i' % (service['endpoint'], latest['user']['screen_name'], latest['id'])
        elif service['api'] == 'laconica':
            url = '%s/notice/%i' % (service['endpoint'].split('/api/', 1)[0], latest['id'])

        return {
            'text': decode_htmlentities(latest['text']),
            'ago': ago(datetime.utcnow() - datetime.strptime(latest['created_at'], '%a %b %d %H:%M:%S +0000 %Y'), 1),
            'url': url,
        }

    @handler
    def update(self, event, service_name, id):
        service = self.services[service_name.lower()]
        try:
            event.addresponse(u'%(screen_name)s: "%(text)s"', self.remote_update(service, int(id)))
        except HTTPError, e:
            if e.code in (401, 403):
                event.addresponse(u'That %s is private', service['name'])
            elif e.code == 404:
                event.addresponse(u'No such %s', service['name'])
            else:
                event.addresponse(u'I can only see the Fail Whale')

    @handler
    def latest(self, event, service_name, user):
        service = self.services[service_name.lower()]
        try:
            event.addresponse(u'"%(text)s" %(ago)s ago, %(url)s', self.remote_latest(service, user))
        except HTTPError, e:
            if e.code in (401, 403):
                event.addresponse(u"Sorry, %s's feed is private", user)
            elif e.code == 404:
                event.addresponse(u'No such %s', service['user'])
            else:
                event.addresponse(u'I can only see the Fail Whale')

    @match(r'^https?://(?:www\.)?twitter\.com/[^/ ]+/statuse?s?/(\d+)$')
    def twitter(self, event, id):
        self.update(event, u'twitter', id)

    @match(r'^https?://(?:www\.)?identi.ca/notice/(\d+)$')
    def identica(self, event, id):
        self.update(event, u'identica', id)

help['currency'] = u'Converts amounts between currencies.'
class Currency(Processor):
    u"""exchange <amount> <currency> for <currency>
    currencies for <country>"""

    feature = "currency"

    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.xe.com/'}
    currencies = {}
    country_codes = {}

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

    strip_currency_re = re.compile(r'^[\.\s]*([\w\s]+?)s?$', re.UNICODE)

    def _resolve_currency(self, name, rough=True):
        "Return the canonical name for a currency"

        if name.upper() in self.currencies:
            return name.upper()

        m = self.strip_currency_re.match(name)
        
        if m is None:
            return False

        name = m.group(1).lower()

        # TLD -> country name
        if rough and len(name) == 2 and name.upper() in self.country_codes:
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

        rough = command.lower() == 'exchange'

        canonical_frm = self._resolve_currency(frm, rough)
        canonical_to = self._resolve_currency(to, rough)
        if not canonical_frm or not canonical_to:
            if rough:
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
        for code, (places, name) in self.currencies.iteritems():
            for place in places:
                if search.search(place):
                    results.append(u'%s uses %s (%s)' % (place, name, code))
                    break

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

            # Cities with more than one airport give duplicate entries. We can take the first
            if len([x for x in places if x == places[0]]) == len(places):
                url = urljoin('http://m.wund.com/cgi-bin/findweather/getForecast',
                        soup.table.find('td').find('a', href=re.compile('.*html$'))['href'])
                soup = get_html_parse_tree(url)
            else:
                raise Weather.TooManyPlacesException(places)

        return soup

    def remote_weather(self, place):
        soup = self._get_page(place)
        tds = [x.table for x in soup.findAll('table') if x.table][0].findAll('td')

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
        table = [table for table in soup.findAll('table') if table.findAll('td', align='left')][0]

        for td in table.findAll('td', align='left'):
            day = td.b.string
            forecast = u' '.join([self._text(line) for line in td.contents[2:]])
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

help['tvshow'] = u'Retrieves TV show information from tvrage.com.'
class TVShow(Processor):
    u"""tvshow <show>"""

    feature = "tvshow"
        
    def remote_tvrage(self, show):
        info_url = "http://services.tvrage.com/tools/quickinfo.php?%s"
        
        try:
            info = urlopen(info_url % urlencode({'show': show}))
        except Exception, e:
            return
        
        info = info.read().decode("ISO-8859-1")
        info = info[5:].splitlines()        
        show_info = [i.split('@', 1) for i in info]
        show_dict = dict(show_info)

        if show_dict.has_key("Next Episode") and show_dict.has_key("Latest Episode"): #Show is airing.
            next_ep, next_name, next_date = show_dict["Next Episode"].split("^")
            next_date = strftime("%d %B %Y", strptime(next_date, "%b/%d/%Y"))
            show_dict["Next Episode"] = '%s - "%s" - %s' %(next_ep, next_name, next_date)

            prev_ep, prev_name, prev_date = show_dict["Latest Episode"].split("^")
            prev_date = strftime("%d %B %Y", strptime(prev_date, "%b/%d/%Y"))
            show_dict["Latest Episode"] = '%s - "%s" - %s' %(prev_ep, prev_name, prev_date)
        elif show_dict.has_key("Next Episode"): #Show is premiering.
            show_dict["Latest Episode"] = "None"

            next_ep, next_name, next_date = show_dict["Next Episode"].split("^")
            next_date = strftime("%d %B %Y", strptime(next_date, "%b/%d/%Y"))
            show_dict["Next Episode"] = '%s - "%s" - %s' %(next_ep, next_name, next_date)
        else: #Show has ended.
            prev_ep, prev_name, prev_date = show_dict["Latest Episode"].split("^")
            prev_date = strftime("%d %B %Y", strptime(prev_date, "%b/%d/%Y"))
            show_dict["Latest Episode"] = '%s - "%s" - %s' %(prev_ep, prev_name, prev_date)

            show_dict["Next Episode"] = "None"

        return show_dict
    
    @match(r"""^tvshow\s+([\w-+=*()"!#$':; ,<>?.\\]+)$""")
    def tvshow(self, event, show):
        s = self.remote_tvrage(show)
        if not s:
            event.addresponse(u"I'm sorry, but I was unable to retrieve the info.")
            return
        
        message = u"Show: %(Show Name)s. Genres: %(Genres)s. " \
                    u"Premiered: %(Premiered)s. Latest Episode: %(Latest Episode)s. " \
                    u"Next Episode: %(Next Episode)s. Airtime: %(Airtime)s on %(Network)s. " \
                    u"Status: %(Status)s. URL: %(Show URL)s."
                    
        event.addresponse(message %s)

# vi: set et sta sw=4 ts=4:
