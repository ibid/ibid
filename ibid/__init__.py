import ibid.core

sources = {}
config = {}
dispatcher = None
processors = []
reloader = None
databases = {}

def reload_reloader():
    reload(ibid.core)
    new_reloader = ibid.core.Reloader()
    ibid.reloader = new_reloader

# vi: set et sta sw=4 ts=4:
