import ibid

class FakeConfig(dict):
    def __init__(self, basedict=None):
        if basedict is None: basedict = {}
        for name, value in basedict.iteritems():
            if isinstance(value, dict):
                value = FakeConfig(value)
            self[name] = value

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value
        

def set_config(config):
    ibid.config = FakeConfig(config)

# vi: set et sta sw=4 ts=4:
