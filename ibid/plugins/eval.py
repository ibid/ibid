# Copyright (c) 2009-2010, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

try:
    import perl
except ImportError:
    pass

try:
    import lua
except ImportError:
    pass

from ibid.plugins import Processor, match, authorise

help = {'eval': u'Evaluates Python, Perl and Lua code.'}

class Python(Processor):
    u"""py <code>"""
    feature = 'eval'

    permission = u'eval'

    @match(r'^py(?:thon)?\s+(.+)$')
    @authorise()
    def eval(self, event, code):
        try:
            globals = {}
            exec('import os', globals)
            exec('import sys', globals)
            exec('import re', globals)
            exec('import time', globals)
            result = eval(code, globals, {})
        except Exception, e:
            result = e
        event.addresponse(repr(result))

class Perl(Processor):
    u"""pl <code>"""
    feature = 'eval'

    permission = u'eval'

    @match(r'^(?:perl|pl)\s+(.+)$')
    @authorise()
    def eval(self, event, code):
        try:
            result = perl.eval(code)
        except Exception, e:
            result = e

        event.addresponse(repr(result))

class Lua(Processor):
    u"""lua <code>"""
    feature = 'eval'

    permission = u'eval'

    @match(r'^lua\s+(.+)$')
    @authorise()
    def eval(self, event, code):
        try:
            result = lua.eval(code)
        except Exception, e:
            result = e

        event.addresponse(repr(result))

# vi: set et sta sw=4 ts=4:
