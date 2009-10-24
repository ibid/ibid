from urllib2 import urlopen, HTTPError
from urllib import urlencode, quote
from httplib import BadStatusLine
from urlparse import urljoin
from time import time, strptime, strftime
from datetime import datetime
from random import choice, shuffle, randint
from math import acos, sin, cos, radians
import re
from sys import exc_info
import logging

import feedparser

from ibid.compat import defaultdict, dt_strptime, ElementTree
from ibid.config import Option, BoolOption, DictOption
from ibid.plugins import Processor, match, handler
from ibid.utils import ago, decode_htmlentities, get_html_parse_tree, \
        cacheable_download, json_webservice, human_join

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
    u"bash[.org] [(random|<number>)]"

    feature = 'bash'

    public_browse = BoolOption('public_browse', 'Allow random quotes in public', True)

    @match(r'^bash(?:\.org)?(?:\s+(random|\d+))?$')
    def bash(self, event, id):
        id = id is None and u'random' or id.lower()

        if id == u'random' and event.public and not self.public_browse:
            event.addresponse(u'Sorry, not in public. PM me')
            return

        soup = get_html_parse_tree('http://bash.org/?%s' % id)

        if id == "random":
            number = u"".join(soup.find('p', 'quote').find('b').contents)
            event.addresponse(u'%s:', number)

        body = soup.find('p', 'qt')
        if not body:
            event.addresponse(u"There's no such quote, but if you keep talking like that maybe there will be")
        else:
            for line in body.contents:
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
            event.addresponse(u', '.join(u'%s (%s ago)' % (
                    e.title,
                    ago(event.time - dt_strptime(e.updated, '%a, %d %b %Y %H:%M:%S +0000'), 1)
                ) for e in songs['entries']))

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
    u"""fml (<number> | [random] | flop | top | last | love | money | kids | work | health | sex | miscellaneous )"""

    feature = "fml"

    api_url = Option('fml_api_url', 'FML API URL base', 'http://api.betacie.com/')
    api_key = Option('fml_api_key', 'FML API Key (optional)', 'readonly')
    fml_lang = Option('fml_lang', 'FML Lanugage', 'en')

    public_browse = BoolOption('public_browse', 'Allow random quotes in public', True)

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
        f = urlopen(url)
        try:
            tree = ElementTree.parse(f)
        except SyntaxError:
            class_, e, tb = exc_info()
            new_exc = FMLException(u'XML Parsing Error: %s' % unicode(e))
            raise new_exc.__class__, new_exc, tb

        if tree.find('.//error'):
            raise FMLException(tree.findtext('.//error'))

        item = tree.find('.//item')
        if item:
            url = u"http://www.fmylife.com/%s/%s" % (
                item.findtext('category'),
                item.get('id'),
            )
            text = item.find('text').text
            return u'%s - %s' % (text, url)

    @match(r'^(?:fml\s+|http://www\.fmylife\.com/\S+/)(\d+|random|flop|top|last|love|money|kids|work|health|sex|miscellaneous)$')
    def fml(self, event, id):
        try:
            body = self.remote_get(id)
        except (FMLException, HTTPError, BadStatusLine):
            event.addresponse(choice(self.failure_messages) % event.sender)
            return

        if body:
            event.addresponse(body)
        elif id.isdigit():
            event.addresponse(u'No such quote')
        else:
            event.addresponse(choice(self.failure_messages) % event.sender)

    @match(r'^fml$')
    def fml_default(self, event):
        if not event.public or self.public_browse:
            self.fml(event, 'random')
        else:
            event.addresponse(u'Sorry, not in public. PM me')

help["tfln"] = u"Looks up quotes from textsfromlastnight.com"
class TextsFromLastNight(Processor):
    u"""tfln [(random|<number>)]
    tfln (worst|best) [(today|this week|this month)]"""

    feature = 'tfln'

    public_browse = BoolOption('public_browse', 'Allow random quotes in public', True)

    random_pool = []

    def get_tfln(self, section):
        tree = get_html_parse_tree('http://textsfromlastnight.com/%s/' % section.lower())
        for div in tree.findAll('div', attrs={'class': 'post_wrap'}):
            id = int(div.get('id').split('_', 1)[1])
            message = []
            line = ''
            for a in div.findAll('div', attrs={'class': 'post_content'})[0].findAll('a'):
                if a['href'].startswith('/areacode/'):
                    line = u'%s: ' % a.contents[0]
                else:
                    message.append(line + a.contents[0])
            yield id, message

    @match(r'^tfln'
            r'(?:\s+(random|worst|best|\d+))?'
            r'(?:this\s+)?(?:\s+(today|week|month))?$')
    def tfln(self, event, number, timeframe=None):
        number = number is None and u'random' or number.lower()

        if number == u'random' and not timeframe \
                and event.public and not self.public_browse:
            event.addresponse(u'Sorry, not in public. PM me')
            return

        if number in (u'worst', u'best'):
            number += u'-nights'
            if timeframe.lower() in (u'week', u'month'):
                number += u'this-' + timeframe.lower()
        elif number.isdigit():
            number = 'view/%s' % number

        if number == u'random':
            if not self.random_pool:
                self.random_pool = [message for message in self.get_tfln(number)]
                shuffle(self.random_pool)

            message = self.random_pool.pop()
        else:
            try:
                message = self.get_tfln(number).next()
            except StopIteration:
                event.addresponse(u'No such quote')
                return

        id, body = message
        if len(body) > 1:
            for line in body:
                event.addresponse(line)
            event.addresponse(u'- http://textsfromlastnight.com/view/%i', id)
        else:
            event.addresponse(u'%(body)s - http://textsfromlastnight.com/view/%(id)i', {
                'id': id,
                'body': body[0],
            })

    @match(r'^(?:http://)?(?:www\.)?textsfromlastnight\.com/view/(\d+)$')
    def tfln_url(self, event, id):
        self.tfln(event, id)

help["mlia"] = u"Looks up quotes from MyLifeIsAverage.com and MyLifeIsG.com"
class MyLifeIsAverage(Processor):
    u"""mlia [(<number> | random | recent | today | yesterday | this week | this month | this year )]
    mlig [(<number> | random | recent | today | yesterday | this week | this month | this year )]"""

    feature = 'mlia'

    public_browse = BoolOption('public_browse', 'Allow random quotes in public', True)

    random_pool = {}
    pages = {}

    def find_stories(self, url):
        if isinstance(url, basestring):
            tree = get_html_parse_tree(url, treetype='etree')
        else:
            tree = url

        stories = [div for div in tree.findall('.//div') if div.get(u'class') == u's']

        for story in stories:
            body = story.findtext('div').strip()
            id = story.findtext('div/a')
            if isinstance(id, basestring) and id[1:].isdigit():
                id = int(id[1:])
                yield id, body

    @match(r'^(mli[ag])(?:\s+this)?(?:\s+(\d+|random|recent|today|yesterday|week|month|year))?$')
    def mlia(self, event, site, query):
        query = query is None and u'random' or query.lower()

        if query == u'random' and event.public and not self.public_browse:
            event.addresponse(u'Sorry, not in public. PM me')
            return

        site = site.lower()
        url = {
                'mlia': 'http://mylifeisaverage.com/',
                'mlig': 'http://mylifeisg.com/',
            }[site]

        if query == u'random' or query is None:
            if not self.random_pool.get(site):
                tree = get_html_parse_tree(
                        url + 'index.php?' + urlencode({'page': randint(1, self.pages.get(site, 1))}),
                        treetype='etree')
                self.random_pool[site] = [story for story in self.find_stories(tree)]
                shuffle(self.random_pool[site])

                pagination = [div for div in tree.findall('.//div') if div.get(u'class') == u'pagination'][0]
                self.pages[site] = sorted(int(a.text) for a in pagination.findall('.//a') if a.text.isdigit())[-1]

            story = self.random_pool[site].pop()

        else:
            try:
                if query.isdigit():
                    story = self.find_stories(url + 'story.php?' + urlencode({'id': query})).next()
                else:
                    story = self.find_stories(url + 'index.php?' + urlencode({'part': query})).next()

            except StopIteration:
                event.addresponse(u'No such quote')
                return

        id, body = story
        event.addresponse(u'%(body)s - %(url)sstory.php?id=%(id)i', {
            'url': url,
            'id': id,
            'body': body,
        })

    @match(r'^(?:http://)?(?:www\.)?mylifeis(average|g)\.com/story\.php\?id=(\d+)$')
    def mlia_url(self, event, site, id):
        self.mlia(event, 'mli' + site[0].lower(), id)

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
    services = DictOption('services', 'Micro blogging services', default)

    class NoSuchUserException(Exception):
        pass

    def setup(self):
        self.update.im_func.pattern = re.compile(r'^(%s)\s+(\d+)$' % '|'.join(self.services.keys()), re.I)
        self.latest.im_func.pattern = re.compile(r'^(?:latest|last)\s+(%s)\s+(?:update\s+)?(?:(?:by|from|for)\s+)?@?(\S+)$'
                % '|'.join(self.services.keys()), re.I)

    def remote_update(self, service, id):
        status = json_webservice('%sstatuses/show/%s.json' % (service['endpoint'], id))

        return {'screen_name': status['user']['screen_name'], 'text': decode_htmlentities(status['text'])}

    def remote_latest(self, service, user):
        statuses = json_webservice(
                '%sstatuses/user_timeline/%s.json' % (service['endpoint'], user.encode('utf-8')),
                {'count': 1})

        if not statuses:
            raise self.NoSuchUserException(user)

        latest = statuses[0]

        if service['api'] == 'twitter':
            url = '%s%s/status/%i' % (service['endpoint'], latest['user']['screen_name'], latest['id'])
        elif service['api'] == 'laconica':
            url = '%s/notice/%i' % (service['endpoint'].split('/api/', 1)[0], latest['id'])

        return {
            'text': decode_htmlentities(latest['text']),
            'ago': ago(datetime.utcnow() - dt_strptime(latest['created_at'], '%a %b %d %H:%M:%S +0000 %Y')),
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
        except self.NoSuchUserException, e:
                event.addresponse(u'No such %s', service['user'])

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
            event.addresponse(human_join(results))
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
    places = DictOption('places', 'Alternate names for places', defaults)
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
                'exception': human_join(e.args[0], separator=u';'),
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
                'exception': human_join(e.args[0], separator=u';'),
            })
        except Weather.WeatherException, e:
            event.addresponse(unicode(e))

help['distance'] = u"Returns the distance between two places"
class Distance(Processor):
    u"""distance [in <unit>] between <source> and <destination>
    place search for <placename>"""

    # For Mathematics, see:
    # http://www.mathforum.com/library/drmath/view/51711.html
    # http://mathworld.wolfram.com/GreatCircle.html

    feature = 'distance'

    default_unit_names = {
            'km': "kilometres",
            'mi': "miles",
            'nm': "nautical miles"}
    default_radius_values = {
            'km': 6378,
            'mi': 3963.1,
            'nm': 3443.9}

    unit_names = DictOption('unit_names', 'Names of units in which to specify distances', default_unit_names)
    radius_values = DictOption('radius_values', 'Radius of the earth in the units in which to specify distances', default_radius_values)

    def get_place_data(self, place, num):
        return json_webservice('http://ws.geonames.org/searchJSON', {'q': place, 'maxRows': num})

    def get_place(self, place):
        js = self.get_place_data(place, 1)
        if js['totalResultsCount'] == 0:
            return None
        info = js['geonames'][0]
        return {'name': "%s, %s, %s" % (info['name'], info['adminName1'], info['countryName']),
                'lng': radians(info['lng']),
                'lat': radians(info['lat'])}

    @match(r'^(?:(?:search\s+for\s+place)|(?:place\s+search\s+for)|(?:places\s+for))\s+(\S.+?)\s*$')
    def placesearch(self, event, place):
        js = self.get_place_data(place, 10)
        if js['totalResultsCount'] == 0:
            event.addresponse(u"I don't know of anywhere even remotely like '%s'", place)
        else:
            event.addresponse(u"I can find: %s",
                    (human_join([u"%s, %s, %s" % (p['name'], p['adminName1'], p['countryName'])
                        for p in js['geonames'][:10]],
                        separator=u';')))

    @match(r'^(?:how\s*far|distance)(?:\s+in\s+(\S+))?\s+'
            r'(?:(between)|from)' # Between ... and ... | from ... to ...
            r'\s+(\S.+?)\s+(?(2)and|to)\s+(\S.+?)\s*$')
    def distance(self, event, unit, ignore, src, dst):
        unit_names = self.unit_names
        if unit and unit not in self.unit_names:
            event.addresponse(u"I don't know the unit '%(badunit)s'. I know about: %(knownunits)s", {
                'badunit': unit,
                'knownunits':
                    human_join(u"%s (%s)" % (unit, self.unit_names[unit])
                        for unit in self.unit_names),
            })
            return
        if unit:
            unit_names = [unit]

        srcp, dstp = self.get_place(src), self.get_place(dst)
        if not srcp or not dstp:
            event.addresponse(u"I don't know of anywhere called %s",
                    (u" or ".join("'%s'" % place[0]
                        for place in ((src, srcp), (dst, dstp)) if not place[1])))
            return

        dist = acos(cos(srcp['lng']) * cos(dstp['lng']) * cos(srcp['lat']) * cos(dstp['lat']) +
                    cos(srcp['lat']) * sin(srcp['lng']) * cos(dstp['lat']) * sin(dstp['lng']) +
                    sin(srcp['lat'])*sin(dstp['lat']))

        event.addresponse(u"Approximate distance, as the bot flies, between %(srcname)s and %(dstname)s is: %(distance)s", {
            'srcname': srcp['name'],
            'dstname': dstp['name'],
            'distance': human_join([
                u"%.02f %s" % (self.radius_values[unit]*dist, self.unit_names[unit])
                for unit in unit_names],
                conjunction=u'or'),
        })

help['tvshow'] = u'Retrieves TV show information from tvrage.com.'
class TVShow(Processor):
    u"""tvshow <show>"""

    feature = 'tvshow'

    def remote_tvrage(self, show):
        info_url = 'http://services.tvrage.com/tools/quickinfo.php?%s'

        info = urlopen(info_url % urlencode({'show': show.encode('utf-8')}))

        info = info.read()
        info = info.decode('utf-8')
        if info.startswith('No Show Results Were Found'):
            return
        info = info[5:].splitlines()
        show_info = [i.split('@', 1) for i in info]
        show_dict = dict(show_info)

        #check if there are actual airdates for Latest and Next Episode. None for Next
        #Episode does not neccesarily mean it is nor airing, just the date is unconfirmed.
        show_dict = defaultdict(lambda: 'None', show_info)

        for field in ('Latest Episode', 'Next Episode'):
            if field in show_dict:
                ep, name, date = show_dict[field].split('^', 2)
                count = date.count('/')
                format_from = {
                    0: '%Y',
                    1: '%b/%Y',
                    2: '%b/%d/%Y'
                }[count]
                format_to = ' '.join(('%d', '%B', '%Y')[-1 - count:])
                date = strftime(format_to, strptime(date, format_from))
                show_dict[field] = u'%s - "%s" - %s' % (ep, name, date)

        if 'Genres' in show_dict:
            show_dict['Genres'] = human_join(show_dict['Genres'].split(' | '))

        return show_dict

    @match(r'^tv\s*show\s+(.+)$')
    def tvshow(self, event, show):
        retr_info = self.remote_tvrage(show)

        message = u'Show: %(Show Name)s. Premiered: %(Premiered)s. ' \
                    u'Latest Episode: %(Latest Episode)s. Next Episode: %(Next Episode)s. ' \
                    u'Airtime: %(Airtime)s on %(Network)s. Genres: %(Genres)s. ' \
                    u'Status: %(Status)s. %(Show URL)s'

        if not retr_info:
            event.addresponse(u"I can't find anything out about '%s'", show)
            return

        event.addresponse(message, retr_info)

# vi: set et sta sw=4 ts=4:
