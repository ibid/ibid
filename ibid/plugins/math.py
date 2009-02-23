from subprocess import Popen, PIPE

from ibid.plugins import Processor, match
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

    def in_base(self, num, base, numerals="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        "Recursive base-display formatter"
        if num == 0:
            return "0"
        return self.in_base(num // base, base).lstrip("0") + numerals[num % base]

    # Ain't I a pretty regex?
    @match(r"^([0-9a-zA-Z+/]+)(?:\s+(base\s+\d+|hex(?:adecimal)?|dec(?:imal)?|oct(?:al)?|bin(?:ary)?))?\s+(?:in|to)\s+(base\s+\d+|hex(?:adecimal)?|dec(?:imal)?|oct(?:al)?|bin(?:ary)?)\s*$")
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
        
        if base_from < 2 or base_from > 36 or base_to < 2 or base_to > 36:
            event.addresponse(u"Sorry, valid bases are between 2 and 36, inclusive.")
            return
            
        number = int(number, base_from)
        
        base = u"base %i" % base_to
        if base_to in self.base_names:
            base = self.base_names[base_to]

        event.addresponse(u"That'd be about %s in %s." % (self.in_base(number, base_to), base))

    @match(r"^ascii\s+(.+)\s+(?:in|to)\s+(hex(?:adecimal)?|dec(?:imal)?|oct(?:al)?|bin(?:ary)?)$")
    def ascii_decode(self, event, text, base_to):
        base_to = self.named_bases[base_to[:3]]

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

        event.addresponse(u"We're looking at %s" % output)

    @match(r"^([0-9a-fA-F\s]+\s+hex(?:adecimal)?|[0-9\s]+\s+dec(?:imal)?|[0-7\s]+\s+oct(?:al)?|[01\s]+\s+bin(?:ary)?)\s+(?:in|to)\s+ascii$")
    def ascii_encode(self, event, source):
        base_from = self.named_bases[source.split()[-1]]
        text = u" ".join(source.split()[:-1])

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

        event.addresponse(u"That says '%s'" % output)

# vi: set et sta sw=4 ts=4:
