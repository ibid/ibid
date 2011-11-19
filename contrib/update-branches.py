#!/usr/bin/env python
# Copyright (c) 2011, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import optparse
import os
import subprocess
import sys

from launchpadlib.launchpad import Launchpad


def main():
    parser = optparse.OptionParser()
    parser.add_option('-a', '--acive-branches',
                      dest='active_branches',
                      default=False, action='store_true',
                      help='Pull all active branches, not just ones involved '
                           'in merge proposals')
    parser.add_option('-p', '--project', metavar='PROJECT',
                      default=os.path.basename(os.getcwd()),
                      help='LP Project (default: current directory name)')
    parser.add_option('-r', '--root', metavar='DIR',
                      default='.',
                      help='Target directory (default: .)')
    parser.add_option('-s', '--shallow',
                      default=False, action='store_true',
                      help='Store branches directly in the root '
                           '(default: user/branch)')
    parser.add_option('--anonymous',
                      default=False, action='store_true',
                      help='Log in to LP anonymously (may be confused by '
                           'identical commit counts')
    options, args = parser.parse_args()

    if options.anonymous:
        lp = Launchpad.login_anonymously('update-branches', 'production')
    else:
        lp = Launchpad.login_with('update-branches', 'production')

    project = lp.projects[options.project]

    if options.active_branches:
        branches = project.getBranches()
    else:
        branches = [mp.source_branch for mp in project.getMergeProposals()]
    update_branches(options.root, options.project, branches,
                    options.shallow)


def update_branches(root, project_name, branches, shallow):
    devnull = open('/dev/null', 'w')
    seen = set()
    for branch in branches:
        unique_name = branch.unique_name
        print 'lp:' + unique_name
        split_unique_name = unique_name.split('/')
        if len(split_unique_name) != 3:
            print >> sys.stderr, ('Unexpected branch name: lp:%s, skipping '
                                  % unique_name)
            continue
        user, project, branch_name = split_unique_name
        user = user[1:]
        if project != project_name:
            print >> sys.stderr, ('Unexpected project: lp:%s, skipping '
                                  % unique_name)
            continue

        if shallow:
            user_dir = root
        else:
            user_dir = os.path.join(root, user)
            if not os.path.isdir(user_dir):
                os.mkdir(user_dir)
            seen.add((user, branch_name))

        branch_dir = os.path.join(user_dir, branch_name)
        if os.path.isdir(branch_dir):
            id_ = branch.last_scanned_id
            if id_ == '<email address hidden>':
                id_ = str(branch.revision_count)
            if subprocess.call(('bzr', 'log', '-r', id_),
                               stdout=devnull, stderr=devnull,
                               cwd=branch_dir) == 0:
                print "Up to date"
            else:
                subprocess.call(('bzr', 'pull', '--remember',
                                 'lp:%s' % unique_name),
                                cwd=branch_dir)
        else:
            subprocess.call(('bzr', 'branch', 'lp:%s' % unique_name),
                            cwd=user_dir)

    if not shallow:
        for user in os.listdir(root):
            if user.startswith('.'):
                continue
            if not os.path.isdir(user):
                continue
            user_dir = os.path.join(root, user)
            for branch_name in os.listdir(user_dir):
                branch_dir = os.path.join(user_dir, branch_name)
                if not os.path.isdir(branch_dir):
                    continue
                if not os.path.isdir(os.path.join(branch_dir, '.bzr')):
                    continue
                if (user, branch_name) not in seen:
                    print ("Inactive local branch: %s/%s"
                          % (user, branch_name))


if __name__ == '__main__':
    main()

# vi: set et sta sw=4 ts=4:
