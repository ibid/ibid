from urlparse import urlparse
from urllib2 import urlopen, URLError
import socket

from bzrlib import branch

repositories =  {   '/srv/src/ibid/': 'ibid',
                }
boturl = 'http://kennels.dyndns.org:8080'

socket.setdefaulttimeout(30)

def post_change_branch_tip(params):
    repository = urlparse(params.branch.base)[2]
    if repository.startswith('///'):
        repository = repository.replace('//', '', 1)
    if repository in repositories:
        try:
            urlopen('%s/bzr/committed/%s/%s/%s' % (boturl, repositories[repository], params.old_revno+1, params.new_revno)).close()
        except URLError, e:
            print u"Couldn't notify Ibid of commit: %s" % (e.reason,)

branch.Branch.hooks.install_named_hook('post_change_branch_tip', post_change_branch_tip, 'Trigger Ibid to announce the commit')

# vi: set et sta sw=4 ts=4:
