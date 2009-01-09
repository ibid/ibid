from cStringIO import StringIO
from time import strftime, localtime
from datetime import datetime
from urlparse import urlparse

from bzrlib.branch import Branch
from bzrlib import log
from bzrlib.errors import InvalidRevisionNumber

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
			if delta.renamed:
				changes.append('Renamed: %s' % ', '.join(['%s => %s' % (file[0], file[1]) for file in delta.renamed]))

			commit = 'Commit %s by %s on %s at %s: %s (%s)\n' % (revision.revno, self.short_author(revision.rev), strftime('%Y/%m/%d', when), strftime('%H:%M:%S', when), revision.rev.message.replace('\n', ' '), '; '.join(changes))
		else:
			commit = 'Commit %s by %s %s ago: %s\n' % (revision.revno, self.short_author(revision.rev), ago(datetime.now() - datetime.fromtimestamp(revision.rev.timestamp), 2), revision.rev.get_summary().replace('\n', ' '))
		self.to_file.write(commit)

class Bazaar(Processor):
	"""last commit | commit <revno> [full]"""
	feature = 'bzr'

	def setup(self):
		self.branches = {}
		for repository in self.repositories:
			path = urlparse(repository)[2].split('/')
			self.branches[(path[-1] or path[-2]).lower()] = Branch.open(repository)

	@match(r'^(?:last\s+)?commit(?:\s+(\d+))?(?:(?:\s+to)?\s+(\S+?))?(\s+full)?$')
	def commit(self, event, revno, repository, full):
		branch = None
		if repository:
			repository = repository.lower()
			if repository not in self.branches:
				event.addresponse(u"I don't know about that repository")
				return
			branch = self.branches[repository]

		if not branch:
			if len(self.branches) == 1:
				branch = self.branches.values()[0]
			else:
				branches = self.branches.values()
				branches.sort(reverse=True, key=lambda x: x.repository.get_revision(x.last_revision_info()[1]).timestamp)
				branch = branches[0]

		if revno:
			revno = int(revno)
			try:
				branch.check_revno(revno)
			except InvalidRevisionNumber:
				event.addresponse(u'No such revision')
				return
		else:
			last = branch.revision_id_to_revno(branch.last_revision())
			revno = last

		f=StringIO();
		log.show_log(branch, LogFormatter(f, branch, full), start_revision=revno, end_revision=revno, limit=1)
		f.seek(0)
		commits = f.readlines()

		for commit in commits:
			if event.source == 'http':
				event.addresponse({'reply': commit.strip(), 'source': self.source, 'target': self.channel})
			else:
				event.addresponse(commit.strip())
