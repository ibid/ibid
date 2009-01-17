import logging

import ibid
from ibid.plugins import Processor, match, authorise

help = {'config': 'Gets and sets configuration settings, and rereads the configuration file.'}

log = logging.getLogger('plugins.config')

class Config(Processor):
    """reread config | set config <name> <value> | get config <name>"""
    feature = 'config'

    permission = u'config'

    @match(r'^reread\s+config$')
    @authorise
    def reload(self, event):
        try:
            ibid.config.reload()
            ibid.reloader.reload_config()
            event.addresponse(u"Configuration reread")
            log.info(u"Reread configuration file")
        except:
            event.addresponse(u"Error reloading configuration")

    @match(r'^set\s+config\s+(\S+?)(?:\s+to\s+|\s*=\s*)(\S.*?)$')
    @authorise
    def set(self, event, key, value):
        config = ibid.config
        for part in key.split('.')[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]

        config[key.split('.')[-1]] = value
        ibid.config.write()
        ibid.reloader.reload_config()
        log.info(u"Set %s to %s", key, value)

        event.addresponse(u'Done')

    @match(r'^get\s+config\s+(\S+?)$')
    def get(self, event, key):
        config = ibid.config
        for part in key.split('.'):
            if part not in config:
                event.addresponse(u'No such option')
                return event
            config = config[part]
        event.addresponse(str(config))
        
# vi: set et sta sw=4 ts=4:
