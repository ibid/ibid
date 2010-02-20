# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import os
import re
from subprocess import Popen, PIPE

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output, human_join, cacheable_download

features = {}

features['aptitude'] = {
    'description': u'Searches for packages',
    'categories': ('sysadmin', 'lookup',),
}
class Aptitude(Processor):
    u"""apt (search|show) <term>"""
    feature = ('aptitude',)

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
            for line in output.splitlines():
                if not description:
                    if line.startswith(u'Description:'):
                        description = u'%s:' % line.split(None, 1)[1]
                    elif line.startswith(u'Provided by:'):
                        provided = line.split(None, 2)[2]
                elif line != "":
                    description += u' ' + line.strip()
                else:
                    # More than one package listed
                    break
            if provided:
                event.addresponse(u'Virtual package provided by %s', provided)
            elif description:
                event.addresponse(description)
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
    u"""apt-file [search] <term>"""
    feature = ('apt-file',)

    aptfile = Option('apt-file', 'Path to apt-file executable', 'apt-file')

    def setup(self):
        if not file_in_path(self.aptfile):
            raise Exception("Cannot locate apt-file executable")

    @match(r'^apt-?file\s+(?:search\s+)?(.+)$')
    def search(self, event, term):
        apt = Popen([self.aptfile, 'search', term], stdout=PIPE, stderr=PIPE)
        output, error = apt.communicate()
        code = apt.wait()

        if code == 0:
            if output:
                output = unicode_output(output.strip())
                output = [line.split(u':')[0] for line in output.splitlines()]
                packages = sorted(set(output))
                event.addresponse(u'Found %(num)i packages: %(names)s', {
                    'num': len(packages),
                    'names': human_join(packages),
                })
            else:
                event.addresponse(u'No packages found')
        else:
            error = unicode_output(error.strip())
            if u"The cache directory is empty." in error:
                event.addresponse(u'Search error: apt-file cache empty')
            else:
                event.addresponse(u'Search error')
            raise Exception("apt-file: %s" % error)

features['man'] = {
    'description': u'Retrieves information from manpages.',
    'categories': ('sysadmin', 'lookup',),
}
class Man(Processor):
    u"""man [<section>] <page>"""
    feature = ('man',)

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
    u"""mac <address>"""
    feature = ('mac',)

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
