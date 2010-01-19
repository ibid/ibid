# Copyright (c) 2008-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

import warnings

import ibid

class Event(dict):

    def __init__(self, source, type):
        self.source = source
        self.type = type
        self.responses = []
        self.sender = {}
        self.processed = False

    def __getattr__(self, name):
        if name == 'session' and 'session' not in self:
            self['session'] = ibid.databases.ibid()
        try:
            return self[name]
        except KeyError, e:
            raise AttributeError(e)

    def __setattr__(self, name, value):
        self[name] = value

    def addresponse(self, response, params={}, processed=True, **kwargs):
        """Add a response to an event.
        By default it'll return to the same source channel.

        Will add any of the following options to the response:
        source: Destination Source
        target: Destination user / channel
        action: True for actions
        notice: True for IRC Notices
        address: False to suppress user addressing, in public
        conflate: False to suppress conflation and truncation of lines in
                  sources like IRC and SILC that don't support newlines
        """
        if response is None:
            # We want to detect this now, so we know which plugin is to blame
            raise Exception("Can't have a None response")

        if isinstance(params, (tuple, list)):
            warnings.warn(
                u'addresponse() params should be a single item or dict. '
                u"You really shouldn't use tuples / lists as they can cause "
                u'difficulties with translation later.',
                SyntaxWarning, stacklevel=2)

        if isinstance(response, basestring) and params:
            response = response % params

        if isinstance(response, str):
            warnings.warn(
                u"addresponse() response should be unicode, not a byte string",
                UnicodeWarning, stacklevel=2)

        if not isinstance(response, dict):
            response = {'reply': response}

        for k, val in (('target', self.get('channel', None)),
                       ('source', self.source),
                       ('address', True),
                       ('conflate', True)):
            if k not in response:
                response[k] = val

        for arg, val in kwargs.iteritems():
            response[arg] = val

        self.responses.append(response)

        if processed:
            self.processed = True

# vi: set et sta sw=4 ts=4:
