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
    parser.add_option('-s', '--user-subdirectories',
                      dest='user_subdirs',
                      default=None, action='store_true',
                      help='Store branches in subdirectories named after each '
                      'user (default: auto-detect)')
    options, args = parser.parse_args()

    lp = Launchpad.login_with('update-branches', 'production')

    if (options.user_subdirs is None
            and detect_user_subdirs(options.root, lp.me.name)):
        options.user_subdirs = True

    project = lp.projects[options.project]

    if options.active_branches:
        branches = project.getBranches()
    else:
        branches = [mp.source_branch for mp in project.getMergeProposals()]
    update_branches(options.root, options.project, branches,
                    options.user_subdirs)


def detect_user_subdirs(root, lp_username):
    return (os.path.exists(os.path.join(root, lp_username))
            and not os.path.exists(os.path.join(root, lp_username, '.bzr')))


def update_branches(root, project_name, branches, user_subdirs):
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

        if user_subdirs:
            user_dir = os.path.join(root, user)
            if not os.path.isdir(user_dir):
                os.mkdir(user_dir)
        else:
            user_dir = root

        branch_dir = os.path.join(user_dir, branch_name)
        if os.path.isdir(branch_dir):
            subprocess.call(('bzr', 'pull', '--remember',
                             'lp:%s' % unique_name),
                            cwd=branch_dir)
        else:
            subprocess.call(('bzr', 'branch', 'lp:%s' % unique_name),
                            cwd=user_dir)


if __name__ == '__main__':
    main()

# vi: set et sta sw=4 ts=4:
