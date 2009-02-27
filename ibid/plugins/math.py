import re
from subprocess import Popen, PIPE

from ibid.plugins import Processor, match, handler
from ibid.config import Option

help = {}

help['bc'] = u'Calculate mathematical expressions using bc'
class BC(Processor):
    """bc <expression>"""

    feature = 'bc'

    bc = Option('bc', 'Path to bc executable', 'bc')

    @match(r'^bc\s+(.+)$')
    def calculate(self, event, expression):
        bc = Popen([self.bc, '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, error = bc.communicate(expression.encode('utf-8') + '\n')
        code = bc.wait()

        if code == 0:
            event.addresponse(output.strip())

help['calc'] = 'Returns the anwser to mathematical expressions'
class Calc(Processor):
    """[calc] <expression>"""
    feature = 'calc'

    priority = 500

    extras = ('abs', 'pow', 'round', 'min', 'max')
    banned = ('for', 'yield', 'lambda')

    # Create a safe dict to pass to eval() as locals
    safe = {}
    exec('from math import *', safe)
    del safe['__builtins__']
    for function in extras:
        safe[function] = eval(function)

    @match(r'^(?:calc\s+)?(.+?)$')
    def calculate(self, event, expression):
        for term in self.banned:
            if term in expression:
                return

        try:
            result = eval(expression, {'__builtins__': None}, self.safe)
        except Exception, e:
            return

        if isinstance(result, (int, long, float, complex)):
            event.addresponse(unicode(result))

help['base'] = 'Convert numbers between bases (radixes)'
class BaseConvert(Processor):
    """<number> [base <number>] (in|to) base <number>"""
    """ascii <text> (in|to) (hex|dec|oct|bin)"""

    feature = "base"
    
    named_bases = {
            "hex": 16,
            "dec": 10,
            "oct": 8,
            "bin": 2,
    }

    base_names = {
            2: u"binary",
            3: u"ternary",
            4: u"quaternary",
            6: u"senary",
            8: u"octal",
            9: u"nonary",
            10: u"decimal",
            12: u"duodecimal",
            16: u"hexadecimal",
            20: u"vigesimal",
            30: u"trigesimal",
            32: u"duotrigesimal",
            36: u"hexatridecimal",
    }

    numerals = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/"
    values = {}
    for value, numeral in enumerate(numerals):
        values[numeral] = value

    def in_base(self, num, base):
        "Recursive base-display formatter"
        if num == 0:
            return "0"
        return self.in_base(num // base, base).lstrip("0") + self.numerals[num % base]

    def from_base(self, num, base):
        "Return a base-n number in decimal - int(x, n) only goes up to 36"
        decimal = 0
        for digit in num:
            decimal *= base
            decimal += self.values[digit]
        return decimal

    def setup(self):
        bases = []
        for abbr, base in self.named_bases.iteritems():
            bases.append(r"%s(?:%s)?" % (abbr, self.base_names[base][3:]))
        bases = "|".join(bases)
        self.base_conversion.im_func.pattern = re.compile(
            r"^(?:convert\s+)?([0-9a-zA-Z+/]+)\s+(?:(?:from\s+)?(base\s+\d+|%s)\s+)?(?:in|to)\s+(base\s+\d+|%s)\s*$" % (bases, bases), re.I)
        self.ascii_decode.im_func.pattern = re.compile(
            r"^(?:convert\s+)?ascii\s+(.+)\s+(?:in|to)\s+(base\s+\d+|%s)$" % bases, re.I)

    @handler
    def base_conversion(self, event, number, base_from, base_to):
        if base_from is None:
            base_from = 10
        elif base_from[:3] in self.named_bases:
            base_from = self.named_bases[base_from[:3]]
        elif base_from.startswith(u"base"):
            base_from = int(base_from.split()[-1])

        if base_to is None:
            base_to = 10
        elif base_to[:3] in self.named_bases:
            base_to = self.named_bases[base_to[:3]]
        elif base_to.startswith(u"base"):
            base_to = int(base_to.split()[-1])
        
        if base_from < 2 or base_from > 64 or base_to < 2 or base_to > 64:
            event.addresponse(u"Sorry, valid bases are between 2 and 64, inclusive.")
            return
            
        number = self.from_base(number, base_from)
        
        base = u"base %i" % base_to
        if base_to in self.base_names:
            base = self.base_names[base_to]

        event.addresponse(u"That is %s in %s." % (self.in_base(number, base_to), base))

    @handler
    def ascii_decode(self, event, text, base_to):
        if base_to[:3] in self.named_bases:
            base_to = self.named_bases[base_to[:3]]
        elif base_to.startswith(u"base"):
            base_to = int(base_to.split()[-1])

        if len(text) > 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            text = text[1:-1]
        
        output = u""
        for char in text:
            code_point = ord(char)
            if code_point > 255:
                output += u"U%i " % code_point
            else:
                output += self.in_base(code_point, base_to) + u" "
        
        output = output.strip()

        event.addresponse(u"That is %s." % output)

    @match(r"^(?:convert\s+)?([0-9a-fA-F\s]+\s+hex(?:adecimal)?|[0-7\s]+\s+oct(?:al)?|[01\s]+\s+bin(?:ary)?|[0-9\s]+(?:\s+dec(?:imal)?)?)\s+(?:in|to)\s+ascii$")
    def ascii_encode(self, event, source):
        source = source.strip().split()
        base_from = source[-1]
        text = u""
        if base_from in self.named_bases:
            base_from = self.named_bases[base_from]
            text = u" ".join(source[:-1])
        else:
            base_from = 10
            text = u" ".join(source)

        output = u""
        buf = u""

        def process_buf(buf):
            char = int(buf, base_from)
            if char > 255:
                raise ValueError(u"I only deal with Basic ASCII. You don't get ascii characters bigger than 127, %i is." % char)
            elif char < 32:
                return u" %s " % "NUL SOH STX EOT ENQ ACK BEL BS HT LF VT FF SO SI DLE DC1 DC2 DC2 DC4 NAK SYN ETB CAN EM SUB ESC FS GS RS US".split()[char]
            elif char == 127:
                return u" DEL "
            return chr(char)

        for char in text:
            if char == u" ":
                if len(buf) > 0:
                    output += process_buf(buf)
                    buf = u""
                else:
                    output += u" "
            else:
                buf += char
                if (len(buf) == 2 and base_from == 16) or (len(buf) == 3 and base_from == 8) or (len(buf) == 8 and base_from == 2):
                    output += process_buf(buf)
                    buf = u""

        if len(buf) > 0:
            output += process_buf(buf)
        
        output = output.strip()

        event.addresponse(u'That is "%s".' % output)

# vi: set et sta sw=4 ts=4:
