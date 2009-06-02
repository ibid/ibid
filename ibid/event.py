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

    def addresponse(self, response, params={}, processed=True):
        if response is None:
            # We want to detect this now, so we know which plugin is to blame
            raise Exception("Can't have a None response")
        elif isinstance(response, basestring) and params:
            self.responses.append(response % params)
        else:
            self.responses.append(response)

        if processed:
            self.processed = True

# vi: set et sta sw=4 ts=4:
