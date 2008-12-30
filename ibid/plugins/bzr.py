from cStringIO import StringIO

from bzrlib.branch import Branch
from bzrlib import log

import ibid
from ibid.plugins import Processor, match

class Bazaar(Processor):

	def __init__(self, name):
		Processor.__init__(self, name)
		self.branch = Branch.open(self.repository)

	@match('^(last\s+)?commit(?:\s+(\d+))?$')
	def commit(self, event, last, revno):
		if last:
			revid = self.branch.last_revision()
			revno = self.branch.revision_id_to_revno(revid)
		elif revno:
			revno = int(revno)
		else:
			return

		f=StringIO();
		log.show_log(self.branch, log.LineLogFormatter(f), start_revision=revno, end_revision=revno, limit=1)
		f.seek(0)
		commits = f.readlines()

		event.responses.extend(commits)
		event.processed = True
