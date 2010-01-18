from math import acos, sin, cos, radians
from urllib import quote
from urlparse import urljoin
import re
import logging
from os.path import exists, join
from datetime import datetime
from os import walk
from dateutil.parser import parse
from dateutil.tz import gettz, tzlocal, tzoffset

from ibid.plugins import Processor, match
from ibid.utils import json_webservice, human_join, format_date
from ibid.utils.html import get_html_parse_tree
from ibid.config import Option, DictOption
from ibid.compat import defaultdict

log = logging.getLogger('plugins.geography')

help = {}

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

help['timezone'] = "Converts times between timezones."
class TimeZone(Processor):
    u"""when is <time> <place|timezone> in <place|timezone>
    time in <place|timezone>"""
    feature = 'timezone'

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

        lowerzones = {}
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
        search = json_webservice('http://ws.geonames.org/searchJSON', {'q': place, 'maxRows': 1})
        if search['totalResultsCount'] == 0:
            return None

        city = search['geonames'][0]
        timezone = json_webservice('http://ws.geonames.org/timezoneJSON', {'lat': city['lat'], 'lng': city['lng']})

        if 'timezoneId' in timezone:
            return gettz(timezone['timezoneId'])

        if 'rawOffset' in timezone:
            offset = timezone['rawOffset']
            return tzoffset('UTC%s%s' % (offset>=0 and '+' or '', offset), offset*3600)

    @match(r'^when\s+is\s+((?:[0-9.:/hT -]|%s)+)(?:\s+in)?(?:\s+(.+))?\s+in\s+(.+)$' % '|'.join(MONTH_SHORT+MONTH_LONG+OTHER_STUFF))
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

# vi: set et sta sw=4 ts=4:
