from subprocess import Popen, PIPE
import logging
import re

import ibid
from ibid.plugins import Processor, handler, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output

help = {}
log = logging.getLogger('conversions')

help['base'] = u'Convert numbers between bases (radixes)'
class BaseConvert(Processor):
    u"""[convert] <number> [from base <number>] to base <number>
    [convert] ascii <text> to base <number>
    [convert] <sequence> from base <number> to ascii"""

    feature = "base"

    abbr_named_bases = {
            "hex": 16,
            "dec": 10,
            "oct": 8,
            "bin": 2,
    }

    base_names = {
            2: "binary",
            3: "ternary",
            4: "quaternary",
            6: "senary",
            8: "octal",
            9: "nonary",
            10: "decimal",
            12: "duodecimal",
            16: "hexadecimal",
            20: "vigesimal",
            30: "trigesimal",
            32: "duotrigesimal",
            36: "hexatridecimal",
    }
    base_values = {}
    for value, name in base_names.iteritems():
        base_values[name] = value

    numerals = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/"
    values = {}
    for value, numeral in enumerate(numerals):
        values[numeral] = value

    def _in_base(self, num, base):
        "Recursive base-display formatter"
        if num == 0:
            return "0"
        return self._in_base(num // base, base).lstrip("0") + self.numerals[num % base]

    def _from_base(self, num, base):
        "Return a base-n number in decimal. Needed as int(x, n) only works for n<=36"

        if base <= 36:
            num = num.upper()

        decimal = 0
        for digit in num:
            decimal *= base
            if self.values[digit] >= base:
                raise ValueError("'%s' is not a valid digit in %s" % (digit, self._base_name(base)))
            decimal += self.values[digit]

        return decimal

    def _parse_base(self, base):
        "Parse a base in the form of 'hex' or 'base 13' or None"

        if base is None:
            base = 10
        elif len(base) == 3 and base in self.abbr_named_bases:
            base = self.abbr_named_bases[base]
        elif base in self.base_values:
            base = self.base_values[base]
        elif base.startswith(u"base"):
            base = int(base.split()[-1])
        else:
            # The above should be the only cases allowed by the regex
            # This exception indicates programmer error:
            raise ValueError("Unparsable base: " + base)

        return base

    def _base_name(self, base):
        "Shows off the bot's smartypants heritage by naming bases"

        base_name = u"base %i" % base

        if base in self.base_names:
            base_name = self.base_names[base]

        return base_name

    def setup(self):
        bases = []
        for number, name in self.base_names.iteritems():
            if name[:3] in self.abbr_named_bases and self.abbr_named_bases[name[:3]] == number:
                bases.append(r"%s(?:%s)?" % (name[:3], name[3:]))
            else:
                bases.append(name)
        bases = "|".join(bases)

        self.base_conversion.im_func.pattern = re.compile(
            r"^(?:convert\s+)?([0-9a-zA-Z+/]+)\s+(?:(?:(?:from|in)\s+)?(base\s+\d+|%s)\s+)?(?:in|to|into)\s+(base\s+\d+|%s)\s*$"
            % (bases, bases), re.I)

        self.ascii_decode.im_func.pattern = re.compile(
            r"^(?:convert\s+)?ascii\s+(.+?)(?:(?:\s+(?:in|to|into))?\s+(base\s+\d+|%s))?$" % bases, re.I)

        self.ascii_encode.im_func.pattern = re.compile(
            r"^(?:convert\s+)?([0-9a-zA-Z+/\s]+?)(?:\s+(?:(?:from|in)\s+)?(base\s+\d+|%s))?\s+(?:in|to|into)\s+ascii$" % bases, re.I)

    @handler
    def base_conversion(self, event, number, base_from, base_to):
        "Arbitrary (2 <= base <= 64) numeric base conversions."

        base_from = self._parse_base(base_from)
        base_to = self._parse_base(base_to)

        if min(base_from, base_to) < 2 or max(base_from, base_to) > 64:
            event.addresponse(u'Sorry, valid bases are between 2 and 64, inclusive')
            return

        try:
            number = self._from_base(number, base_from)
        except ValueError, e:
            event.addresponse(unicode(e))
            return

        event.addresponse(u'That is %(result)s in %(base)s', {
            'result': self._in_base(number, base_to),
            'base': self._base_name(base_to),
        })

    @handler
    def ascii_decode(self, event, text, base_to):
        "Display the values of each character in an ASCII string"

        base_to = self._parse_base(base_to)

        if len(text) > 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            text = text[1:-1]

        output = u""
        for char in text:
            code_point = ord(char)
            if code_point > 255:
                output += u'U%s ' % self._in_base(code_point, base_to)
            else:
                output += self._in_base(code_point, base_to) + u" "

        output = output.strip()

        event.addresponse(u'That is %(result)s in %(base)s', {
            'result': output,
            'base': self._base_name(base_to),
        })

        if base_to == 64 and [True for plugin in ibid.processors if getattr(plugin, 'feature', None) == 'base64']:
            event.addresponse(u'If you want a base64 encoding, use the "base64" feature')

    @handler
    def ascii_encode(self, event, source, base_from):

        base_from = self._parse_base(base_from)

        output = u""
        buf = u""

        def process_buf(buf):
            char = self._from_base(buf, base_from)
            if char > 127:
                raise ValueError(u"I only deal with the first page of ASCII (i.e. under 127). %i is invalid." % char)
            elif char < 32:
                return u" %s " % "NUL SOH STX EOT ENQ ACK BEL BS HT LF VT FF SO SI DLE DC1 DC2 DC2 DC4 NAK SYN ETB CAN EM SUB ESC FS GS RS US".split()[char]
            elif char == 127:
                return u" DEL "
            return unichr(char)

        try:
            for char in source:
                if char == u" ":
                    if len(buf) > 0:
                        output += process_buf(buf)
                        buf = u""
                else:
                    buf += char
                    if (len(buf) == 2 and base_from == 16) or (len(buf) == 3 and base_from == 8) or (len(buf) == 8 and base_from == 2):
                        output += process_buf(buf)
                        buf = u""

            if len(buf) > 0:
                output += process_buf(buf)
        except ValueError, e:
            event.addresponse(unicode(e))
            return

        event.addresponse(u'That is "%s"', output)
        if base_from == 64 and [True for plugin in ibid.processors if getattr(plugin, 'feature', None) == 'base64']:
            event.addresponse(u'If you want a base64 encoding, use the "base64" feature')

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

# vi: set et sta sw=4 ts=4:
