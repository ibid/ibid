from urllib2 import urlopen

from bzrlib import branch

repository = '/srv/src/ibid/'
boturl = 'http://kennels.dyndns.org:8080/'

def post_change_branch_tip(params):
	if params.branch.base.endswith('//%s' % repository):
		for revno in xrange(params.old_revno+1, params.new_revno+1):
			urlopen('%s?m=commit+%s' % (boturl, revno)).close()

branch.Branch.hooks.install_named_hook('post_change_branch_tip', post_change_branch_tip, 'Trigger Ibid to announce the commit')
