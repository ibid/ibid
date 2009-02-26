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
            if expression.find(term) != -1:
                return

        try:
            result = eval(expression, {'__builtins__': None}, self.safe)
        except Exception, e:
            return

        if isinstance(result, (int, long, float, complex)):
            event.addresponse(unicode(result))

# vi: set et sta sw=4 ts=4:
