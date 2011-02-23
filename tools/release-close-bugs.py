#!/usr/bin/env python
# Copyright (c) 2011, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from launchpadlib.launchpad import Launchpad

launchpad = Launchpad.login_with('ibid-close-bugs', 'production')
ibid = launchpad.projects['ibid']
last_release = list(ibid.releases)[-1]

print "Closing 'Fix Committed' bugs for %s" % last_release.display_name
print "OK?"
input()

milestone = last_release.milestone
for task in milestone.searchTasks(status='Fix Committed'):
    print task
    task.status = 'Fix Released'
    task.lp_save()
