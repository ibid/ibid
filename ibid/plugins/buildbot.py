import ibid
from ibid.plugins import Processor, RPC

help = {}

class BuildBot(Processor, RPC):

    feature = 'buildbot'

    def __init__(self, name):
        Processor.__init__(self, name)
        RPC.__init__(self)

    def remote_built(self, branch, revision, person, result):
        reply = u"Build %s of %s triggered by %s: %s" % (revision, branch, person, result)
        ibid.dispatcher.send({'reply': reply, 'source': self.source, 'target': self.channel})

# vi: set et sta sw=4 ts=4:
