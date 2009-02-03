from subprocess import Popen, PIPE

from ibid.plugins import Processor, match, Option

help = {}

help['aptitude'] = u'Searches for packages'
class Aptitude(Processor):
    """(apt|aptitude|apt-get) [search] <term>"""
    feature = 'aptitude'

    aptitude = Option('aptitude', 'Path to aptitude executable', 'aptitude')

    @match(r'^(?:apt|aptitude|apt-get)\s+(?:search\s+)?(.+)$')
    def search(self, event, term):
        apt = Popen([self.aptitude, 'search', '-F', '%p', term], stdout=PIPE, stderr=PIPE)
        output, error = apt.communicate()
        code = apt.wait()

        if code == 0:
            if output:
                event.addresponse(u', '.join(line.strip() for line in output.splitlines()))
            else:
                event.addresponse(u'No packages found')
    
# vi: set et sta sw=4 ts=4:
