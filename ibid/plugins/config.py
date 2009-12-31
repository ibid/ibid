from os.path import join
import logging

import ibid
from ibid.config import FileConfig
from ibid.utils import human_join
from ibid.plugins import Processor, match, authorise, auth_responses

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
    @authorise()
    def reload(self, event):
        ibid.config.reload()
        ibid.config.merge(FileConfig(join(ibid.options['base'], 'local.ini')))
        ibid.reloader.reload_config()
        ibid.auth.drop_caches()
        event.addresponse(True)
        log.info(u'Reread configuration file')

    @match(r'^(?:set\s+config|config\s+set)\s+(\S+?)(?:\s+to\s+|\s*=\s*)(\S.*?)$')
    @authorise()
    def set(self, event, key, value):
        config = ibid.config
        for part in key.split('.')[:-1]:
            if isinstance(config, dict):
                if part not in config:
                    config[part] = {}
            else:
                event.addresponse(u'No such option')
                return

            config = config[part]

        part = key.split('.')[-1]
        if not isinstance(config, dict):
            event.addresponse(u'No such option')
            return
        if ',' in value:
            config[part] = [part.strip() for part in value.split(',')]
        else:
            config[part] = value

        ibid.config.write()
        ibid.reloader.reload_config()
        log.info(u"Set %s to %s", key, value)

        event.addresponse(True)

    @match(r'^(?:get\s+config|config\s+get)\s+(\S+?)$')
    def get(self, event, key):
        if 'password' in key.lower() and not auth_responses(event, u'config'):
            return

        config = ibid.config
        for part in key.split('.'):
            if not isinstance(config, dict) or part not in config:
                event.addresponse(u'No such option')
                return
            config = config[part]
        if isinstance(config, list):
            event.addresponse(u', '.join(config))
        elif isinstance(config, dict):
            event.addresponse(u'Keys: ' + human_join(config.keys()))
        else:
            event.addresponse(unicode(config))

# vi: set et sta sw=4 ts=4:
