# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from cStringIO import StringIO
from datetime import datetime
import logging

from bzrlib.branch import Branch
from bzrlib import log
from bzrlib.errors import NotBranchError, RevisionNotPresent

import ibid
from ibid.plugins import Processor, match, RPC, handler, periodic
from ibid.config import DictOption, IntOption
from ibid.utils import ago, format_date, human_join

features = {'bzr': {
    'description': u'Retrieves commit logs from a Bazaar repository.',
    'categories': ('development',),
}}

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

            timestamp = datetime.utcfromtimestamp(revision.rev.timestamp)
            commit = 'Commit %s by %s to %s on %s at %s: %s (%s)\n' % (
                    revision.revno,
                    self.short_author(revision.rev),
                    self.repository,
                    format_date(timestamp, 'date'),
                    format_date(timestamp, 'time'),
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
    usage = u"""(last commit|commit <revno>) [to <repo>] [full]
    repositories"""
    features = ('bzr',)
    autoload = False

    repositories = DictOption('repositories', 'Dict of repositories names and URLs')
    interval = IntOption('interval',
            'Interval inbetween checks for new revisions', 300)

    def __init__(self, name):
        self.log = logging.getLogger('plugins.bzr')
        Processor.__init__(self, name)
        RPC.__init__(self)

    def setup(self):
        self.branches = {}
        must_monitor = False
        for name, repository in self.repositories.items():
            try:
                self.branches[name.lower()] = Branch.open(repository['url'])
            except NotBranchError:
                self.log.error(u'%s is not a branch', repository)
                continue
            if repository.get('poll', 'False').lower() in ('yes', 'true'):
                must_monitor = True
        self.check.im_func.disabled = not must_monitor
        if must_monitor:
            self.seen_revisions = {}

    @match(r'^(?:repos|repositories)$')
    def handle_repositories(self, event):
        repositories = self.branches.keys()
        if repositories:
            event.addresponse(u'I know about: %s', human_join(sorted(repositories)))
        else:
            event.addresponse(u"I don't know about any repositories")

    def remote_committed(self, repository, start, end=None):
        commits = self.get_commits(repository, start, end)
        repo = self.repositories[repository]
        for commit in commits:
            ibid.dispatcher.send({'reply': commit,
                'source': repo['source'],
                'target': repo['channel'],
            })

        return True

    @match(r'^(?:last\s+)?commit(?:\s+(\d+))?(?:(?:\s+to)?\s+(\S+?))?(\s+full)?$')
    def commit(self, event, revno, repository, full):

        revno = revno and int(revno) or None
        commits = self.get_commits(repository, revno, full=full)

        output = u''
        for commit in commits:
            if commit:
                output += commit.strip()
        event.addresponse(output, conflate=False)

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

        for name, repository in self.repositories.iteritems():
            if (event.headers['X-Launchpad-Branch']
                    == repository.get('lp_branch', None)):
                self.remote_committed(name,
                    int(event.headers['X-Launchpad-Branch-Revision-Number']))

    @periodic(config_key='interval')
    def check(self, event):
        for name, repo in self.repositories.iteritems():
            if repo.get('poll', 'False').lower() not in ('yes', 'true'):
                continue
            branch = self.branches[name]
            lastrev = branch.last_revision()
            if name not in self.seen_revisions:
                self.seen_revisions[name] = lastrev
                continue
            if lastrev == self.seen_revisions[name]:
                continue

            try:
                commits = self.get_commits(name, None, False)
            except RevisionNotPresent:
                self.log.debug(u"Got a RevisionNotPresent, hoping it won't be there next time...")
                continue
            self.seen_revisions[name] = lastrev

            if commits:
                event.addresponse(unicode(commits[0].strip()),
                    source=repo['source'],
                    target=repo['channel'],
                    address=False)

# vi: set et sta sw=4 ts=4:
