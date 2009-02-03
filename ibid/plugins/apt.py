from subprocess import Popen, PIPE

from ibid.plugins import Processor, match
from ibid.config import Option

help = {}

help['aptitude'] = u'Searches for packages'
class Aptitude(Processor):
    """(apt|aptitude|apt-get) [search] <term>"""
    feature = 'aptitude'

    aptitude = Option('aptitude', 'Path to aptitude executable', 'aptitude')

    @match(r'^(?:apt|aptitude|apt-get)\s+(?:search\s+)(.+)$')
    def search(self, event, term):
        apt = Popen([self.aptitude, 'search', '-F', '%p', term], stdout=PIPE, stderr=PIPE)
        output, error = apt.communicate()
        code = apt.wait()

        if code == 0:
            if output:
                event.addresponse(u', '.join(line.strip() for line in output.splitlines()))
            else:
                event.addresponse(u'No packages found')

    @match(r'(?:apt|aptitude|apt-get)\s+(?:show\s+)(.+)$')
    def show(self, event, package):
        apt = Popen([self.aptitude, 'show', package], stdout=PIPE, stderr=PIPE)
        output, error = apt.communicate()
        code = apt.wait()

        if code == 0:
            description = None
            for line in output.splitlines():
                if not description:
                    if line.startswith('Description:'):
                        description = u'%s:' % line.replace('Description:', '', 1).strip()
                else:
                    description += ' ' + line.strip()
            if output:
                event.addresponse(description)
            else:
                event.addresponse(u'No such package')
    
help['apt-file'] = u'Searches for packages containing the specified file'
class AptFile(Processor):
    """apt-file [search] <term>"""
    feature = 'apt-file'

    aptfile = Option('apt-file', 'Path to apt-file executable', 'apt-file')

    @match(r'^apt-?file\s+(?:search\s+)?(.+)$')
    def search(self, event, term):
        apt = Popen([self.aptfile, 'search', term], stdout=PIPE, stderr=PIPE)
        output, error = apt.communicate()
        code = apt.wait()

        if code == 0:
            if output:
                event.addresponse(u', '.join(line.split(':')[0] for line in output.splitlines()))
            else:
                event.addresponse(u'No packages found')

# vi: set et sta sw=4 ts=4:
