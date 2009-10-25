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
        return self[name]

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
        """
        if response is None:
            # We want to detect this now, so we know which plugin is to blame
            raise Exception("Can't have a None response")

        if isinstance(response, basestring) and params:
            response = response % params

        if not isinstance(response, dict):
            response = {'reply': response}

        for k, val in (('target', self.channel),
                ('source', self.source),
                ('address', True)):
            if k not in response:
                response[k] = val

        for arg, val in kwargs.iteritems():
            response[arg] = val

        if (response.get('action', False)
                and 'action' not in ibid.sources[response['source']].supports):
            response['reply'] = '* %s %s' % (
                    ibid.config['botname'],
                    response['reply'],
            )

        self.responses.append(response)

        if processed:
            self.processed = True

# vi: set et sta sw=4 ts=4:
