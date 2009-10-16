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

# vi: set et sta sw=4 ts=4:
