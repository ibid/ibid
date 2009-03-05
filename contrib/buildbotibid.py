import re
from buildbot.interfaces import IEmailLookup, IStatusReceiver
from buildbot.status import base
from buildbot.status.builder import Results
from twisted.web.client import getPage
from zope.interface import implements

class IdentityLookup(object):
    implements(IEmailLookup)
    
    def __init__(self):
        pass
    
    def getAddress(self, name):
        return name

class RegexLookup(object):
    implements(IEmailLookup)
    def __init__(self, pattern):
        self.pattern = pattern
    
    def getAddress(self, name):
        m = re.search(self.pattern, name)
        if m:
            return m.groups()[0]
        else:
            return name

class MailToUsernameLookup(RegexLookup):
    """
    Takes an email address (possibly including a name before <>) and turns
    it into a name which is just the part before the domain name.
    
    This is useful with bzr (and possibly other VCS), where $who is usually
    an email address, or of that form.
    """
    implements(IEmailLookup)
    
    def __init__(self, domain=None):
        usernamepart = "[^ <]+"
        if domain:
            pattern = '(%s)@%s' % (usernamepart, domain, )
            pattern = re.compile(pattern)
        else:
            pattern = re.compile('(%s)@' % (usernamepart, ))
        RegexLookup.__init__(self, pattern)

class IbidNotifier(base.StatusReceiverMultiService):
    """
    A basic Status plugin for Buildbot, which will notify a channel
    of a build result.
    """
    implements(IStatusReceiver)
    # Example url would be:
    # http://localhost:9000/buildbot/built
    # Note, don't add a trailing /
    def __init__(self, url, lookup=None):
        base.StatusReceiverMultiService.__init__(self)
        self.url = url
        if not lookup:
            self.lookup = IdentityLookup()
        else:
            self.lookup = lookup
    
    def setServiceParent(self, parent):
        base.StatusReceiverMultiService.setServiceParent(self, parent)
        self.status = self.parent.getStatus()
        self.status.subscribe(self)
    
    def builderAdded(self, name, builder):
        return self    

    def transformUsers(self, l):
        r = []
        for u in l:
            r.append(self.lookup.getAddress(u))
        return r
    
    def buildFinished(self, name, build, results):
        ss = build.getSourceStamp()
        branch = "%s/%s" % (ss.branch, name)
        rev = ss.revision
        person = ",".join(self.transformUsers(build.getResponsibleUsers()))
        result = Results[results]
        return getPage("%s?branch=%s&revision=%s&person=%s&result=%s" % \
                     (self.url, branch, rev, person, result))

# vi: set et sta sw=4 ts=4:
