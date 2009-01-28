from cStringIO import StringIO
from datetime import datetime

from bzrlib.branch import Branch
from bzrlib import log
from bzrlib.errors import InvalidRevisionNumber, NotBranchError

import ibid
from ibid.plugins import Processor, match, RPC
from ibid.utils import ago

help = {'bzr': 'Retrieves commit logs from a Bazaar repository.'}

class LogFormatter(log.LogFormatter):

    def __init__(self, f, repository, branch, full, datetime_format):
        log.LogFormatter.__init__(self, f)
        self.branch = branch
        self.full = full
        self.repository = repository
        self.datetime_format = datetime_format

    def log_revision(self, revision):
        if self.full:
            when = datetime.fromtimestamp(revision.rev.timestamp)
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

            commit = 'Commit %s by %s to %s %s: %s (%s)\n' % (revision.revno, self.short_author(revision.rev), self.repository, when.strftime(self.datetime_format), revision.rev.message.replace('\n', ' '), '; '.join(changes))
        else:
            commit = 'Commit %s by %s to %s %s ago: %s\n' % (revision.revno, self.short_author(revision.rev), self.repository, ago(datetime.now() - datetime.fromtimestamp(revision.rev.timestamp), 2), revision.rev.get_summary().replace('\n', ' '))
        self.to_file.write(commit)

class Bazaar(Processor, RPC):
    """last commit to <repo> | commit <revno> [full]
    repositories"""
    feature = 'bzr'

    datetime_format = 'on %Y/%m/%d at %H:%M:%S'

    def __init__(self, name):
        Processor.__init__(self, name)
        RPC.__init__(self)

    def setup(self):
        self.branches = {}
        for name, repository in self.repositories.items():
            try:
                self.branches[name.lower()] = Branch.open(repository)
            except NotBranchError, e:
                print str(e)

    @match(r'^(?:repos|repositories)$')
    def handle_repositories(self, event):
        event.addresponse(', '.join(self.branches.keys()))

    def remote_committed(self, repository, start, end=None):
        commits = self.get_commits(repository, start, end)
        for commit in commits:
            ibid.dispatcher.send({'reply': commit, 'source': self.source, 'target': self.channel})

        return True

    @match(r'^(?:last\s+)?commit(?:\s+(\d+))?(?:(?:\s+to)?\s+(\S+?))?(\s+full)?$')
    def commit(self, event, revno, repository, full):

        revno = revno and int(revno) or None
        commits = self.get_commits(repository, revno, full=full)

        for commit in commits:
            if commit:
                if event.source == 'http':
                    event.addresponse({'reply': commit.strip(), 'source': self.source, 'target': self.channel})
                else:
                    event.addresponse(commit.strip())

    def get_commits(self, repository, start, end=None, full=None):
        branch = None
        if repository:
            repository = repository.lower()
            if repository not in self.branches:
                return None
            branch = self.branches[repository]

        if not branch:
            if len(self.branches) == 1:
                (repository, branch) = self.branches.items()[0]
            else:
                (repository, branch) = sorted(self.branches.iteritems(), reverse=True, key=lambda (k,v): v.repository.get_revision(v.last_revision_info()[1]).timestamp)[0]

        if not start:
            start = branch.revision_id_to_revno(branch.last_revision())

        f=StringIO();
        log.show_log(branch, LogFormatter(f, repository, branch, full, self.datetime_format), start_revision=start, end_revision=end or start)
        f.seek(0)
        commits = f.readlines()
        commits.reverse()
        return commits

# vi: set et sta sw=4 ts=4:
