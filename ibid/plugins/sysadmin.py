# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import os
import re
from subprocess import Popen, PIPE

from ibid.compat import defaultdict
from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output, human_join, \
                       cacheable_download, json_webservice

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

        result = json_webservice(
            u'http://dde.debian.net/dde/q/aptfile/byfile/%s/%s' %
            (distro, term), {'t': 'json'})
        result = result['r']
        if result:
            if isinstance(result[0], list):
                numpackages = len(set(x[-1] for x in result))
                bypkg = map(lambda x: (x[-1], u'/'.join(x[:-1])), result)
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
