from subprocess import Popen, PIPE

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output

help = {}

help['bc'] = u'Calculate mathematical expressions using bc'
class BC(Processor):
    u"""bc <expression>"""

    feature = 'bc'

    bc = Option('bc', 'Path to bc executable', 'bc')

    def setup(self):
        if not file_in_path(self.bc):
            raise Exception("Cannot locate bc executeable")

    @match(r'^bc\s+(.+)$')
    def calculate(self, event, expression):
        bc = Popen([self.bc, '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, error = bc.communicate(expression.encode('utf-8') + '\n')
        code = bc.wait()

        if code == 0:
            if output:
                output = unicode_output(output.strip())
                output = output.replace('\\\n', '')
                event.addresponse(output)
            else:
                error = unicode_output(error.strip())
                error = error.split(":", 1)[1].strip()
                error = error[0].lower() + error[1:]
                event.addresponse(u"You can't %s" % error)
        else:
            event.addresponse(u"Error running bc")
            error = unicode_output(error.strip())
            raise Exception("BC Error: %s" % error)

help['calc'] = u'Returns the anwser to mathematical expressions'
class Calc(Processor):
    u"""[calc] <expression>"""
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

# vi: set et sta sw=4 ts=4:
