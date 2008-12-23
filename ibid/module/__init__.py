class Module(object):

    def __init__(self, name):
        self.name = name

    def process(self, query):
        raise NotImplementedError

# vi: set et sta sw=4 ts=4:
