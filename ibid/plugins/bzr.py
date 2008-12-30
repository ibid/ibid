from cStringIO import StringIO
from time import strftime
from datetime import datetime

from bzrlib.branch import Branch
from bzrlib import log

import ibid
from ibid.plugins import Processor, match

help = {'bzr': 'Retrieves commit logs from a Bazaar repository.'}

class LogFormatter(log.LogFormatter):

	def ago(self, time):
		then = datetime.fromtimestamp(time)
		delta = datetime.now() - then
		ago = ''
		for name, value in (('year', delta.days/365), ('month', delta.days/30), ('day', delta.days), ('hour', delta.seconds/3600), ('minute', delta.seconds/60), ('second', delta.seconds)):
			if value >= 1 or name == 'second':
				ago = '%s %s%s' % (value, name, value != 1 and 's' or '')
				break

		return ago

	def log_revision(self, revision):
		self.to_file.write('Commit %s by %s %s ago: %s\n' % (revision.revno, self.short_author(revision.rev), self.ago(revision.rev.timestamp), revision.rev.message.replace('\n', '')))

class Bazaar(Processor):
	"""last commit | commit <revno>"""
	feature = 'bzr'

	def __init__(self, name):
		Processor.__init__(self, name)
		self.branch = Branch.open(self.repository)

	@match('^(?:last\s+)?commit(?:\s+(\d+))?$')
	def commit(self, event, revno):
		last = self.branch.revision_id_to_revno(self.branch.last_revision())

		if revno:
			revno = int(revno)
			if revno < 1 or revno > last:
				event.addresponse(u'No such revision')
				return
		else:
			revno = last

		f=StringIO();
		log.show_log(self.branch, LogFormatter(f), start_revision=revno, end_revision=revno, limit=1)
		f.seek(0)
		commits = f.readlines()

		for commit in commits:
			if event.source == 'http':
				event.addresponse({'reply': commit.strip(), 'source': self.source, 'target': self.channel})
			else:
				event.addresponse(commit.strip())
