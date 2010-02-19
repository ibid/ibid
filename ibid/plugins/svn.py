# Copyright (c) 2009-2010, Neil Blakey-Milner, Adrianna Pinska
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

"""
Configuration:

[plugins]
    [[svn]]
        [[[repositories]]]
            [[[[repo1]]]]
                url = https://...
                username = user1
                password = mypassword
            [[[[repo2]]]]
                url = https://...
                username = user2
                password = mypassword
            ...

"""

from datetime import datetime, timedelta
import logging
import os.path
from os import kill
from signal import SIGTERM
import textwrap
import ibid
from ibid.compat import ElementTree as ET, dt_strptime
from subprocess import Popen, PIPE
from time import time, sleep, mktime

# Can use either pysvn or command-line svn
try:
    import pysvn
except:
    pysvn = None

from ibid.plugins import Processor, match, RPC, authorise
from ibid.config import DictOption, FloatOption, Option, BoolOption
from ibid.utils import ago, format_date, human_join

features = {'svn': u'Retrieves commit logs from a Subversion repository.'}

HEAD_REVISION = object()

class Branch(object):
    def __init__(self, repository_name = None, url = None, username = None, password = None, multiline = False):
        self.repository = repository_name
        self.url = url
        self.username = username
        self.password = password
        self.multiline = multiline

    def get_commits(self, start_revision = None, end_revision = None, limit = None, full = False):
        """
        Get formatted commit messages for each of the commits in range
        [start_revision:end_revision], defaulting to the latest revision.
        """
        if not full: # such as None
            full = False

        if not start_revision:
            start_revision = HEAD_REVISION

        start_revision = self._convert_to_revision(start_revision)

        # If no end-revision and no limit given, set limit to 1
        if not end_revision:
            end_revision = 0
            if not limit:
                limit = 1

        end_revision = self._convert_to_revision(end_revision)

        log_messages = self.log(start_revision, end_revision, limit=limit, paths=full)
        commits = [self.format_log_message(log_message, full) for log_message in log_messages]

        return commits

    def _generate_delta(self, changed_paths):
        class T(object):
            pass

        delta = T()
        delta.basepath = "/"
        delta.added = []
        delta.modified = []
        delta.removed = []
        delta.renamed = []

        action_mapper = {
            'M': delta.modified,
            'A': delta.added,
            'D': delta.removed,
        }

        all_paths = [changed_path.path for changed_path in changed_paths]

        commonprefix = os.path.commonprefix(all_paths)

        # os.path.commonprefix will return "/e" if you give it "/etc/passwd"
        # and "/exports/foo", which is not what we want.  Remove until the last
        # "/" character.
        while commonprefix and commonprefix[-1] != "/":
            commonprefix = commonprefix[:-1]

        pathinfo = commonprefix

        if commonprefix.startswith("/trunk/"):
            commonprefix = "/trunk/"
            pathinfo = " [trunk]"

        if commonprefix.startswith("/branches/"):
            commonprefix = "/branches/%s" % (commonprefix.split('/')[2],)
            pathinfo = " [" + commonprefix.split('/')[2] + "]"

        if commonprefix.startswith("/tags/"):
            commonprefix = "/tags/%s" % (commonprefix.split('/')[2],)
            pathinfo = " [" + commonprefix.split('/')[2] + "]"

        for changed_path in changed_paths:
            action_mapper[changed_path.action].append([changed_path.path[len(commonprefix):], None])

        return pathinfo, delta

    def format_log_message(self, log_message, full=False):
        """
        author - string - the name of the author who committed the revision
        date - float time - the date of the commit
        message - string - the text of the log message for the commit
        revision - pysvn.Revision - the revision of the commit

        changed_paths - list of dictionaries. Each dictionary contains:
            path - string - the path in the repository
            action - string
            copyfrom_path - string - if copied, the original path, else None
            copyfrom_revision - pysvn.Revision - if copied, the revision of the original, else None
        """
        revision_number = log_message['revision'].number
        author = log_message['author']
        commit_message = log_message['message']
        timestamp = log_message['date']

        if full:
            pathinfo, delta = self._generate_delta(log_message['changed_paths'])
            changes = []

            if delta.added:
                if self.multiline:
                    changes.append('Added:\n\t%s' % '\n\t'.join([file[0] for file in delta.added]))
                else:
                    changes.append('Added: %s' % ', '.join([file[0] for file in delta.added]))
            if delta.modified:
                if self.multiline:
                    changes.append('Modified:\n\t%s' % '\n\t'.join([file[0] for file in delta.modified]))
                else:
                    changes.append('Modified: %s' % '\, '.join([file[0] for file in delta.modified]))
            if delta.removed:
                if self.multiline:
                    changes.append('Removed:\n\t%s' % '\n\t'.join([file[0] for file in delta.removed]))
                else:
                    changes.append('Removed: %s' % ', '.join([file[0] for file in delta.removed]))
            if delta.renamed:
                changes.append('Renamed: %s' % ', '.join(['%s => %s' % (file[0], file[1]) for file in delta.renamed]))

            timestamp_dt = datetime.utcfromtimestamp(timestamp)

            if self.multiline:
                commit = 'Commit %s by %s to %s%s on %s at %s:\n\n\t%s \n\n%s\n' % (
                    revision_number,
                    author,
                    self.repository,
                    pathinfo,
                    format_date(timestamp_dt, 'date'),
                    format_date(timestamp_dt, 'time'),
                    u'\n'.join(textwrap.wrap(commit_message, initial_indent="    ", subsequent_indent="    ")),
                    '\n\n'.join(changes))
            else:
                commit = 'Commit %s by %s to %s%s on %s at %s: %s (%s)\n' % (
                        revision_number,
                        author,
                        self.repository,
                        pathinfo,
                        format_date(timestamp_dt, 'date'),
                        format_date(timestamp_dt, 'time'),
                        commit_message.replace('\n', ' '),
                        '; '.join(changes))
        else:
            commit = 'Commit %s by %s to %s %s ago: %s\n' % (
                revision_number,
                author,
                self.repository,
                ago(datetime.now() - datetime.fromtimestamp(timestamp), 2),
                commit_message.replace('\n', ' '))

        return commit

class PySVNBranch(Branch):
    def _call_command(self, command, *args, **kw):
        return command(self, username=self.username, password=self.password)(*args, **kw)

    def log(self, *args, **kw):
        """
        Low-level SVN logging call - returns lists of pysvn.PysvnLog objects.
        """
        return self._call_command(SVNLog, *args, **kw)

    def _convert_to_revision(self, revision):
        """
        Convert numbers to pysvn.Revision instances
        """
        if revision is HEAD_REVISION:
            return pysvn.Revision(pysvn.opt_revision_kind.head)

        try:
            revision.kind
            return revision
        except:
            return pysvn.Revision(pysvn.opt_revision_kind.number, revision)

class CommandLineChangedPath(object):
    pass

class TimeoutException(Exception):
    pass

class CommandLineRevision(object):
    def __init__(self, number):
        self.number = number

class CommandLineBranch(Branch):
    def __init__(self, repository_name = None, url = None, username = None, password = None, svn_command = 'svn', svn_timeout = 15.0, multiline = False):
        super(CommandLineBranch, self).__init__(repository_name, url, username, password, multiline=multiline)
        self.svn_command = svn_command
        self.svn_timeout = svn_timeout

    def _convert_to_revision(self, revision):
        return revision

    def log(self, start_revision, end_revision, paths=False, limit=1):
        cmd = ["svn", "log", "--no-auth-cache", "--non-interactive", "--xml"]

        if paths:
            cmd.append("-v")

        if self.username:
            cmd.append("--username")
            cmd.append(self.username)

        if self.password:
            cmd.append("--password")
            cmd.append(self.password)

        if limit:
            cmd.append("--limit")
            cmd.append(str(limit))

        if start_revision is None or start_revision is HEAD_REVISION:
            pass
        else:
            if not end_revision or start_revision == end_revision:
                if not limit:
                    # if start revision, no end revision (or equal to start_revision), and no limit given, just the revision
                    cmd.append("-r")
                    cmd.append(str(start_revision))
                    cmd.append("--limit")
                    cmd.append("1")
                else:
                    cmd.append("-r")
                    cmd.append("%i" % (start_revision,))
            else:
                cmd.append("-r")
                cmd.append("%i:%i" % (end_revision, start_revision))

        cmd.append(self.url)

        logging.getLogger('plugins.svn').info(str(cmd))

        svnlog = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        svnlog.stdin.close()

        start_time = time()

        while svnlog.poll() is None and time() - start_time < self.svn_timeout:
            sleep(0.1)

        if svnlog.poll() is None:
            kill(svnlog.pid, SIGTERM)
            raise TimeoutException()

        output = svnlog.stdout.read()
        error = svnlog.stderr.read()

        code = svnlog.wait()

        return self._xml_to_log_message(output)

    def _xmldate_to_timestamp(self, xmldate):
        xmldate = xmldate.split('.')[0]
        dt = dt_strptime(xmldate, "%Y-%m-%dT%H:%M:%S")
        return mktime(dt.timetuple())

    def _xml_to_log_message(self, output):
        """
        author - string - the name of the author who committed the revision
        date - float time - the date of the commit
        message - string - the text of the log message for the commit
        revision - pysvn.Revision - the revision of the commit

        changed_paths - list of dictionaries. Each dictionary contains:
            path - string - the path in the repository
            action - string
            copyfrom_path - string - if copied, the original path, else None
            copyfrom_revision - pysvn.Revision - if copied, the revision of the original, else None
        """
        doc = ET.fromstring(output)
        entries = []

        for logentry in doc:
            entry = dict(
                revision = CommandLineRevision(logentry.get('revision')),
                author = logentry.findtext("author"),
                date = self._xmldate_to_timestamp(logentry.findtext("date")),
                message = logentry.findtext("msg"),
            )

            entry['changed_paths'] = []
            paths = logentry.find("paths")
            if paths:
                for path in paths:
                    cp = CommandLineChangedPath()
                    cp.kind = path.get('kind')
                    cp.action = path.get('action')
                    cp.path = path.text
                    entry['changed_paths'].append(cp)
            entries.append(entry)
        return entries


class SVNCommand(object):
    def __init__(self, branch, username=None, password=None):
        self._branch = branch
        self._username = username
        self._password = password
        self._client = self._initClient(branch)

    def _initClient(self, branch):
        client = pysvn.Client()
        client.callback_get_login = self.get_login
        client.callback_cancel = CancelAfterTimeout()
        return client

    def get_login(self, realm, username, may_save):
        if self._username and self._password:
            return True, self._username.encode('utf-8'), self._password.encode('utf-8'), False
        return False, None, None, False

    def _initCommand(self):
        self._client.callback_cancel.start()
        pass

    def _destroyCommand(self):
        self._client.callback_cancel.done()
        pass

    def __call__(self, *args, **kw):
        self._initCommand()
        return self._command(*args, **kw)
        self._destroyCommand()

class SVNLog(SVNCommand):
    def _command(self, start_revision=HEAD_REVISION, end_revision=None, paths=False, stop_on_copy=True, limit=1):
        log_messages = self._client.log(self._branch.url, revision_start=start_revision, revision_end=end_revision, discover_changed_paths=paths, strict_node_history=stop_on_copy, limit=limit)
        return log_messages

class CancelAfterTimeout(object):
    """
    Implement timeout for if a SVN command is taking its time
    """
    def __init__(self, timeout = 15):
        self.timeout = timeout

    def start(self):
        self.cancel_at = datetime.now() + timedelta(seconds=self.timeout)

    def __call__(self):
        return datetime.now() > self.cancel_at

    def done(self):
        pass

class Subversion(Processor, RPC):
    u"""(last commit|commit <revno>) [to <repo>] [full]
    (svnrepos|svnrepositories)
    """
    feature = 'svn'
    autoload = False

    permission = u'svn'

    repositories = DictOption('repositories', 'Dict of repositories names and URLs')

    svn_command = Option('svn_command', 'Path to svn executable', 'svn')
    svn_timeout = FloatOption('svn_timeout', 'Maximum svn execution time (sec)', 15.0)
    multiline = BoolOption('multiline', 'Output multi-line (Jabber, Campfire)', False)

    def __init__(self, name):
        self.log = logging.getLogger('plugins.svn')
        Processor.__init__(self, name)
        RPC.__init__(self)

    def setup(self):
        self.branches = {}
        for name, repository in self.repositories.items():
            reponame = name.lower()
            if pysvn:
                self.branches[reponame] = PySVNBranch(reponame, repository['url'], username = repository['username'], password = repository['password'], multiline=self.multiline)
            else:
                self.branches[reponame] = CommandLineBranch(reponame, repository['url'], username = repository['username'], password = repository['password'], svn_command=self.svn_command, svn_timeout=self.svn_timeout, multiline=self.multiline)

    @match(r'^svn ?(?:repos|repositories)$')
    @authorise()
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
            ibid.dispatcher.send({'reply': commit.strip(),
                'source': repo['source'],
                'target': repo['channel'],
            })

        return True

    @match(r'^(?:last\s+)?commit(?:\s+(\d+))?(?:(?:\s+to)?\s+(\S+?))?(\s+full)?$')
    @authorise()
    def commit(self, event, revno, repository, full):

        if repository == "full":
            repository = None
            full = True

        if full:
            full = True

        revno = revno and int(revno) or None
        commits = self.get_commits(repository, revno, full=full)

        if commits:
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
            (repository, branch) = self.branches.items()[0]

        if not start:
            start = HEAD_REVISION

        if not end:
            end = None

        commits = branch.get_commits(start, end_revision=end, full=full)
        return commits

# vi: set et sta sw=4 ts=4:
