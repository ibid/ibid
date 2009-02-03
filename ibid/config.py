import logging

from configobj import ConfigObj
from validate import Validator
from pkg_resources import resource_stream

import ibid

def monkeypatch(self, name):
    if self.has_key(name):
        return self[name]
    super(ConfigObj, self).__getattr__(name)

ConfigObj.__getattr__ = monkeypatch

def FileConfig(filename):
    spec = resource_stream(__name__, 'configspec.ini')
    configspec = ConfigObj(spec, list_values=False, encoding='utf-8')
    config = ConfigObj(filename, configspec=configspec, interpolation='Template', encoding='utf-8')
    config.validate(Validator())
    logging.getLogger('core.config').info(u"Loaded configuration from %s", filename)
    return config

class Option(object):
    accessor = 'get'

    def __init__(self, name, description, default=None):
        self.name = name
        self.default = default
        self.description = description

    def __get__(self, instance, owner):
        if instance.name in ibid.config.plugins and self.name in ibid.config.plugins[instance.name]:
            section = ibid.config.plugins[instance.name]
            return getattr(section, self.accessor)(self.name)
        else:
            return self.default

class BoolOption(Option):
    accessor = 'as_bool'

class IntOption(Option):
    accessor = 'as_int'

class FloatOption(Option):
    accessor = 'as_float'

# vi: set et sta sw=4 ts=4:
