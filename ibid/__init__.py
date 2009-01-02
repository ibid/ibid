from traceback import print_exc

import sys
sys.path.append("./lib/wokkel.egg")
sys.path.insert(0, './lib')

import ibid.core
from ibid.config import FileConfig

sources = {}
config = {}
dispatcher = None
processors = []
reloader = None
databases = None
auth = None
service = None

def setup(service=None):
    service = service
    ibid.config = FileConfig("ibid.ini")
    ibid.config.merge(FileConfig("local.ini"))
    ibid.reload_reloader()
    ibid.reloader.reload_dispatcher()
    ibid.reloader.load_processors()
    ibid.reloader.load_sources(service)
    ibid.reloader.reload_databases()
    ibid.reloader.reload_auth()

def reload_reloader():
    try:
        reload(ibid.core)
        new_reloader = ibid.core.Reloader()
        ibid.reloader = new_reloader
        return True
    except:
        print_exc()
        return False

# vi: set et sta sw=4 ts=4:
