import logging
import logging.config
from os import makedirs
from os.path import join, dirname, expanduser, exists
from ConfigParser import SafeConfigParser

import sys
sys.path.insert(0, '%s/lib' % dirname(__file__))

import twisted.python.log

import ibid.core
from ibid.compat import defaultdict
from ibid.config import FileConfig

class InsensitiveDict(dict):
    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.lower(), value)

    def __contains__(self, key):
        return dict.__contains__(self, key.lower())

sources = InsensitiveDict()
config = {}
dispatcher = None
processors = []
reloader = None
databases = None
auth = None
service = None
options = {}
rpc = {}
channels = defaultdict(lambda: defaultdict(set))

def twisted_log(eventDict):
    log = logging.getLogger('twisted')
    if 'failure' in eventDict:
        log.error(eventDict.get('why') or 'Unhandled exception' + '\n' + str(eventDict['failure'].getTraceback()))
    elif 'warning' in eventDict:
        log.warning(eventDict['warning'])
    else:
        log.debug(' '.join([str(m) for m in eventDict['message']]))

def setup(opts, service=None):
    service = service
    for key, value in opts.items():
        options[key] = value
    options['base'] = dirname(options['config'])

    # Get Twisted to log to Python logging
    twisted.python.log.startLoggingWithObserver(twisted_log)

    # Undo Twisted logging's redirection of stdout and stderr
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    logging.basicConfig(level=logging.INFO)

    if not exists(options['config']):
        raise IbidException('Cannot find configuration file %s' % options['config'])

    ibid.config = FileConfig(options['config'])
    ibid.config.merge(FileConfig(join(options['base'], 'local.ini')))

    if 'logging' in ibid.config:
        logging.getLogger('core').info(u'Loading log configuration from %s', ibid.config['logging'])
        create_logdirs(ibid.config['logging'])
        logging.config.fileConfig(join(options['base'], expanduser(ibid.config['logging'])))

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

def create_logdirs(configfile):
    config = SafeConfigParser()
    config.read(configfile)

    if config.has_option('handlers', 'keys'):
        handlers = config.get('handlers', 'keys').split(',')
        for handler in handlers:
            section = 'handler_' + handler
            if config.has_option(section, 'class') and config.get(section, 'class') in ('FileHandler', 'handlers.RotatingFileHandler', 'handlers.TimedRotatingFileHandler'):
                if config.has_option(section, 'args'):
                    try:
                        args = eval(config.get(section, 'args'))
                    except Exception:
                        continue
                    if isinstance(args, tuple) and len(args) > 0:
                        dir = dirname(args[0])
                        if not exists(dir):
                            makedirs(dir)

class IbidException(Exception):
    pass

class AuthException(IbidException):
    pass

class SourceException(IbidException):
    pass

# vi: set et sta sw=4 ts=4:
