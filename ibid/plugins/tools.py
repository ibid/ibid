import re
from random import random, randint
from subprocess import Popen, PIPE
from datetime import datetime

from dateutil.parser import parse
from dateutil.tz import gettz, tzutc, tzlocal

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output

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

help['timezone'] = "Converts times between timezones."
class TimeZone(Processor):
    u"""when is <time> <place|timezone> in <place|timezone>
    time in <place|timezone>"""
    feature = 'timezone'

    @match(r'^when\s+is\s+(.+?)(?:\s+([a-z/_]+))?\s+in\s+(\S+)$')
    def convert(self, event, time, from_, to):
        time = parse(time)

        if from_:
            from_zone = gettz(from_)
            if not from_zone:
                event.addresponse(u"I don't know about the %s timezone", from_)
                return
        else:
            from_zone = tzlocal()

        to_zone = gettz(to)
        if not to_zone:
            event.addresponse(u"I don't know about the %s timezone", to)
            return

        source = time.replace(tzinfo=from_zone)
        result = source.astimezone(to_zone)

        event.addresponse(u'%(sdate)s %(stime)s %(szone)s is %(ddate)s %(dtime)s %(dzone)s', {
            'sdate': source.strftime('%Y/%m/%d'),
            'stime': source.strftime('%H:%M:%S'),
            'szone': source.tzinfo.tzname(source),
            'ddate': result.strftime('%Y/%m/%d'),
            'dtime': result.strftime('%H:%M:%S'),
            'dzone': result.tzinfo.tzname(result),
        })

    @match(r"^(?:what(?:'?s|\s+is)\s+the\s+)?time\s+in\s+(\S+)$")
    def time(self, event, place):
        self.convert(event, datetime.now().isoformat(), None, place)

# vi: set et sta sw=4 ts=4:
