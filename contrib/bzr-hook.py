from urllib2 import urlopen

from bzrlib import branch

def post_change_branch_tip(params):
	if params.branch.base.endswith('///srv/src/ibid/'):
		f = urlopen('http://kennels.dyndns.org:8080/?m=commit+%s' % params.new_revno)
		f.read()
		f.close()

branch.Branch.hooks.install_named_hook('post_change_branch_tip', post_change_branch_tip, 'Trigger Ibid to announce the commit')
