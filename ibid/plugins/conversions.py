# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from subprocess import Popen, PIPE
from urllib import urlencode
import logging
import re
import unicodedata

import ibid
from ibid.plugins import Processor, handler, match
from ibid.compat import any, defaultdict, ElementTree
from ibid.config import Option
from ibid.utils import (cacheable_download, file_in_path, get_country_codes,
                        human_join, unicode_output, generic_webservice)
from ibid.utils.html import get_html_parse_tree

features = {}
log = logging.getLogger('plugins.conversions')

features['base'] = {
    'description': u'Convert numbers between bases (radixes)',
    'categories': ('calculate', 'convert',),
}
class BaseConvert(Processor):
    usage = u"""[convert] <number> [from base <number>] to base <number>
    [convert] ascii <text> to base <number>
    [convert] <sequence> from base <number> to ascii"""

    features = ('base',)

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

        if base_to == 64 and any(True for plugin in ibid.processors
                if 'base64' in getattr(plugin, 'features', [])):
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
        if base_from == 64 and any(True for plugin in ibid.processors
                if 'base64' in getattr(plugin, 'features', [])):
            event.addresponse(u'If you want a base64 encoding, use the "base64" feature')

features['units'] = {
    'description': 'Converts values between various units.',
    'categories': ('convert',),
}
class Units(Processor):
    usage = u'convert [<value>] <unit> to <unit>'
    features = ('units',)
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

features['currency'] = {
    'description': u'Converts amounts between currencies.',
    'categories': ('convert',),
}
class Currency(Processor):
    usage = u"""exchange <amount> <currency> for <currency>
    currencies for <country>"""

    features = ('currency',)

    currencies = {}
    country_codes = {}

    def _load_currencies(self):
        iso4127_file = cacheable_download(
                'http://www.currency-iso.org/dl_iso_table_a1.xml',
                'conversions/iso4217.xml')
        document = ElementTree.parse(iso4127_file)
        # Code -> [Countries..., Currency Name]
        self.currencies = {}
        # Country -> Code
        self.country_currencies = {}
        self.country_codes = get_country_codes()
        for currency in document.getiterator('ISO_CURRENCY'):
            code = currency.findtext('ALPHABETIC_CODE').strip()
            if code == '':
                continue
            name = currency.findtext('CURRENCY').strip()
            place = currency.findtext('ENTITY').strip().title()
            if code in self.currencies:
                if self.country_codes.get(code[:2], '').lower() == place.lower():
                    self.currencies[code][0].insert(0, place)
                else:
                    self.currencies[code][0].append(place)
            else:
                self.currencies[code] = [[place], name]
            if code[:2] not in self.country_currencies:
                self.country_currencies[code[:2]] = code

        # Non-currencies:
        for code in ('BOV CLF COU MXV UYI ' # Various Fund codes
                     'CHE CHW '             # Swiss WIR currencies
                     'USN USS '             # US Dollar fund codes
                     'XAG XAU XPD XPT '     # Metals
                     'XBA XBB XBC XBD '     # Euro Bond Market
                     'XDR XTS XXX '         # Other specials
                    ).split():
            del self.currencies[code]

        # Special cases for shared currencies:
        self.currencies['EUR'][0].insert(0, u'Euro Member Countries')
        self.currencies['XAF'][0].insert(0, u"Communaut\xe9 financi\xe8re d'Afrique")
        self.currencies['XCD'][0].insert(0, u'Organisation of Eastern Caribbean States')
        self.currencies['XOF'][0].insert(0, u'Coop\xe9ration financi\xe8re en Afrique centrale')
        self.currencies['XPF'][0].insert(0, u'Comptoirs Fran\xe7ais du Pacifique')

    def resolve_currency(self, name, rough=True):
        "Return the canonical name for a currency"

        if not self.currencies:
            self._load_currencies()

        if name.upper() in self.currencies:
            return name.upper()

        # Strip leading dots (.TLD) and plurals
        strip_currency_re = re.compile(r'^[\.\s]*([\w\s]+?)s?$', re.UNICODE)
        m = strip_currency_re.match(name)

        if m is None:
            return False

        name = m.group(1).lower()

        # TLD -> country name
        if rough and len(name) == 2 and name.upper() in self.country_codes:
           name = self.country_codes[name.upper()].lower()

        # Currency Name
        if name == u'dollar':
            return "USD"
        if name == u'pound':
            return "GBP"
        for code, (places, currency) in self.currencies.iteritems():
            if name in currency.lower():
                return code

        # Country Names
        for code, place in self.country_codes.iteritems():
            if name in place.lower():
                return self.country_currencies[code]

        return False

    @match(r'^(exchange|convert)\s+([0-9.]+)\s+(.+)\s+(?:for|to|into)\s+(.+)$')
    def exchange(self, event, command, amount, frm, to):
        rough = command.lower() == 'exchange'

        canonical_frm = self.resolve_currency(frm, rough)
        canonical_to = self.resolve_currency(to, rough)
        if not canonical_frm or not canonical_to:
            if rough:
                event.addresponse(u"Sorry, I don't know about a currency for %s", (not canonical_frm and frm or to))
            return

        data = generic_webservice(
                'http://download.finance.yahoo.com/d/quotes.csv', {
                    'f': 'l1ba',
                    'e': '.csv',
                    's': canonical_frm + canonical_to + '=X',
                })
        last_trade_rate, bid, ask = data.strip().split(',')
        if last_trade_rate == 0:
            event.addresponse(
                    u"Whoops, looks like I couldn't make that conversion")
            return

        event.addresponse(
            u'%(fresult)s %(fcode)s (%(fcountry)s %(fcurrency)s) = '
            u'%(tresult)0.2f %(tcode)s (%(tcountry)s %(tcurrency)s) '
            u'(Last trade rate: %(rate)s, Bid: %(bid)s, Ask: %(ask)s)', {
                'fresult': amount,
                'tresult': float(amount) * float(last_trade_rate),
                'fcountry': self.currencies[canonical_frm][0][0],
                'fcurrency': self.currencies[canonical_frm][1],
                'tcountry': self.currencies[canonical_to][0][0],
                'tcurrency': self.currencies[canonical_to][1],
                'fcode': canonical_frm,
                'tcode': canonical_to,
                'rate': last_trade_rate,
                'bid': bid,
                'ask': ask,
            })

    @match(r'^(?:currency|currencies)\s+for\s+(?:the\s+)?(.+)$')
    def currency(self, event, place):
        if not self.currencies:
            self._load_currencies()

        search = re.compile(place, re.I)
        results = defaultdict(list)
        for code, (places, name) in self.currencies.iteritems():
            for place in places:
                if search.search(place):
                    results[place].append(u'%s (%s)' % (name, code))
                    break

        if results:
            event.addresponse(human_join(
                u'%s uses %s' % (place, human_join(currencies))
                for place, currencies in results.iteritems()
            ))
        else:
            event.addresponse(u'No currencies found')

class UnassignedCharacter(Exception): pass

def fix_pinyin_tone(syllable):
    """Change numeric tones to diacritics in pinyin."""
    tone = syllable[-1]
    if tone.isdigit():
        tone = {'1': u'\u0304', '2': u'\u0301', '3': u'\u030c',
                '4': u'\u0300'}.get(tone, '')
        syllable = syllable[:-1]
        # if there's an A, E or O then it takes the mark; in the case of AO, the
        # mark goes on the A
        for v in 'AaEeOo':
            if v in syllable:
                return unicodedata.normalize('NFC', syllable.replace(v, v+tone))
        # the mark goes on the second letter of UI and IU
        for v in ('UI', 'ui' 'IU', 'iu'):
            if v in syllable:
                return unicodedata.normalize('NFC', syllable.replace(v, v+tone))
        # otherwise there was only a single vowel
        for v in u'IiUuVv' \
                 u'\N{Latin Capital Letter U With Diaeresis}' \
                 u'\N{Latin Small Letter U With Diaeresis}':
            if v in syllable:
                return unicodedata.normalize('NFC', syllable.replace(v, v+tone))

    return syllable

def html_flatten(soup):
    text = []
    for subsoup in soup.contents:
        if isinstance(subsoup, basestring):
            text.append(subsoup)
        else:
            text.append(html_flatten(subsoup))
    return ''.join(text)
    
class Unihan(object):
    def __init__(self, char):
        self.char = char
        url = 'http://www.unicode.org/cgi-bin/GetUnihanData.pl?'
        params = {'codepoint': self.char.encode('utf8'),
                  'useuft8': 'true'}
        soup = get_html_parse_tree(url + urlencode(params),
                                            treetype='html5lib-beautifulsoup')

        tables = soup('table', border="1")

        self.data = defaultdict(unicode,
                                ((html_flatten(td).strip() for td in row('td'))
                                 for table in tables for row in table('tr')[1:]))

    def pinyin(self):
        return map(fix_pinyin_tone, self.data['kMandarin'].lower().split())

    def hangul(self):
        return self.data['kHangul'].split()

    def korean_yale(self):
        return self.data['kKorean'].lower().split()

    def korean(self):
        return [u'%s [%s]' % (h, y) for h, y in
                                    zip(self.hangul(), self.korean_yale())]

    def japanese_on(self):
        return self.data['kJapaneseOn'].lower().split()

    def japanese_kun(self):
        return self.data['kJapaneseKun'].lower().split()

    def definition(self):
        return self.data['kDefinition']

    def variant(self):
        msgs = []
        for name in ('simplified', 'traditional'):
            variants = self.data['k' + name.title() + 'Variant'].split()[1::2]
            if variants:
                msgs.append(u'the %(name)s form is %(var)s' %
                            {'name': name,
                             'var': human_join(variants, conjunction='or')})
        return msgs

    def __unicode__(self):
        msgs = []
        if self.definition():
            msgs = [u'it means %s' % self.definition()]

        msgs += self.variant()

        prons = []
        for reading, lang in ((self.pinyin, 'pinyin'),
                                (self.korean, 'Korean'),
                                (self.japanese_on, 'Japanese on'),
                                (self.japanese_kun, 'Japanese kun')):
            readings = reading()
            if readings:
                prons.append(u'%(readings)s (%(lang)s)' %
                                {'readings': human_join(readings, conjunction=u'or'), 'lang': lang})

        if prons:
            msgs.append(u'it is pronounced ' +
                            human_join(prons, conjunction=u'or'))

        msg =  u'; '.join(msgs)
        if msg:
            msg = msg[0].upper() + msg[1:]
        return msg

features['unicode'] = {
    'description': u'Look up characters in the Unicode database.',
    'categories': ('lookup', 'convert',),
}
class UnicodeData(Processor):
    usage = u"""U+<hex code>
    unicode (<character>|<character name>|<decimal code>|0x<hex code>)"""

    features = ('unicode',)

    bidis = {'AL': u'right-to-left Arabic', 'AN': u'Arabic number',
             'B': u'paragraph separator', 'BN': u'boundary neutral',
             'CS': u'common number separator', 'EN': u'European number',
             'ES': u'European number separator',
             'ET': u'European number terminator',
             'L': u'left-to-right', u'LRE': 'left-to-right embedding',
             'LRO': u'left-to-right override', 'NSM': u'non-spacing mark',
             'ON': u'other neutral', 'PDF': u'pop directional format',
             'R': u'right-to-left', 'RLE': u'right-to-left embedding',
             'RLO': u'right-to-left override', 'S': u'segment separator',
             'WS': u'whitespace'}

    categories = {'Cc': u'a control character', 'Cf': u'a formatting character',
                  'Cn': u'an unassigned character', 'Co': u'a private-use character',
                  'Cs': u'a surrogate character', 'Ll': u'a Lowercase Letter',
                  'Lm': u'a Modifier Letter', 'Lo': u'a Letter',
                  'Lt': u'a Titlecase Letter', 'Lu': u'an Uppercase Letter',
                  'Mc': u'a Spacing Combining Mark', 'Me': u'an Enclosing Mark',
                  'Mn': u'a Nonspacing Mark', 'Nd': u'a Decimal Digit Number',
                  'Nl': u'a Letter Number', 'No': u'a Number',
                  'Pc': u'a Connector', 'Pd': u'a Dash',
                  'Pe': u'a Close Punctuation mark', 'Pf': u'a Final quote',
                  'Pi': u'an Initial quote', 'Po': u'a Punctuation character',
                  'Ps': u'an Open Punctuation mark', 'Sc': u'a Currency Symbol',
                  'Sk': u'a Modifier Symbol', 'Sm': u'a Math Symbol',
                  'So': u'a Symbol', 'Zl': u'a Line Separator',
                  'Zp': u'a Paragraph Separator', 'Zs': u'a Space Separator'}

    @match(r'^(?:(?:uni(?:code|han)\s+)?U\+|'
                r'uni(?:code|han)\s+#?0?x)([0-9a-f]+)$|'
           r'^(?:unicode|unihan|ascii)\s+'
                r'([0-9a-f]*(?:[0-9][a-f]|[a-f][0-9])[0-9a-f]*)$|'
           r'^(?:unicode|unihan|ascii)\s+#?(\d{2,})$', simple=False)
    def unichr(self, event, hexcode, hexcode2, deccode):
        if hexcode or hexcode2:
            code = int(hexcode or hexcode2, 16)
        else:
            code = int(deccode)

        try:
            char = unichr(code)
            info = self.info(char)
        except (ValueError, OverflowError):
            event.addresponse(u"Unicode isn't *that* big!")
        except UnassignedCharacter:
            event.addresponse(u"That character isn't in Unicode")
        else:
            if info['example']:
                info['example'] = ' (' + info['example'] + ')'
            if deccode:
                info['code'] += ' (%i)' % code
            event.addresponse(u"U+%(code)s is %(name)s%(example)s, "
                          u"%(category)s with %(bidi)s directionality"
                          u"%(unihan)s",
                          info)

    @match(r'^uni(?:code|han)\s+(.)$', 'deaddressed', simple=False)
    def ord(self, event, char):
        try:
            info = self.info(char)
        except UnassignedCharacter:
            event.addresponse(u"That character isn't in Unicode. "
                              u"Where did you even find it?")
        else:
            if info['example']:
                info['example'] = "'" + info['example'] + "'"
            else:
                info['example'] = 'That'
            event.addresponse(u"%(example)s is %(name)s (U+%(code)s), "
                              u"%(category)s with %(bidi)s directionality"
                              u"%(unihan)s",
                              info)

    @match(r'uni(?:code|han) ([a-z][a-z0-9 -]+)')
    def fromname(self, event, name):
        try:
            char = unicodedata.lookup(name.upper())
        except KeyError:
            event.addresponse(u"I couldn't find a character with that name")
        else:
            info = self.info(char)
            if info['example']:
                info['example'] = ' (' + info['example'] + ')'
            event.addresponse(u"%(name)s is U+%(code)s%(example)s, "
                              u"%(category)s with %(bidi)s directionality"
                              u"%(unihan)s",
                              info)

    # Match any string that can't be a character name or a number.
    @match(r'unicode (.*[^0-9a-z#+\s-].+|.+[^0-9a-z#+\s-].*)', 'deaddressed')
    def characters(self, event, string):
        event.addresponse(human_join('U+%(code)s %(name)s' % self.info(c)
                                        for c in string))

    def info(self, char):
        cat = unicodedata.category(char)
        if cat == 'Cn':
            raise UnassignedCharacter

        catname = self.categories[cat]
        bidi = self.bidis[unicodedata.bidirectional(char)]
        name = unicodedata.name(char, 'an unnamed character').decode('ascii')

        if cat[0] == 'C' or cat in ('Zp', 'Zl'):
            example = u''
        elif cat[0] == 'M' and cat[1] != 'c':
            example = u'\N{DOTTED CIRCLE}' + char
        else:
            example = char

        haninfo = u''
        if 'CJK' in name and 'IDEOGRAPH' in name:
            unihan = Unihan(char)
            haninfo = unicode(unihan)
            if haninfo:
                haninfo = u'. ' + haninfo + u'.'

        return {'code': u'%04X' % ord(char),
                'name': name.title().replace('Cjk', 'CJK'), 'char': char,
                'example': example, 'category': catname.lower(), 'bidi': bidi,
                'unihan': haninfo}

# vi: set et sta sw=4 ts=4:
