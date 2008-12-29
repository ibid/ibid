#!/usr/bin/env python

import sys
sys.path.append("./lib/wokkel.egg")
sys.path.insert(0, './lib')

from twisted.application import service
import ibid

application = service.Application("Ibid")
ibidService = service.MultiService()

ibid.setup(ibidService)

ibidService.setServiceParent(application)
