# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import os
import re
from subprocess import Popen, PIPE
from urllib2 import HTTPError

from ibid.compat import defaultdict
from ibid.plugins import Processor, match
from ibid.config import DictOption, Option
from ibid.utils import cacheable_download, file_in_path, generic_webservice, \
                       human_join, json_webservice, plural, unicode_output

features = {}

features['aptitude'] = {
    'description': u'Searches for packages',
    'categories': ('sysadmin', 'lookup',),
}
class Aptitude(Processor):
    usage = u'apt (search|show) <term>'
    features = ('aptitude',)

    aptitude = Option('aptitude', 'Path to aptitude executable', 'aptitude')

    bad_search_strings = (
        "?action", "~a", "?automatic", "~A", "?broken", "~b",
        "?config-files", "~c", "?garbage", "~g", "?installed", "~i",
        "?new", "~N", "?obsolete", "~o", "?upgradable", "~U",
        "?user-tag", "?version", "~V"
    )

    def setup(self):
        if not file_in_path(self.aptitude):
            raise Exception("Cannot locate aptitude executable")

    def _check_terms(self, event, term):
        "Check for naughty users"

        for word in self.bad_search_strings:
            if word in term:
                event.addresponse(u"I can't tell you about my host system. Sorry")
                return False

        if term.strip().startswith("-"):
            event.addresponse(False)
            return False

        return True

    @match(r'^(?:apt|aptitude|apt-get|apt-cache)\s+search\s+(.+)$')
    def search(self, event, term):

        if not self._check_terms(event, term):
            return

        apt = Popen([self.aptitude, 'search', '-F', '%p', term], stdout=PIPE, stderr=PIPE)
        output, error = apt.communicate()
        code = apt.wait()

        if code == 0:
            if output:
                output = unicode_output(output.strip())
                output = [line.strip() for line in output.splitlines()]
                event.addresponse(u'Found %(num)i packages: %(names)s', {
                    'num': len(output),
                    'names': human_join(output),
                })
            else:
                event.addresponse(u'No packages found')
        else:
            error = unicode_output(error.strip())
            if error.startswith(u"E: "):
                error = error[3:]
            event.addresponse(u"Couldn't search: %s", error)

    @match(r'^(?:apt|aptitude|apt-get)\s+show\s+(.+)$')
    def show(self, event, term):

        if not self._check_terms(event, term):
            return

        apt = Popen([self.aptitude, 'show', term], stdout=PIPE, stderr=PIPE)
        output, error = apt.communicate()
        code = apt.wait()

        if code == 0:
            description = None
            provided = None
            output = unicode_output(output)
            real = True
            for line in output.splitlines():
                if not description:
                    if line.startswith(u'Description:'):
                        description = u'%s:' % line.split(None, 1)[1]
                    elif line.startswith(u'Provided by:'):
                        provided = line.split(None, 2)[2]
                    elif line == u'State: not a real package':
                        real = False
                elif line != "":
                    description += u' ' + line.strip()
                else:
                    # More than one package listed
                    break
            if provided:
                event.addresponse(u'Virtual package provided by %s', provided)
            elif description:
                event.addresponse(description)
            elif not real:
                event.addresponse(u'Virtual package, not provided by anything')
            else:
                raise Exception("We couldn't successfully parse aptitude's output")
        else:
            error = unicode_output(error.strip())
            if error.startswith(u"E: "):
                error = error[3:]
            event.addresponse(u"Couldn't find package: %s", error)

features['apt-file'] = {
    'description': u'Searches for packages containing the specified file',
    'categories': ('sysadmin', 'lookup',),
}
class AptFile(Processor):
    usage = u'apt-file [search] <term> [on <distribution>[/<architecture>]]'
    features = ('apt-file',)

    distro = Option('distro', 'Default distribution to search', 'sid')
    arch = Option('arch', 'Default distribution to search', 'i386')

    @match(r'^apt-?file\s+(?:search\s+)?(\S+)'
           r'(?:\s+[oi]n\s+(\S+?)(?:[/-](\S+))?)?$')
    def search(self, event, term, distro, arch):
        distro = distro and distro.lower() or self.distro
        arch = arch and arch.lower() or self.arch
        distro = distro + u'-' + arch
        if distro == u'all-all':
            distro = u'all'
        if '/' in distro + term or '?' in distro + term:
            return

        result = json_webservice(
            u'http://dde.debian.net/dde/q/aptfile/byfile/%s/%s' %
            (distro, term), {'t': 'json'})
        result = result['r']
        if result:
            if isinstance(result[0], list):
                bypkg = map(lambda x: (x[-1], u'/'.join(x[:-1])), result)
                numpackages = len(bypkg)
                packages = defaultdict(list)
                for p, arch in bypkg:
                    packages[p].append(arch)
                packages = map(lambda i: u'%s [%s]' % (i[0], u', '.join(i[1])),
                               packages.iteritems())
            else:
                numpackages = len(result)
                packages = result
            event.addresponse(u'Found %(num)i packages: %(names)s', {
                'num': numpackages,
                'names': human_join(packages),
            })
        else:
            event.addresponse(u'No packages found')

features['debian-bts'] = {
    'description': u'Searches the Debain Bug Tracking System',
    'categories': ('sysadmin', 'lookup',),
}
class DebianBTS(Processor):
    usage = u"""debian bug #<number>
    debian bugs in <package> [/search/]
    """
    features = ('debian-bts',)

    @match(r'^deb(?:ian\s+)?bug\s+#?([0-9]+)$')
    def lookup(self, event, bug_number):
        bug_number = int(bug_number)
        try:
            result = json_webservice(
                u'http://dde.debian.net/dde/q/bts/bynumber/%i' % bug_number,
                {'t': 'json'})
        except HTTPError, e:
            if e.code == 400:
                event.addresponse(
                        u"Sorry, but I can't find a bug of that number.")
                return
            else:
                raise
        bug = result['r']

        tags = bug['tags']
        if bug['pending'] != 'pending':
            tags.append(bug['pending'])
        if tags:
            tags = ', ' + ', '.join(bug['tags'])
        else:
            tags = ''

        package = ''
        if not bug['subject'].startswith(bug['package'] + ':'):
            package = bug['package']
        if (bug['source']
                and bug['package'] != bug['source']
                and not bug['package'].startswith('src:')
                and not bug['found_versions']):
            if package:
                package += ' (src:%s)' % bug['source']
            else:
                package = 'src:' + bug['source']
        if bug['found_versions']:
            if package:
                package += ' '
            package += human_join(bug['found_versions'])
        if package:
            package = ' In %s,' % package

        affects = ''
        if bug['affects']:
            affects = ' Affects %s,' % bug['affects']

        blocked = ''
        if bug['blockedby']:
            blocked = map(int, bug['blockedby'].split())
            blocked.sort()
            blocked = map(str, blocked)
            if len(blocked) > 5:
                blocked = blocked[:5] + ['others']
            blocked = ' Blocked by %s,' + human_join(blocked)

        merged = ''
        if bug['mergedwith']:
            merged = ' Merged with %s,' % bug['mergedwith']

        event.addresponse(
            u'%(archived)s"%(subject)s" [%(severity)s%(tags)s]%(package)s'
            u'%(affects)s%(merged)s%(blocked_by)s'
            u' http://bugs.debian.org/%(bug_num)i', {
                'affects': affects,
                'archived': bug['archived'] and 'Archived: ' or '',
                'blocked_by': blocked,
                'bug_num': bug_number,
                'merged': merged,
                'package': package,
                'severity': bug['severity'],
                'subject': bug['subject'],
                'tags': tags,
            })

    @match(r'^deb(?:ian\s+)?bugs?\s+in\s+(\S+)(?:\s+/(.+)/)?$')
    def search(self, event, package, search):
        if '/' in package or '?' in package:
            return
        package = package.lower()
        if search is not None:
            search = search.lower()
        result = json_webservice(
            u'http://dde.debian.net/dde/q/bts/bypackage/%s' % package,
            {'t': 'json'})
        bugs = result['r']
        if not bugs:
            event.addresponse(u"Sorry, I couldn't find any open bugs on %s",
                    package)
            return

        severities = {
            'critical': 4,
            'grave': 3,
            'serious': 2,
            'important': 1,
            'normal': 0,
            'minor': -1,
            'wishlist': -2,
        }

        buglist = []
        for b in bugs.itervalues():
            if search and search not in b['subject'].lower():
                continue

            tags = b['tags']
            if b['pending'] != 'pending':
                tags.append(b['pending'])
            if tags:
                tags = ', ' + ', '.join(b['tags'])
            else:
                tags = ''

            body = '%s [%s%s]' % (b['subject'], b['severity'], tags)
            sev = 0 - severities.get(b['severity'], 0)
            buglist.append((b['bug_num'], sev, body))
        buglist.sort()
        if not buglist:
            event.addresponse(u"Sorry, I couldn't find any open bugs matching "
                              u"your query")
            return
        event.addresponse(u'Found %(count)i matching %(plural)s: %(bugs)s', {
            'count': len(buglist),
            'plural': plural(len(buglist), u'bug', u'bugs'),
            'bugs': ', '.join('%i: %s' % (b[0], b[2]) for b in buglist)
        })

features['rmadison'] = {
    'description': u'Shows package versions in Debian and Ubuntu distributions',
    'categories': ('sysadmin', 'lookup',),
}
class RMadison(Processor):
    usage = u"""what versions of <package> are in <distro>[/<verison>]
    rmadison <package> [in <distro>[/<verison>]]
    """
    features = ('rmadison',)
    rmadison_sources = DictOption('rmadison_sources', "Rmadison service URLs", {
        'debian': 'http://qa.debian.org/madison.php',
        'bpo': 'http://www.backports.org/cgi-bin/madison.cgi',
        'debug': 'http://debug.debian.net/cgi-bin/madison.cgi',
        'ubuntu': 'http://people.canonical.com/~ubuntu-archive/madison.cgi',
        'udd': 'http://qa.debian.org/cgi-bin/madison.cgi',
    })

    @match(r'^(?:what\s+)?versions?\s+of\s+(\S+)\s+(?:are\s+)?'
            r'in\s+(\S+?)(?:[\s/]+(\S+))?$')
    def english_rmadison(self, event, package, distro, release):
        self.rmadison(event, package, distro, release)

    @match(r'^rmadison\s+(\S+)(?:\s+in\s+(\S+?)(?:[\s/]+(\S+))?)?$')
    def rmadison(self, event, package, distro, release):
        distro = distro and distro.lower() or 'all'
        params = {
            'package': package.lower(),
            'text': 'on',
        }
        if release is not None:
            params['s'] = release.lower()
        if distro == 'all':
            params['table'] = 'all'
            distro = 'udd'
        if distro not in self.rmadison_sources:
            event.addresponse(
                    "I'm sorry, but I don't have a madison source for %s",
                    distro)
            return
        table = generic_webservice(self.rmadison_sources[distro], params)
        table = table.strip().splitlines()
        if table[0] == 'Traceback (most recent call last):':
            # Not very REST
            event.addresponse(u"Whoops, madison couldn't understand that: %s",
                    table[-1])
        versions = []
        for row in table:
            row = [x.strip() for x in row.split('|')]
            if versions and versions[-1][0] == row[1]:
                versions[-1].append(row[2])
            else:
                versions.append([row[1], row[2]])
        versions = human_join(u'%s (%s)' % (r[0], u', '.join(r[1:]))
                              for r in versions)
        if versions:
            event.addresponse(versions)
        else:
            event.addresponse(u"Sorry, I can't find a package called %s",
                              package.lower())

features['man'] = {
    'description': u'Retrieves information from manpages.',
    'categories': ('sysadmin', 'lookup',),
}
class Man(Processor):
    usage = u'man [<section>] <page>'
    features = ('man',)

    man = Option('man', 'Path of the man executable', 'man')

    def setup(self):
        if not file_in_path(self.man):
            raise Exception("Cannot locate man executable")

    @match(r'^man\s+(?:(\d)\s+)?(\S+)$')
    def handle_man(self, event, section, page):
        command = [self.man, page]
        if section:
            command.insert(1, section)

        if page.strip().startswith("-"):
            event.addresponse(False)
            return

        env = os.environ.copy()
        env["COLUMNS"] = "500"

        man = Popen(command, stdout=PIPE, stderr=PIPE, env=env)
        output, error = man.communicate()
        code = man.wait()

        if code != 0:
            event.addresponse(u'Manpage not found')
        else:
            output = unicode_output(output.strip(), errors="replace")
            output = output.splitlines()
            index = output.index('NAME')
            if index:
                event.addresponse(output[index+1].strip())
            index = output.index('SYNOPSIS')
            if index:
                event.addresponse(output[index+1].strip())

features['mac'] = {
    'description': u'Finds the organization owning the specific MAC address.',
    'categories': ('sysadmin', 'lookup',),
}
class Mac(Processor):
    usage = u'mac <address>'
    features = ('mac',)

    @match(r'^((?:mac|oui|ether(?:net)?(?:\s*code)?)\s+)?((?:(?:[0-9a-f]{2}(?(1)[:-]?|:))){2,5}[0-9a-f]{2})$')
    def lookup_mac(self, event, _, mac):
        oui = mac.replace('-', '').replace(':', '').upper()[:6]
        ouis = open(cacheable_download('http://standards.ieee.org/regauth/oui/oui.txt', 'sysadmin/oui.txt'))
        match = re.search(r'^%s\s+\(base 16\)\s+(.+?)$' % oui, ouis.read(), re.MULTILINE)
        ouis.close()
        if match:
            name = match.group(1).decode('utf8').title()
            event.addresponse(u"That belongs to %s", name)
        else:
            event.addresponse(u"I don't know who that belongs to")

# vi: set et sta sw=4 ts=4:
