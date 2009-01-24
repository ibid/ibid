from urlparse import urlparse
from urllib2 import urlopen

from bzrlib import branch
from twisted.spread import pb
from twisted.internet import reactor
from twisted.python import util

repositories =  {   '/srv/src/ibid/': 'ibid',
                }

server = 'localhost'
port = 8789

def post_change_branch_tip(params):
    repository = urlparse(params.branch.base)[2]
    if repository.startswith('///'):
        repository = repository.replace('//', '', 1)

    if repository in repositories:
        factory = pb.PBClientFactory()
        reactor.connectTCP(server, port, factory)
        d = factory.getRootObject()
        d.addCallback(lambda root: root.callRemote('get_plugin', 'bzr', 'Bazaar'))
        d.addCallback(lambda bzr: bzr.callRemote('committed', repositories[repository], params.old_revno+1, params.new_revno))
        d.addErrback(lambda reason: util.println(reason.value))
        d.addCallback(lambda _: reactor.stop())
        reactor.run()

branch.Branch.hooks.install_named_hook('post_change_branch_tip', post_change_branch_tip, 'Trigger Ibid to announce the commit')

# vi: set et sta sw=4 ts=4:
