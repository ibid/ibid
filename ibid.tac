#!/usr/bin/python

import sys
sys.path.append("./lib/wokkel.egg")

from twisted.application import service
import ibid

application = service.Application("Ibid")
ibidService = service.MultiService()

ibid.setup(ibidService)

ibidService.setServiceParent(application)
