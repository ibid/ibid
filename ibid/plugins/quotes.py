from ibid.plugins import Processor, match, RPC
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output

help = {}

help['fortune'] = u'Returns a random fortune.'
class Fortune(Processor, RPC):
    u"""fortune"""
    feature = 'fortune'

    fortune = Option('fortune', 'Path of the fortune executable', 'fortune')

    def __init__(self, name):
        super(Fortune, self).__init__(name)
        RPC.__init__(self)

    def setup(self):
        if not file_in_path(self.fortune):
            raise Exception("Cannot locate fortune executable")

    @match(r'^fortune$')
    def handler(self, event):
        fortune = self.remote_fortune()
        if fortune:
            event.addresponse(fortune)
        else:
            event.addresponse(u"Couldn't execute fortune")

    def remote_fortune(self):
        fortune = Popen(self.fortune, stdout=PIPE, stderr=PIPE)
        output, error = fortune.communicate()
        code = fortune.wait()

        output = unicode_output(output.strip(), 'replace')

        if code == 0:
            return output
        else:
            return None

# vi: set et sta sw=4 ts=4:
