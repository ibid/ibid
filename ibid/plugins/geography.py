# Copyright (c) 2009-2010, Jonathan Hitchcock, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from math import acos, sin, cos, radians
from urllib import quote, urlencode
from urlparse import urljoin
import re
import logging
from os.path import exists, join
from datetime import datetime
from os import walk
import csv
from sys import maxint

from dateutil.parser import parse
from dateutil.tz import gettz, tzlocal, tzoffset

from ibid.plugins import Processor, match
from ibid.utils import json_webservice, human_join, format_date, cacheable_download
from ibid.utils.html import get_html_parse_tree
from ibid.config import Option, DictOption, IntOption
from ibid.compat import defaultdict

log = logging.getLogger('plugins.geography')

features = {}

features['distance'] = {
    'description': u'Returns the distance between two places',
    'categories': ('lookup', 'calculate',),
}
class Distance(Processor):
    usage = u"""distance [in <unit>] between <source> and <destination>
    place search for <placename>"""

    # For Mathematics, see:
    # http://www.mathforum.com/library/drmath/view/51711.html
    # http://mathworld.wolfram.com/GreatCircle.html

    features = ('distance',)

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
        return json_webservice('http://ws.geonames.org/searchJSON', {'q': place, 'maxRows': num, 'username': 'ibid'})

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

features['weather'] = {
    'description': u'Retrieves current weather and forecasts for cities.',
    'categories': ('lookup', 'web',),
}
class Weather(Processor):
    usage = u"""weather in <city>
    forecast for <city>"""

    features = ('weather',)

    defaults = {    'ct': 'Cape Town, South Africa',
                    'jhb': 'Johannesburg, South Africa',
                    'joburg': 'Johannesburg, South Africa',
               }
    places = DictOption('places', 'Alternate names for places', defaults)
    labels = {'temperature': 'temp',
              'humidity': 'humidity',
              'dew point': 'dew',
              'wind': 'wind',
              'pressure': 'pressure',
              'conditions': 'conditions',
              'visibility': 'visibility',
              'uv': 'uv',
              'clouds': 'clouds',
              "yesterday's minimum": 'ymin',
              "yesterday's maximum": 'ymax',
              "yesterday's cooling degree days": 'ycool',
              'sunrise': 'sunrise',
              'sunset': 'sunset',
              'moon rise': 'moonrise',
              'moon set': 'moonset',
              'moon phase': 'moonphase',
              'raw metar': 'metar',
             }

    class WeatherException(Exception):
        pass

    class TooManyPlacesException(WeatherException):
        pass

    def _text(self, string):
        if not isinstance(string, basestring):
            string = ''.join(string.findAll(text=True))
        return re.sub('\s+', ' ', string).strip()

    def _get_page(self, place):
        if place.lower() in self.places:
            place = self.places[place.lower()]

        soup = get_html_parse_tree(
                    'http://m.wund.com/cgi-bin/findweather/getForecast?'
                    + urlencode({'brand': 'mobile_metric',
                                 'query': place.encode('utf-8')}))

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
        tds = soup.findAll('td')

        values = {}
        for index, td in enumerate(tds):
            text = self._text(td).lower()
            if text.startswith('updated:'):
                values['place'] = td.findAll('b')[1].string
                values['time'] = td.findAll('b')[0].string
            if text in self.labels:
                values[self.labels[text]] = self._text(tds[index+1])

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

    @match(r'^weather (?:(?:for|at|in) )?(.+)$')
    def weather(self, event, place):
        # The regex also matches "weather forecast..." which forecast should
        # process. So ignore it when this happens
        if place.lower().startswith('forecast'):
            return

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

    @match(r'^(?:weather )?forecast (?:for )?(.+)$')
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

class TimezoneException(Exception):
    pass

MONTH_SHORT = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MONTH_LONG = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
OTHER_STUFF = ('am', 'pm', 'st', 'nd', 'rd', 'th')

CUSTOM_ZONES = {
    'PST': 'US/Pacific',
    'MST': 'US/Mountain',
    'CST': 'US/Central',
    'EST': 'US/Eastern',
}

features['timezone'] = {
    'description': 'Converts times between timezones.',
    'categories': ('convert',),
}
class TimeZone(Processor):
    usage = u"""when is <time> <place|timezone> in <place|timezone>
    time in <place|timezone>"""
    features = ('timezone',)

    zoneinfo = Option('zoneinfo', 'Timezone info directory', '/usr/share/zoneinfo')
    custom_zones = DictOption('timezones', 'Custom timezone names', CUSTOM_ZONES)

    countries = {}
    timezones = {}
    lowerzones = {}

    def setup(self):
        iso3166 = join(self.zoneinfo, 'iso3166.tab')
        if exists(iso3166):
            self.countries = {}
            for line in open(iso3166).readlines():
                if not line.startswith('#'):
                    code, name = line.strip().split('\t')
                    self.countries[code] = name

        zones = join(self.zoneinfo, 'zone.tab')
        if exists(zones):
            self.timezones = defaultdict(list)
            for line in open(zones).readlines():
                if not line.startswith('#'):
                    code, coordinates, zone = line.strip().split('\t', 2)
                    if '\t' in zone:
                        zone, comment = zone.split('\t')
                    self.timezones[code].append(zone)

        self.lowerzones = {}
        for path, directories, filenames in walk(self.zoneinfo):
            if path.replace(self.zoneinfo, '').lstrip('/').split('/')[0] not in ('posix', 'right'):
                for filename in filenames:
                    name = join(path, filename).replace(self.zoneinfo, '').lstrip('/')
                    self.lowerzones[name.lower().replace('etc/', '')] = name

    def _find_timezone(self, string):
        for name, zonename in self.custom_zones.items():
            if string.lower() == name.lower():
                return gettz(zonename)

        zone = gettz(string)
        if zone:
            return zone

        zone = gettz(string.upper())
        if zone:
            return zone

        if string.lower() in self.lowerzones:
            return gettz(self.lowerzones[string.lower()])

        ccode = None
        for code, name in self.countries.items():
            if name.lower() == string.lower():
                ccode = code
        if not ccode:
            if string.replace('.', '').upper() in self.timezones:
                ccode = string.replace('.', '').upper()

        if ccode:
            if len(self.timezones[ccode]) == 1:
                return gettz(self.timezones[ccode][0])
            else:
                raise TimezoneException(u'%s has multiple timezones: %s' % (self.countries[ccode], human_join(self.timezones[ccode])))

        possibles = []
        for zones in self.timezones.values():
            for name in zones:
                if string.replace(' ', '_').lower() in [part.lower() for part in name.split('/')]:
                    possibles.append(name)

        if len(possibles) == 1:
            return gettz(possibles[0])
        elif len(possibles) > 1:
            raise TimezoneException(u'Multiple timezones found: %s' % (human_join(possibles)))

        zone = self._geonames_lookup(string)
        if zone:
            return zone

        raise TimezoneException(u"I don't know about the %s timezone" % (string,))

    def _geonames_lookup(self, place):
        search = json_webservice('http://ws.geonames.org/searchJSON', {'q': place, 'maxRows': 1, 'username': 'ibid'})
        if search['totalResultsCount'] == 0:
            return None

        city = search['geonames'][0]
        timezone = json_webservice('http://ws.geonames.org/timezoneJSON', {'lat': city['lat'], 'lng': city['lng'], 'username': 'ibid'})

        if 'timezoneId' in timezone:
            return gettz(timezone['timezoneId'])

        if 'rawOffset' in timezone:
            offset = timezone['rawOffset']
            return tzoffset('UTC%s%s' % (offset>=0 and '+' or '', offset), offset*3600)

    @match(r'^when\s+is\s+((?:[0-9.:/hT -]|%s)+)(?:\s+in)?(?:\s+(.+))?\s+in\s+(.+)$' % '|'.join(MONTH_SHORT+MONTH_LONG+OTHER_STUFF), simple=False)
    def convert(self, event, time, from_, to):
        try:
            source = time and parse(time) or datetime.now()
        except ValueError:
            event.addresponse(u"That's not a real time")
            return

        try:
            if from_:
                from_zone = self._find_timezone(from_)
            else:
                from_zone = tzlocal()

            to_zone = self._find_timezone(to)
        except TimezoneException, e:
            event.addresponse(unicode(e))
            return

        source = source.replace(tzinfo=from_zone)
        result = source.astimezone(to_zone)

        event.addresponse(time and u'%(source)s is %(destination)s' or 'It is %(destination)s', {
            'source': format_date(source, tolocaltime=False),
            'destination': format_date(result, tolocaltime=False),
        })

    @match(r"^(?:(?:what(?:'?s|\s+is)\s+the\s+)?time\s+in|what\s+time\s+is\s+it\s+in)\s+(.+)$")
    def time(self, event, place):
        self.convert(event, None, None, place)

features['flight'] = {
    'description': u'Search for flights on travelocity',
    'categories': ('lookup', 'web',),
}
class Flight:
    def __init__(self):
        self.flight, self.depart_time, self.depart_ap, self.arrive_time, \
                self.arrive_ap, self.duration, self.stops, self.price = \
                [], None, None, None, None, None, None, None

    def int_price(self):
        try:
            return int(self.price[1:])
        except ValueError:
            return maxint

    def int_duration(self):
        hours, minutes = 0, 0
        match = re.search(r'(\d+)hr', self.duration)
        if match:
            hours = int(match.group(1))
        match = re.search(r'(\d+)min', self.duration)
        if match:
            minutes = int(match.group(1))
        return int(hours)*60 + int(minutes)

MONTH_SHORT = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MONTH_LONG = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
OTHER_STUFF = ('am', 'pm', 'st', 'nd', 'rd', 'th', 'morning', 'afternoon', 'evening', 'anytime')
DATE = r'(?:[0-9.:/hT -]|%s)+' % '|'.join(MONTH_SHORT+MONTH_LONG+OTHER_STUFF)

class FlightException(Exception):
    pass

class FlightSearch(Processor):
    usage = u"""airport [in] <name|location|code>
    [<cheapest|quickest>] flight from <departure> to <destination> from <depart_date> [anytime|morning|afternoon|evening|<time>] to <return_date> [anytime|morning|afternoon|evening|<time>]"""

    features = ('flight',)

    airports_url = u'http://openflights.svn.sourceforge.net/viewvc/openflights/openflights/data/airports.dat'
    max_results = IntOption('max_results', 'Maximum number of results to list', 5)

    airports = {}

    def read_airport_data(self):
        # File is listed as ISO 8859-1 (Latin-1) encoded on
        # http://openflights.org/data.html, but from decoding it appears to
        # actually be UTF8
        filename = cacheable_download(self.airports_url, u'flight/airports.dat')
        reader = csv.reader(open(filename), delimiter=',', quotechar='"')
        for row in reader:
            self.airports[int(row[0])] = [unicode(r, u'utf-8') for r in row[1:]]

    def _airport_search(self, query, search_loc = True):
        if not self.airports:
            self.read_airport_data()
        if search_loc:
            ids = self._airport_search(query, False)
            if len(ids) == 1:
                return ids
            query = [q for q in query.lower().split()]
        else:
            query = [query.lower()]
        ids = []
        for id, airport in self.airports.items():
            if search_loc:
                data = (u' '.join(c.lower() for c in airport[:5])).split()
            elif len(query[0]) == 3:
                data = [airport[3].lower()]
            else: # assume length 4 (won't break if not)
                data = [airport[4].lower()]
            if len(filter(lambda q: q in data, query)) == len(query):
                ids.append(id)
        return ids

    def repr_airport(self, id):
        airport = self.airports[id]
        code = u''
        if airport[3] or airport[4]:
            code = u' (%s)' % u'/'.join(filter(lambda c: c, airport[3:5]))
        return u'%s%s' % (airport[0], code)

    @match(r'^airports?\s+((?:in|for)\s+)?(.+)$')
    def airport_search(self, event, search_loc, query):
        search_loc = search_loc is not None
        if not search_loc and not 3 <= len(query) <= 4:
            event.addresponse(u'Airport code must be 3 or 4 characters')
            return
        ids = self._airport_search(query, search_loc)
        if len(ids) == 0:
            event.addresponse(u"Sorry, I don't know that airport")
        elif len(ids) == 1:
            id = ids[0]
            airport = self.airports[id]
            code = u'unknown code'
            if airport[3] and airport[4]:
                code = u'codes %s and %s' % (airport[3], airport[4])
            elif airport[3]:
                code = u'code %s' % airport[3]
            elif airport[4]:
                code = u'code %s' % airport[4]
            event.addresponse(u'%(airport)s in %(city)s, %(country)s has %(code)s', {
                u'airport': airport[0],
                u'city': airport[1],
                u'country': airport[2],
                u'code': code,
            })
        else:
            event.addresponse(u'Found the following airports: %s', human_join(self.repr_airport(id) for id in ids)[:480])

    def _flight_search(self, event, dpt, to, dep_date, ret_date):
        airport_dpt = self._airport_search(dpt)
        airport_to = self._airport_search(to)
        if len(airport_dpt) == 0:
            event.addresponse(u"Sorry, I don't know the airport you want to leave from")
            return
        if len(airport_to) == 0:
            event.addresponse(u"Sorry, I don't know the airport you want to fly to")
            return
        if len(airport_dpt) > 1:
            event.addresponse(u'The following airports match the departure: %s', human_join(self.repr_airport(id) for id in airport_dpt)[:480])
            return
        if len(airport_to) > 1:
            event.addresponse(u'The following airports match the destination: %s', human_join(self.repr_airport(id) for id in airport_to)[:480])
            return

        dpt = airport_dpt[0]
        to = airport_to[0]

        def to_travelocity_date(date):
            date = date.lower()
            time = None
            for period in [u'anytime', u'morning', u'afternoon', u'evening']:
                if period in date:
                    time = period.title()
                    date = date.replace(period, u'')
                    break
            try:
                date = parse(date)
            except ValueError:
                raise FlightException(u"Sorry, I can't understand the date %s" % date)
            if time is None:
                if date.hour == 0 and date.minute == 0:
                    time = u'Anytime'
                else:
                    time = date.strftime('%I:00')
                    if time[0] == u'0':
                        time = time[1:]
                    if date.hour < 12:
                        time += u'am'
                    else:
                        time += u'pm'
            date = date.strftime('%m/%d/%Y')
            return (date, time)

        (dep_date, dep_time) = to_travelocity_date(dep_date)
        (ret_date, ret_time) = to_travelocity_date(ret_date)

        params = {}
        params[u'leavingFrom'] = self.airports[dpt][3]
        params[u'goingTo'] = self.airports[to][3]
        params[u'leavingDate'] = dep_date
        params[u'dateLeavingTime'] = dep_time
        params[u'returningDate'] = ret_date
        params[u'dateReturningTime'] = ret_time
        etree = get_html_parse_tree('http://travel.travelocity.com/flights/InitialSearch.do', data=urlencode(params), treetype='etree')
        while True:
            script = [script for script in etree.getiterator(u'script')][1]
            matches = script.text and re.search(r'var finurl = "(.*)"', script.text)
            if matches:
                url = u'http://travel.travelocity.com/flights/%s' % matches.group(1)
                etree = get_html_parse_tree(url, treetype=u'etree')
            else:
                break

        # Handle error
        div = [d for d in etree.getiterator(u'div') if d.get(u'class') == u'e_content']
        if len(div):
            error = div[0].find(u'h3').text
            raise FlightException(error)

        departing_flights = self._parse_travelocity(etree)
        return_url = None
        table = [t for t in etree.getiterator(u'table') if t.get(u'id') == u'tfGrid'][0]
        for tr in table.getiterator(u'tr'):
            for td in tr.getiterator(u'td'):
                if td.get(u'class').strip() in [u'tfPrice', u'tfPriceOrButton']:
                    onclick = td.find(u'div/button').get(u'onclick')
                    match = re.search(r"location.href='\.\./flights/(.+)'", onclick)
                    url_page = match.group(1)
                    match = re.search(r'^(.*?)[^/]*$', url)
                    url_base = match.group(1)
                    return_url = url_base + url_page

        etree = get_html_parse_tree(return_url, treetype=u'etree')
        returning_flights = self._parse_travelocity(etree)

        return (departing_flights, returning_flights, url)

    def _parse_travelocity(self, etree):
        flights = []
        table = [t for t in etree.getiterator(u'table') if t.get(u'id') == u'tfGrid'][0]
        trs = [t for t in table.getiterator(u'tr')]
        tr_index = 1
        while tr_index < len(trs):
            tds = []
            while True:
                new_tds = [t for t in trs[tr_index].getiterator(u'td')]
                tds.extend(new_tds)
                tr_index += 1
                if len(filter(lambda t: t.get(u'class').strip() == u'tfAirlineSeatsMR', new_tds)):
                    break
            flight = Flight()
            for td in tds:
                if td.get(u'class').strip() == u'tfAirline':
                    anchor = td.find(u'a')
                    if anchor is not None:
                        airline = anchor.text.strip()
                    else:
                        airline = td.text.split(u'\n')[0].strip()
                    flight.flight.append(u'%s %s' % (airline, td.findtext(u'div').strip()))
                if td.get(u'class').strip() == u'tfDepart' and td.text:
                    flight.depart_time = td.text.split(u'\n')[0].strip()
                    flight.depart_ap = u'%s %s' % (td.findtext(u'div').strip(),
                            td.findtext(u'div/span').strip())
                if td.get(u'class').strip() == u'tfArrive' and td.text:
                    flight.arrive_time = td.text.split(u'\n')[0].strip()
                    span = td.find(u'span')
                    if span is not None and span.get(u'class').strip() == u'tfNextDayDate':
                        flight.arrive_time = u'%s %s' % (flight.arrive_time, span.text.strip()[2:])
                        span = [s for s in td.find(u'div').getiterator(u'span')][1]
                        flight.arrive_ap = u'%s %s' % (td.findtext(u'div').strip(),
                                span.text.strip())
                    else:
                        flight.arrive_ap = u'%s %s' % (td.findtext(u'div').strip(),
                                td.findtext(u'div/span').strip())
                if td.get(u'class').strip() == u'tfTime' and td.text:
                    flight.duration = td.text.strip()
                    flight.stops = td.findtext(u'span/a').strip()
                if td.get(u'class').strip() in [u'tfPrice', u'tfPriceOr'] and td.text:
                    flight.price = td.text.strip()
            flight.flight = human_join(flight.flight)
            flights.append(flight)

        return flights

    @match(r'^(?:(cheapest|quickest)\s+)?flights?\s+from\s+(.+)\s+to\s+(.+)\s+from\s+(%s)\s+to\s+(%s)$' % (DATE, DATE), simple=False)
    def flight_search(self, event, priority, dpt, to, dep_date, ret_date):
        try:
            flights = self._flight_search(event, dpt, to, dep_date, ret_date)
        except FlightException, e:
            event.addresponse(unicode(e))
            return
        if flights is None:
            return
        if len(flights[0]) == 0:
            event.addresponse(u'No matching departure flights found')
            return
        if len(flights[1]) == 0:
            event.addresponse(u'No matching return flights found')
            return

        cmp = None
        if priority is not None:
            priority = priority.lower()
        if priority == u'cheapest':
            cmp = lambda a, b: a.int_price() < b.int_price()
        elif priority == u'quickest':
            cmp = lambda a, b: a.int_duration() < b.int_duration()
        if cmp:
            # select best flight based on priority
            for i in xrange(2):
                flights[i].sort(cmp=cmp)
                del flights[i][1:]
        response = []
        for i, flight_type in zip(xrange(2), [u'Departing', u'Returning']):
            if len(flights[i]) > 1:
                response.append(u'%s flights:' % flight_type)
            for flight in flights[i][:self.max_results]:
                leading = u''
                if len(flights[i]) == 1:
                    leading = u'%s flight: ' % flight_type
                response.append(u'%(leading)s%(flight)s departing %(depart_time)s from %(depart_airport)s, arriving %(arrive_time)s at %(arrive_airport)s (flight time %(duration)s, %(stops)s) costs %(price)s per person' % {
                    'leading': leading,
                    'flight': flight.flight,
                    'depart_time': flight.depart_time,
                    'depart_airport': flight.depart_ap,
                    'arrive_time': flight.arrive_time,
                    'arrive_airport': flight.arrive_ap,
                    'duration': flight.duration,
                    'stops': flight.stops,
                    'price': flight.price or 'unknown'
                })
        response.append(u'Full results: %s' % flights[2])
        event.addresponse(u'\n'.join(response), conflate=False)

# vi: set et sta sw=4 ts=4:
