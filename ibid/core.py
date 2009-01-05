from traceback import print_exc
import inspect
import re

from twisted.internet import reactor, threads
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import ibid
import ibid.plugins
import ibid.auth_

class Dispatcher(object):

    def _process(self, event):
        for processor in ibid.processors:
            try:
                event = processor.process(event) or event
            except Exception:
                print_exc()

        print event

        filtered = []
        for response in event['responses']:
            source = response['source'].lower()
            if source == event.source.lower():
                filtered.append(response)
            else:
                if source in ibid.sources:
                    reactor.callFromThread(ibid.sources[source].send, response)
                else:
                    print u'Invalid source %s' % response['source']

        event.responses = filtered
        return event

    def dispatch(self, event):
        return threads.deferToThread(self._process, event)

class Reloader(object):

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
            return True
        except Exception:
            print_exc()
            return False
        
    def load_source(self, name, service=None):
        type = ibid.config.sources[name]['type']

        module = 'ibid.source.%s' % type
        factory = 'ibid.source.%s.SourceFactory' % type
        try:
            __import__(module)
            moduleclass = eval(factory)
        except:
            print_exc()
            return

        ibid.sources[name.lower()] = moduleclass(name)
        ibid.sources[name.lower()].setServiceParent(service)
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
        except Exception:
            print_exc()
            return False

        try:
            if module == classname:
                for classname, klass in inspect.getmembers(m, inspect.isclass):
                    if issubclass(klass, ibid.plugins.Processor) and klass != ibid.plugins.Processor:
                        ibid.processors.append(klass(name))
            else:
                moduleclass = eval(classname)
                ibid.processors.append(moduleclass(name))
                
        except Exception:
            print_exc()
            return False

        ibid.processors.sort(key=lambda x: x.priority)

        return True

    def unload_processor(self, name):
        found = False
        for processor in ibid.processors:
            if processor.name == name:
                ibid.processors.remove(processor)
                found = True

        return found

    def reload_databases(self):
        reload(ibid.core)
        ibid.databases = DatabaseManager()
        return True

    def reload_auth(self):
        reload(ibid.auth_)
        ibid.auth = ibid.auth_.Auth()
        return True

    def reload_config(self):
        for processor in ibid.processors:
            processor.load_config()

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
        for database in ibid.config.databases.keys():
            self.load(database)

    def load(self, name):
        uri = ibid.config.databases[name]['uri']
        if uri.startswith('sqlite:///'):
            engine = create_engine('sqlite:///', creator=sqlite_creator(uri.replace('sqlite:///', '', 1)), echo=True)
        else:
            engine = create_engine(uri)
        self[name] = scoped_session(sessionmaker(bind=engine))

    def __getattr__(self, name):
        return self[name]

# vi: set et sta sw=4 ts=4:
