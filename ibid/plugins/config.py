from os.path import join
import logging

import ibid
from ibid.config import FileConfig
from ibid.plugins import Processor, match, authorise

help = {'config': u'Gets and sets configuration settings, and rereads the configuration file.'}

log = logging.getLogger('plugins.config')

class Config(Processor):
    u"""reread config
    set config <name> to <value>
    get config <name>"""
    feature = 'config'

    priority = -10
    permission = u'config'

    @match(r'^reread\s+config$')
    @authorise
    def reload(self, event):
        ibid.config.reload()
        ibid.config.merge(FileConfig(join(ibid.options['base'], 'local.ini')))
        ibid.reloader.reload_config()
        event.addresponse(True)
        log.info(u'Reread configuration file')

    @match(r'^(?:set\s+config|config\s+set)\s+(\S+?)(?:\s+to\s+|\s*=\s*)(\S.*?)$')
    @authorise
    def set(self, event, key, value):
        config = ibid.config
        for part in key.split('.')[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]

        if ',' in value:
            config[key.split('.')[-1]] = [part.strip() for part in value.split(',')]
        else:
            config[key.split('.')[-1]] = value
        ibid.config.write()
        ibid.reloader.reload_config()
        log.info(u"Set %s to %s", key, value)

        event.addresponse(True)

    @match(r'^(?:get\s+config|config\s+get)\s+(\S+?)$')
    def get(self, event, key):
        config = ibid.config
        for part in key.split('.'):
            if part not in config:
                event.addresponse(u'No such option')
                return
            config = config[part]
        event.addresponse(unicode(config))
        
# vi: set et sta sw=4 ts=4:
