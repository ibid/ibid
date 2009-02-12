import inspect
import re
import logging
from os.path import join, expanduser

from twisted.internet import reactor, threads
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import ibid
import auth

class Dispatcher(object):

    def __init__(self):
        self.log = logging.getLogger('core.dispatcher')

    def _process(self, event):
        for processor in ibid.processors:
            try:
                event = processor.process(event) or event
            except Exception:
                self.log.exception(u"Exception occured in %s processor of %s plugin", processor.__class__.__name__, processor.name)

        print event

        filtered = []
        for response in event['responses']:
            source = response['source'].lower()
            if source == event.source.lower():
                filtered.append(response)
            else:
                self.send(response)

        event.responses = filtered
        self.log.debug(u"Returning event to %s source", event.source)
        return event

    def send(self, response):
        source = response['source'].lower()
        if source in ibid.sources:
            reactor.callFromThread(ibid.sources[source].send, response)
            self.log.debug(u"Sent response to non-origin source %s: %s", source, response['reply'])
        else:
            self.log.warning(u'Received response for invalid source %s: %s', response['source'], response['reply'])
        
    def dispatch(self, event):
        self.log.debug(u"Received event from %s source", event.source)
        return threads.deferToThread(self._process, event)

class Reloader(object):

    def __init__(self):
        self.log = logging.getLogger('core.reloader')

    def run(self):
        self.reload_dispatcher()
        self.load_sources()
        self.load_processors()
        reactor.run()

    def reload_dispatcher(self):
        try:
            reload(ibid.core)
            dispatcher = ibid.core.Dispatcher()
            ibid.dispatcher = dispatcher
            self.log.info(u"Reloaded reloader")
            return True
        except Exception, e:
            self.log.error(u"Failed to reload reloader: %s", e.message)
            return False
        
    def load_source(self, name, service=None):
        type = 'type' in ibid.config.sources[name] and ibid.config.sources[name]['type'] or name

        module = 'ibid.source.%s' % type
        factory = 'ibid.source.%s.SourceFactory' % type
        try:
            __import__(module)
            moduleclass = eval(factory)
        except:
            self.log.exception(u"Couldn't import %s and instantiate %s", module, factory)
            return

        ibid.sources[name.lower()] = moduleclass(name)
        ibid.sources[name.lower()].setServiceParent(service)
        self.log.info(u"Loaded %s source %s", type, name)
        return True

    def load_sources(self, service=None):
        for source in ibid.config.sources.keys():
            if 'disabled' not in ibid.config.sources[source]:
                self.load_source(source, service)

    def unload_source(self, name):
        name = name.lower()
        if name not in ibid.sources:
            return False

        ibid.sources[name].protocol.loseConnection()
        del ibid.sources[name]
        self.log.info(u"Unloaded %s source", name)

    def reload_source(self, name):
        if name not in ibid.config['sources']:
            return False

        self.unload_source(name)

        source = ibid.config['sources'][name]
        m=eval('ibid.source.%s' % source['type'])
        reload(m)

        self.load_source(source)

    def load_processors(self):
        for processor in ibid.config['load']:
            if not self.load_processor(processor):
                print "Couldn't load processor %s" % processor

    def load_processor(self, name):
        object = name
        if name in ibid.config.plugins and 'type' in ibid.config.plugins[name]:
            object = ibid.config['plugins'][name]['type']

        module = 'ibid.plugins.' + object.split('.')[0]
        classname = 'ibid.plugins.' + object
        try:
            __import__(module)
            m = eval(module)
            reload(m)
        except Exception, e:
            if isinstance(e, ImportError):
                error = u"Couldn't load %s plugin because it requires module %s" % (name, e.args[0].replace('No module named ', ''))
                self.log.warning(error)
            else:
                self.log.exception(u"Couldn't load %s plugin", name)
            return False

        try:
            if module == classname:
                for classname, klass in inspect.getmembers(m, inspect.isclass):
                    if issubclass(klass, ibid.plugins.Processor) and klass != ibid.plugins.Processor:
                        ibid.processors.append(klass(name))
            else:
                moduleclass = eval(classname)
                ibid.processors.append(moduleclass(name))
                
        except Exception, e:
            self.log.exception(u"Couldn't instantiate %s processor of %s plugin", classname, name)
            return False

        ibid.processors.sort(key=lambda x: x.priority)

        self.log.debug(u"Loaded %s plugin", name)
        return True

    def unload_processor(self, name):
        for processor in ibid.processors:
            if processor.name == name:
                ibid.processors.remove(processor)
        else:
            return False

        self.log.info(u"Unloaded %s plugin", name)
        return True

    def reload_databases(self):
        reload(ibid.core)
        ibid.databases = DatabaseManager()
        return True

    def reload_auth(self):
        try:
            reload(auth)
            ibid.auth = auth.Auth()
            self.log.info(u'Reloaded auth')
            return True
        except Exception, e:
            self.log.error(u"Couldn't reload auth: %s", e.message)

        return False

    def reload_config(self):
        for processor in ibid.processors:
            processor.load_config()
        self.log.info(u"Notified all processors of config reload")

def regexp(pattern, item):
    return re.search(pattern, item) and True or False

def sqlite_creator(database):
    from pysqlite2 import dbapi2 as sqlite
    def connect():
        connection = sqlite.connect(database)
        connection.create_function('regexp', 2, regexp)
        return connection
    return connect

class DatabaseManager(dict):

    def __init__(self):
        self.log = logging.getLogger('core.databases')
        for database in ibid.config.databases.keys():
            self.load(database)

    def load(self, name):
        uri = ibid.config.databases[name]['uri']
        if uri.startswith('sqlite:///'):
            engine = create_engine('sqlite:///', creator=sqlite_creator(join(ibid.options['base'], expanduser(uri.replace('sqlite:///', '', 1)))), encoding='utf-8', convert_unicode=True, assert_unicode=True, echo=False)
        else:
            engine = create_engine(uri, encoding='utf-8', convert_unicode=True, assert_unicode=True)
        self[name] = scoped_session(sessionmaker(bind=engine, transactional=False, autoflush=True))
        self.log.info(u"Loaded %s database", name)

    def __getattr__(self, name):
        return self[name]

# vi: set et sta sw=4 ts=4:
