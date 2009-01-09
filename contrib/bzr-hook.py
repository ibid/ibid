from urlparse import urlparse
from urllib2 import urlopen

from bzrlib import branch

repositories =	{	'/srv/src/ibid/': 'ibid',
				}
boturl = 'http://kennels.dyndns.org:8080/'

def post_change_branch_tip(params):
	repository = urlparse(params.branch.base)[2]
	if repository.startswith('///'):
		repository = repository.replace('//', '', 1)
	if repository in repositories:
		for revno in xrange(params.old_revno+1, params.new_revno+1):
			urlopen('%s?m=commit+%s+%s' % (boturl, revno, repositories[repository])).close()

branch.Branch.hooks.install_named_hook('post_change_branch_tip', post_change_branch_tip, 'Trigger Ibid to announce the commit')
