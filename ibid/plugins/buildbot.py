from twisted.spread import pb
from twisted.internet import reactor
from twisted.cred import credentials
from .. buildbot.interfaces import IStatusReceiver
from zope.interface import implements

import ibid
from ibid.plugins import Processor, match, RPC
from ibid.config import Option, IntOption

help = {}

class BuildBot(Processor, RPC):
    implements(IStatusReceiver)

    feature = 'buildbot'

    server = Option('server', 'Buildbot server hostname', 'localhost')
    status_port = IntOption('status_port', 'Buildbot server port number', 9988)
    change_port = IntOption('change_port', 'Buildbot server port number', 9989)
    source = Option('source', 'Source to send commit notifications to')
    channel = Option('channel', 'Channel to send commit notifications to')

    def __init__(self, name):
        Processor.__init__(self, name)
        RPC.__init__(self)

    def setup(self):
        self.status = pb.PBClientFactory()
        reactor.connectTCP(self.server, self.status_port, self.status)
        d = self.status.login(credentials.UsernamePassword('statusClient', 'clientpw'))
        d.addCallback(self.store_root, 'status')
        d.addCallback(lambda root: root.callRemote('subscribe', 'builds', 0, self))
        d.addErrback(self.exception)

        self.change = pb.PBClientFactory()
        reactor.connectTCP(self.server, self.change_port, self.change)
        d = self.change.login(credentials.UsernamePassword('change', 'changepw'))
        d.addCallback(self.store_root, 'change')
        d.addErrback(self.exception)

    def remote_built(self, branch, revision, person, result):
        reply = u"Build %s of %s triggered by %s: %s" % (revision, branch, person, result)
        ibid.dispatcher.send({'reply': reply, 'source': self.source, 'target': self.channel})
        return True

    @match(r'^(?:re)?build\s+(.+?)(?:\s+(?:revision|r)?\s*(\d+))?$')
    def build(self, event, branch, revision):
        change = {  'who': event.who,
                    'branch': branch,
                    'files': [None],
                    'revision': revision or '-1',
                    'comments': 'Rebuild',
                }

        d = self.change_root.callRemote('addChange', change)
        d.addCallback(self.respond, event, True)
        d.addErrback(self.respond, event, False)
        event.processed = True

    def respond(self, rpc_response, event, result):
        ibid.dispatcher.send({'reply': result and 'Okay' or u"buildbot doesn't want to build :-(", 'source': event.source, 'target': event.channel})

    def store_root(self, root, type):
        setattr(self, '%s_root' % type, root)
        return root

    def exception(self, exception):
        print exception
        raise exception

    def remote_buildsetSubmitted(self, buildset):
        pass

    def remote_builderAdded(self, builderName, builder):
        pass

    def remote_builderChangedState(self, builderName, state, foo):
        pass

    def remote_buildStarted(self, builderName, build):
        print "Build %s started on %s" % (builderName, build)

    def remote_buildETAUpdate(self, build, ETA):
        pass

    def remote_stepStarted(self, build, step):
        pass

    def remote_stepTextChanged(self, build, step, text):
        pass

    def remote_stepText2Changed(self, build, step, text2):
        pass

    def remote_stepETAUpdate(self, build, step, ETA, expectations):
        pass

    def remote_logStarted(self, build, step, log):
        pass

    def remote_logChunk(self, build, step, log, channel, text):
        pass

    def remote_logFinished(self, build, step, log):
        pass

    def remote_stepFinished(self, build, step, results):
        pass

    def remote_buildFinished(self, builderName, build, results):
        print "Build %s finished on %s" % (builderName, build)

    def remote_builderRemoved(self, builderName):
        pass

# vi: set et sta sw=4 ts=4:
