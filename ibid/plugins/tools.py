import re
from random import random, randint
from subprocess import Popen, PIPE
from datetime import datetime
from os.path import exists, join

from dateutil.parser import parse
from dateutil.tz import gettz, tzutc, tzlocal, tzoffset

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output, human_join, format_date, json_webservice
from ibid.compat import defaultdict

help = {}

help['retest'] = u'Checks whether a regular expression matches a given string.'
class ReTest(Processor):
    u"""does <pattern> match <string>"""
    feature = 'retest'

    @match('^does\s+(.+?)\s+match\s+(.+?)$')
    def retest(self, event, regex, string):
        event.addresponse(re.search(regex, string) and u'Yes' or u'No')

help['random'] = u'Generates random numbers.'
class Random(Processor):
    u"""random [ <max> | <min> <max> ]"""
    feature = 'random'

    @match('^rand(?:om)?(?:\s+(\d+)(?:\s+(\d+))?)?$')
    def random(self, event, begin, end):
        if not begin and not end:
            event.addresponse(u'I always liked %f', random())
        else:
            begin = int(begin)
            end = end and int(end) or 0
            event.addresponse(u'I always liked %i', randint(min(begin,end), max(begin,end)))

help['units'] = 'Converts values between various units.'
class Units(Processor):
    u"""convert [<value>] <unit> to <unit>"""
    feature = 'units'
    priority = 10

    units = Option('units', 'Path to units executable', 'units')

    temp_scale_names = {
        'fahrenheit': 'tempF',
        'f': 'tempF',
        'celsius': 'tempC',
        'celcius': 'tempC',
        'c': 'tempC',
        'kelvin': 'tempK',
        'k': 'tempK',
        'rankine': 'tempR',
        'r': 'tempR',
    }

    temp_function_names = set(temp_scale_names.values())

    def setup(self):
        if not file_in_path(self.units):
            raise Exception("Cannot locate units executable")

    def format_temperature(self, unit):
        "Return the unit, and convert to 'tempX' format if a known temperature scale"

        lunit = unit.lower()
        if lunit in self.temp_scale_names:
            unit = self.temp_scale_names[lunit]
        elif lunit.startswith("deg") and " " in lunit and lunit.split(None, 1)[1] in self.temp_scale_names:
            unit = self.temp_scale_names[lunit.split(None, 1)[1]]
        return unit

    @match(r'^convert\s+(-?[0-9.]+)?\s*(.+)\s+(?:in)?to\s+(.+)$')
    def convert(self, event, value, frm, to):

        # We have to special-case temperatures because GNU units uses function notation
        # for direct temperature conversions
        if self.format_temperature(frm) in self.temp_function_names \
                and self.format_temperature(to) in self.temp_function_names:
            frm = self.format_temperature(frm)
            to = self.format_temperature(to)

        if value is not None:
            if frm in self.temp_function_names:
                frm = "%s(%s)" % (frm, value)
            else:
                frm = '%s %s' % (value, frm)

        units = Popen([self.units, '--verbose', '--', frm, to], stdout=PIPE, stderr=PIPE)
        output, error = units.communicate()
        code = units.wait()

        output = unicode_output(output)
        result = output.splitlines()[0].strip()

        if code == 0:
            event.addresponse(result)
        elif code == 1:
            if result == "conformability error":
                event.addresponse(u"I don't think %(from)s can be converted to %(to)s", {
                    'from': frm,
                    'to': to,
                })
            elif result.startswith("conformability error"):
                event.addresponse(u"I don't think %(from)s can be converted to %(to)s: %(error)s", {
                    'from': frm,
                    'to': to,
                    'error': result.split(":", 1)[1],
                })
            else:
                event.addresponse(u"I can't do that: %s", result)

class TimezoneException(Exception):
    pass

MONTH_SHORT = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MONTH_LONG = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
OTHER_STUFF = ('am', 'pm', 'st', 'nd', 'rd', 'th')

help['timezone'] = "Converts times between timezones."
class TimeZone(Processor):
    u"""when is <time> <place|timezone> in <place|timezone>
    time in <place|timezone>"""
    feature = 'timezone'

    zoneinfo = Option('zoneinfo', 'Timezone info directory', '/usr/share/zoneinfo')

    countries = {}
    timezones = {}

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

    def _find_timezone(self, string):
        ccode = None

        if string.upper() in ('GMT', 'UTC', 'UCT', 'ZULU'):
            string = 'UTC'
        zone = gettz(string)

        if not zone:
            for code, name in self.countries.items():
                if name.lower() == string.lower():
                    ccode = code
            if not ccode:
                if string.replace('.', '').upper() in self.timezones:
                    ccode = string.replace('.', '').upper()

            if ccode:
                if len(self.timezones[ccode]) == 1:
                    zone = gettz(self.timezones[ccode][0])
                else:
                    raise TimezoneException(u'%s has multiple timezones: %s' % (self.countries[ccode], human_join(self.timezones[ccode])))

            else:
                possibles = []
                for zones in self.timezones.values():
                    for name in zones:
                        if string.replace(' ', '_').lower() in [part.lower() for part in name.split('/')]:
                            possibles.append(name)

                if len(possibles) == 1:
                    zone = gettz(possibles[0])
                elif len(possibles) > 1:
                    raise TimezoneException(u'Multiple timezones found: %s' % (human_join(possibles)))
                else:
                    zone = self._geonames_lookup(string)
                    if not zone:
                        raise TimezoneException(u"I don't know about the %s timezone" % (string,))

        return zone

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

    @match(r'^when\s+is\s+((?:[0-9.:/hT -]|%s)+)(?:\s+(.+))?\s+in\s+(.+)$' % '|'.join(MONTH_SHORT+MONTH_LONG+OTHER_STUFF))
    def convert(self, event, time, from_, to):
        source = time and parse(time) or datetime.now()

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
