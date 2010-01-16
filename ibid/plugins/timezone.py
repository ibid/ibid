from os.path import exists, join
from datetime import datetime
from os import walk
from dateutil.parser import parse
from dateutil.tz import gettz, tzlocal, tzoffset

from ibid.plugins import Processor, match
from ibid.config import Option, DictOption
from ibid.utils import human_join, format_date, json_webservice
from ibid.compat import defaultdict

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
