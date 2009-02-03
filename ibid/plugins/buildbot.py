from twisted.spread import pb
from twisted.internet import reactor
from twisted.cred import credentials

import ibid
from ibid.plugins import Processor, match, RPC, Option, IntOption

help = {}

class BuildBot(Processor, RPC):

    feature = 'buildbot'

    server = Option('server', 'Buildbot server hostname', 'localhost')
    port = IntOption('port', 'Buildbot server port number', 9989)
    source = Option('source', 'Source to send commit notifications to')
    channel = Option('channel', 'Channel to send commit notifications to')

    def __init__(self, name):
        Processor.__init__(self, name)
        RPC.__init__(self)

    def remote_built(self, branch, revision, person, result):
        reply = u"Build %s of %s triggered by %s: %s" % (revision, branch, person, result)
        ibid.dispatcher.send({'reply': reply, 'source': self.source, 'target': self.channel})

    @match(r'^(?:re)?build\s+(.+?)(?:\s+(?:revision|r)?\s*(\d+))?$')
    def build(self, event, branch, revision):
        change = {  'who': event.who,
                    'branch': branch,
                    'files': [None],
                    'revision': revision or '-1',
                    'comments': 'Rebuild',
                }

        buildbot = pb.PBClientFactory()
        reactor.connectTCP(self.server, self.port, buildbot)
        d = buildbot.login(credentials.UsernamePassword('change', 'changepw'))
        d.addCallback(lambda root: root.callRemote('addChange', change))
        d.addCallback(self.respond, event, True)
        d.addErrback(self.respond, event, False)
        event.processed = True

    def respond(self, rpc_response, event, result):
        ibid.dispatcher.send({'reply': result and 'Okay' or u"buildbot doesn't want to build :-(", 'source': event.source, 'target': event.channel})
                    

# vi: set et sta sw=4 ts=4:
