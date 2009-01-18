#!/usr/bin/env python

from optparse import OptionParser

from twisted.internet import reactor
import ibid

parser = OptionParser(usage='%prog [options] <config filename>')
parser.add_option('-d', '--debug', dest='debug', action='store_true', help='Output debug messages')
options, args = parser.parse_args(values={})

options['config'] = len(args) > 0 and args[0] or 'ibid.ini'

ibid.setup(options)
reactor.run()

# vi: set et sta sw=4 ts=4:
