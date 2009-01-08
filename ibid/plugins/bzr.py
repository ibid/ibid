from cStringIO import StringIO
from time import strftime, localtime
from datetime import datetime

from bzrlib.branch import Branch
from bzrlib import log

import ibid
from ibid.plugins import Processor, match
from ibid.utils import ago

help = {'bzr': 'Retrieves commit logs from a Bazaar repository.'}

class LogFormatter(log.LogFormatter):

	def __init__(self, f, branch, full):
		log.LogFormatter.__init__(self, f)
		self.branch = branch
		self.full = full

	def log_revision(self, revision):
		if self.full:
			when = localtime(revision.rev.timestamp)
			delta = self.branch.repository.get_revision_delta(revision.rev.revision_id)
			changes = []

			if delta.added:
				changes.append('Added: %s' % ', '.join([file[0] for file in delta.added]))
			if delta.modified:
				changes.append('Modified: %s' % ', '.join([file[0] for file in delta.modified]))
			if delta.removed:
				changes.append('Removed: %s' % ', '.join([file[0] for file in delta.removed]))

			commit = 'Commit %s by %s on %s at %s: %s (%s)\n' % (revision.revno, self.short_author(revision.rev), strftime('%Y/%m/%d', when), strftime('%H:%M:%S', when), revision.rev.message.replace('\n', ' '), '; '.join(changes))
		else:
			commit = 'Commit %s by %s %s ago: %s\n' % (revision.revno, self.short_author(revision.rev), ago(datetime.now() - datetime.fromtimestamp(revision.rev.timestamp), 2), revision.rev.get_summary().replace('\n', ' '))
		self.to_file.write(commit)

class Bazaar(Processor):
	"""last commit | commit <revno>"""
	feature = 'bzr'

	def setup(self):
		self.branch = Branch.open(self.repository)

	@match(r'^(?:last\s+)?commit(?:\s+(\d+))?(\s+full)?$')
	def commit(self, event, revno, full):
		last = self.branch.revision_id_to_revno(self.branch.last_revision())

		if revno:
			revno = int(revno)
			if revno < 1 or revno > last:
				event.addresponse(u'No such revision')
				return
		else:
			revno = last

		f=StringIO();
		log.show_log(self.branch, LogFormatter(f, self.branch, full), start_revision=revno, end_revision=revno, limit=1)
		f.seek(0)
		commits = f.readlines()

		for commit in commits:
			if event.source == 'http':
				event.addresponse({'reply': commit.strip(), 'source': self.source, 'target': self.channel})
			else:
				event.addresponse(commit.strip())
