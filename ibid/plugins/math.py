from subprocess import Popen, PIPE

from ibid.plugins import Processor, match
from ibid.config import Option

help = {}

help['calc'] = 'Returns the anwser to mathematical expressions'
class BC(Processor):
    """<expression>"""

    feature = 'calc'
    priority = 500

    bc = Option('bc', 'Path to bc executable', 'bc')

    @match(r'^(.+)$')
    def calculate(self, event, expression):
        bc = Popen([self.bc, '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, error = bc.communicate(expression.encode('utf-8') + '\n')
        code = bc.wait()

        if code == 0:
            event.addresponse(output)

# vi: set et sta sw=4 ts=4:
