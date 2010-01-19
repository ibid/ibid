#!/usr/bin/env python
# Copyright (c) 2008-2009, Jonathan Hitchcock, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from twisted.application import service
import ibid

application = service.Application("Ibid")
ibidService = service.MultiService()

ibid.setup({'config': 'ibid.ini'}, ibidService)

ibidService.setServiceParent(application)

# vi: set et sta sw=4 ts=4:
