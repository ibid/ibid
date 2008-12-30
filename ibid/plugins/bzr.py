from cStringIO import StringIO
from time import strftime
from datetime import datetime

from bzrlib.branch import Branch
from bzrlib import log

import ibid
from ibid.plugins import Processor, match

class LogFormatter(log.LogFormatter):

	def ago(self, time):
		then = datetime.utcfromtimestamp(time)
		delta = datetime.now() - then
		ago = ''
		if delta.days / 365:
			ago = '%s years' % (delta.days / 365)
		elif delta.days / 30:
			ago = '%s months' % (delta.days / 30)
		elif delta.days:
			ago = '%s days' % delta.days
		elif delta.seconds / 3600:
			ago = '%s hours' % (delta.seconds / 3600)
		elif delta.seconds / 60:
			ago = '%s minutes' % (delta.seconds / 60)
		else:
			ago = '%s seconds' % delta.seconds
		return ago

	def log_revision(self, revision):
		self.to_file.write('Commit %s by %s %s ago: %s\n' % (revision.revno, self.short_author(revision.rev), self.ago(revision.rev.timestamp), revision.rev.message.replace('\n', '')))

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
		log.show_log(self.branch, LogFormatter(f), start_revision=revno, end_revision=revno, limit=1)
		f.seek(0)
		commits = f.readlines()

		for commit in commits:
			if event.source == 'http':
				event.addresponse({'reply': commit.strip(), 'source': self.source, 'target': self.channel})
			else:
				event.addresponse(commit.strip())
