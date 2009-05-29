import logging
from os import kill
import re
from signal import SIGTERM
from subprocess import Popen, PIPE
from time import time, sleep

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option, FloatOption
from ibid.utils import file_in_path, unicode_output

try:
    from ast import NodeTransformer, Pow, Name, Load, Call, copy_location, parse
    transform_method='ast'

except ImportError:
    from compiler import ast, pycodegen, parse, misc, walk
    class NodeTransformer(object):
        pass
    transform_method='compiler'

help = {}
log = logging.getLogger('math')

help['bc'] = u'Calculate mathematical expressions using bc'
class BC(Processor):
    u"""bc <expression>"""

    feature = 'bc'

    bc = Option('bc', 'Path to bc executable', 'bc')
    bc_timeout = FloatOption('bc_timeout', 'Maximum BC execution time (sec)', 2.0)

    def setup(self):
        if not file_in_path(self.bc):
            raise Exception("Cannot locate bc executable")

    @match(r'^bc\s+(.+)$')
    def calculate(self, event, expression):
        bc = Popen([self.bc, '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        start_time = time()
        bc.stdin.write(expression.encode('utf-8') + '\n')
        bc.stdin.close()

        while bc.poll() is None and time() - start_time < self.bc_timeout:
            sleep(0.1)

        if bc.poll() is None:
            kill(bc.pid, SIGTERM)
            event.addresponse(u'Sorry, that took too long. I stopped waiting')
            return

        output = bc.stdout.read()
        error = bc.stderr.read()
        
        code = bc.wait()

        if code == 0:
            if output:
                output = unicode_output(output.strip())
                output = output.replace('\\\n', '')
                event.addresponse(output)
            else:
                error = unicode_output(error.strip())
                error = error.split(":", 1)[1].strip()
                error = error[0].lower() + error[1:].split('\n')[0]
                event.addresponse(u"I'm sorry, I couldn't deal with the %s", error)
        else:
            event.addresponse(u"Error running bc")
            error = unicode_output(error.strip())
            raise Exception("BC Error: %s" % error)

help['calc'] = u'Returns the anwser to mathematical expressions'
class LimitException(Exception):
    pass

def limited_pow(*args):
    "We don't want users to DOS the bot. Pow is the most dangerous function. Limit it"

    # Are all the arguments ints?
    if not [True for arg in args if not isinstance(arg, int) and not isinstance(arg, long)]:
        try:
            answer = pow(float(args[0]), float(args[1]))
            if answer > 1e+300:
                raise LimitException

        except OverflowError, e:
            raise LimitException(e)

    return pow(*args)

# ast method
class PowSubstitutionTransformer(NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, Pow):
            fnode = Name('pow', Load())
            copy_location(fnode, node)
            cnode = Call(fnode, [node.left, node.right], [], None, None)
            copy_location(cnode, node)
            return cnode
        return node

# compiler method
class PowSubstitutionWalker(object):
    def visitPower(self, node, *args):
        walk(node.left, self)
        walk(node.right, self)
        cnode = ast.CallFunc(ast.Name('pow'), [node.left, node.right], None, None)
        node.left = cnode
        # Little hack: instead of trying to turn node into a CallFunc, we just do pow(left, right)**1
        node.right = ast.Const(1)

class Calc(Processor):
    u"""[calc] <expression>"""
    feature = 'calc'

    priority = 500

    extras = ('abs', 'round', 'min', 'max')
    banned = ('for', 'yield', 'lambda')

    # Create a safe dict to pass to eval() as locals
    safe = {}
    exec('from math import *', safe)
    del safe['__builtins__']
    for function in extras:
        safe[function] = eval(function)
    safe['pow'] = limited_pow

    @match(r'^(?:calc\s+)?(.+?)$')
    def calculate(self, event, expression):
        for term in self.banned:
            if term in expression:
                return

        try:
            # We need to remove all power operators and replace with our limited pow
            # ast is the new method (Python >=2.6) compiler is the old 
            ast = parse(expression, mode='eval')
            if transform_method == 'ast':
                ast = PowSubstitutionTransformer().visit(ast)
                code = compile(ast, '<string>', 'eval')
            else:
                misc.set_filename('<string>', ast)
                walk(ast, PowSubstitutionWalker())
                code = pycodegen.ExpressionCodeGenerator(ast).getCode()

            result = eval(code, {'__builtins__': None}, self.safe)

        except ZeroDivisionError, e:
            event.addresponse(u"I can't divide by zero.")
            return
        except ArithmeticError, e:
            event.addresponse(u"I can't do that: %s", unicode(e))
            return
        except ValueError, e:
            if unicode(e) == u"math domain error":
                event.addresponse(u"I can't do that: %s", unicode(e))
            return
        except LimitException, e:
            event.addresponse(u"I'm afraid I'm not allowed to play with big numbers")
            return
        except Exception, e:
            return

        if isinstance(result, (int, long, float, complex)):
            event.addresponse(unicode(result))

help['base'] = 'Convert numbers between bases (radixes)'
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

# vi: set et sta sw=4 ts=4:
