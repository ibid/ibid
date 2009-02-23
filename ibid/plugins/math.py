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
    """<number> [base <number>] in base <number>"""
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
    @match(r"^([0-9a-zA-Z+/]+)(?:\s+(base\s+\d+|hex(?:adecimal)?|dec(?:imal)?|oct(?:al)?|bin(?:ary)?))?\s+in\s+(base\s+\d+|hex(?:adecimal)?|dec(?:imal)?|oct(?:al)?|bin(?:ary)?)\s*$")
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

# vi: set et sta sw=4 ts=4:
