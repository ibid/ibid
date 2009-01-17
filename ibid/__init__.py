import logging
import logging.config

import sys
sys.path.append("./lib/wokkel.egg")
sys.path.insert(0, './lib')

import ibid.core
from ibid.config import FileConfig
from ibid.log import PythonExceptionLoggingObserver

sources = {}
config = {}
dispatcher = None
processors = []
reloader = None
databases = None
auth = None
service = None

def setup(service=None):
    logging.basicConfig(level=logging.INFO)

    service = service
    ibid.config = FileConfig("ibid.ini")
    ibid.config.merge(FileConfig("local.ini"))

    if 'logging' in ibid.config:
        logging.getLogger('core').info(u'Loading log configuration from %s', ibid.config['logging'])
        logging.config.fileConfig(ibid.config['logging'])

    observer = PythonExceptionLoggingObserver()
    observer.start()
     
    ibid.reload_reloader()
    ibid.reloader.reload_dispatcher()
    ibid.reloader.reload_databases()
    ibid.reloader.load_processors()
    ibid.reloader.load_sources(service)
    ibid.reloader.reload_auth()

def reload_reloader():
    try:
        reload(ibid.core)
        new_reloader = ibid.core.Reloader()
        ibid.reloader = new_reloader
        return True
    except:
        logging.getLogger('core').exception(u"Exception occured while reloading Reloader")
        return False

# vi: set et sta sw=4 ts=4:
