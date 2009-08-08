from cStringIO import StringIO
from datetime import datetime
import logging

from bzrlib.branch import Branch
from bzrlib import log
from bzrlib.errors import NotBranchError

import ibid
from ibid.plugins import Processor, match, RPC, handler
from ibid.config import Option, DictOption
from ibid.utils import ago, format_date, human_join

help = {'bzr': u'Retrieves commit logs from a Bazaar repository.'}

class LogFormatter(log.LogFormatter):

    def __init__(self, f, repository, branch, full):
        log.LogFormatter.__init__(self, f)
        self.branch = branch
        self.full = full
        self.repository = repository

    def log_revision(self, revision):
        if self.full:
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

            commit = 'Commit %s by %s to %s on %s at %s: %s (%s)\n' % (
                    revision.revno,
                    self.short_author(revision.rev),
                    self.repository,
                    format_date(revision.rev.timestamp, 'date'),
                    format_date(revision.rev.timestamp, 'time'),
                    revision.rev.message.replace('\n', ' '),
                    '; '.join(changes))
        else:
            commit = 'Commit %s by %s to %s %s ago: %s\n' % (
                    revision.revno,
                    self.short_author(revision.rev),
                    self.repository,
                    ago(datetime.now() - datetime.fromtimestamp(revision.rev.timestamp), 2),
                    revision.rev.get_summary().replace('\n', ' '))
        self.to_file.write(commit)

class Bazaar(Processor, RPC):
    u"""(last commit|commit <revno>) [to <repo>] [full]
    repositories"""
    feature = 'bzr'
    autoload = False

    repositories = DictOption('repositories', 'Dict of repository names and URLs')
    source = Option('source', 'Source to send commit notifications to')
    channel = Option('channel', 'Channel to send commit notifications to')
    launchpad_branches = DictOption('launchpad_branches', 'Branch paths in Launchpad mapped to names')

    def __init__(self, name):
        self.log = logging.getLogger('plugins.bzr')
        Processor.__init__(self, name)
        RPC.__init__(self)

    def setup(self):
        self.branches = {}
        for name, repository in self.repositories.items():
            try:
                self.branches[name.lower()] = Branch.open(repository)
            except NotBranchError, e:
                self.log.error(u'%s is not a branch', repository)

    @match(r'^(?:repos|repositories)$')
    def handle_repositories(self, event):
        repositories = self.branches.keys()
        if repositories:
            event.addresponse(u'I know about: %s', human_join(sorted(repositories)))
        else:
            event.addresponse(u"I don't know about any repositories")

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
        log.show_log(branch, LogFormatter(f, repository, branch, full), start_revision=start, end_revision=end or start)
        f.seek(0)
        commits = f.readlines()
        commits.reverse()
        return commits

    @handler
    def launchpad(self, event):
        if ibid.sources[event.source].type != 'smtp' \
                or 'X-Launchpad-Branch' not in event.headers:
            return

        event.processed = True

        if 'X-Launchpad-Branch' not in event.headers or 'X-Launchpad-Branch-Revision-Number' not in event.headers:
            return

        if event.headers['X-Launchpad-Branch'] in self.launchpad_branches:
            self.remote_committed(self.launchpad_branches[event.headers['X-Launchpad-Branch']], int(event.headers['X-Launchpad-Branch-Revision-Number']))

# vi: set et sta sw=4 ts=4:
