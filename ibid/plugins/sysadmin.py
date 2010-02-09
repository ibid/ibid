# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import os
from collections import defaultdict
from os.path import exists
from subprocess import Popen, PIPE

from ibid.plugins import Processor, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output, human_join

help = {}

help['aptitude'] = u'Searches for packages'
class Aptitude(Processor):
    u"""apt (search|show) <term>"""
    feature = 'aptitude'

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

help['apt-file'] = u'Searches for packages containing the specified file'
class AptFile(Processor):
    u"""apt-file [search] <term>"""
    feature = 'apt-file'

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

help['man'] = u'Retrieves information from manpages.'
class Man(Processor):
    u"""man [<section>] <page>"""
    feature = 'man'

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

help['ports'] = u'Looks up port numbers for protocols'
class Ports(Processor):
    u"""port for <protocol>
    (tcp|udp) port <number>"""
    feature = 'ports'

    services = Option('services', 'Path to services file', '/etc/services')
    nmapservices = Option('nmap-services', "Path to Nmap's services file", '/usr/share/nmap/nmap-services')
    protocols = {}
    ports = {}

    def setup(self):
        filename = None
        if exists(self.nmapservices):
            filename = self.nmapservices
            nmap = True
        elif exists(self.services):
            filename = self.services
            nmap = False

        if not filename:
            raise Exception(u"Services file doesn't exist")

        self.protocols = defaultdict(list)
        self.ports = defaultdict(list)
        f = open(filename)
        for line in f.readlines():
            parts = line.split()
            if parts and not parts[0].startswith('#') and parts[0] != 'unknown':
                self.protocols[parts[0]].append(parts[1])
                self.ports[parts[1]].append(parts[0])
                if not nmap:
                    for proto in parts[2:]:
                        if proto.startswith('#'):
                            break
                        self.protocols[proto].append(parts[1])

    @match(r'^ports?\s+for\s+(.+)$')
    def portfor(self, event, protocol):
        if protocol.lower() in self.protocols:
            event.addresponse(human_join(self.protocols[protocol.lower()]))
        else:
            event.addresponse(u"I don't know about that protocol")

    @match(r'^(?:(udp|tcp|sctp)\s+)?port\s+(\d+)$')
    def port(self, event, transport, number):
        results = []
        if transport:
            results.extend(self.ports.get('%s/%s' % (number, transport.lower()), []))
        else:
            for transport in ('tcp', 'udp', 'sctp'):
                results.extend('%s (%s)' % (protocol, transport) for protocol in self.ports.get('%s/%s' % (number, transport.lower()), []))

        if results:
            event.addresponse(human_join(results))
        else:
            event.addresponse(u"I don't know about any protocols using that port")

# vi: set et sta sw=4 ts=4:
