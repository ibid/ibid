#!/usr/bin/env python

from twisted.application import service
import ibid

application = service.Application("Ibid")
ibidService = service.MultiService()

ibid.setup({'config': 'ibid.ini'}, ibidService)

ibidService.setServiceParent(application)

# vi: set et sta sw=4 ts=4:
