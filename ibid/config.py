# Copyright (c) 2008-2009, Michael Gorven
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

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
        __import__('ibid.plugins')
        __import__('ibid.source')

    def __get__(self, instance, owner):
        if instance is None:
            return self.default

        if issubclass(owner, ibid.plugins.Processor):
            config = ibid.config.plugins
        elif issubclass(owner, ibid.source.IbidSourceFactory):
            config = ibid.config.sources
        else:
            raise AttributeError

        if instance.name in config and self.name in config[instance.name]:
            section = config[instance.name]
            return getattr(section, self.accessor)(self.name)
        else:
            return self.default

class BoolOption(Option):
    accessor = 'as_bool'

class IntOption(Option):
    accessor = 'as_int'

class FloatOption(Option):
    accessor = 'as_float'

class ListOption(Option):

    def __get__(self, instance, owner):
        value = Option.__get__(self, instance, owner)
        if not isinstance(value, (list, tuple)):
            value = [value]

        if value and not value[0] and self.default:
            both = []
            both.extend(self.default)
            both.extend(value[1:])
            value = both

        return value

class DictOption(Option):

    def __get__(self, instance, owner):
        value = Option.__get__(self, instance, owner)

        if self.default and value is not self.default:
            both = self.default.copy()
            both.update(value)
            value = both

            for k, v in value.items():
                if not v:
                    del value[k]

        return value

# vi: set et sta sw=4 ts=4:
