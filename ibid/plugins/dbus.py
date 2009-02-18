import sys
from traceback import print_exc

import ibid
from ibid.plugins import Processor

class Proxy(Processor):

    def __init__(self, name):
        Module.__init__(self, name)
        if 'dbus' not in sys.modules:
            raise Exception('dbus library not loaded')

        self.iface = None
        self.addressed = None
        self.notprocessed = None
        self.pattern = None

        self.init()

    def init(self):
        bus_name = ibid.config.modules[self.name]['bus_name']
        object_path = ibid.config.modules[self.name]['object_path']
        bus = sys.modules['dbus'].SessionBus()
        object = bus.get_object(bus_name, object_path)
        self.iface = sys.modules['dbus'].Interface(object, 'org.ibid.ModuleInterface')
        (self.addressed, self.notprocessed, regex) = self.iface.init(self.name)
        if regex:
            self.pattern = re.compile(regex, re.I)

    def process(self, event):
        if self.addressed and ('addressed' not in event or not event['addressed']):
            return

        if self.notprocessed and ('processed' in event and event['processed']):
            return

        if not self.pattern.search(event['msg']):
            return

        converted = event.copy()
        if 'responses' in converted:
            del converted['responses']
        for key, value in converted.items():
            converted[key] = str(value)
        print converted

        try:
            response = self.iface.process(converted)
        except sys.modules['dbus'].DBusException:
            print_exc()
            self.init()
            response = self.iface.process(converted)

        if response:
            event['responses'].append(response)
            event['processed'] = True
            return event

# vi: set et sta sw=4 ts=4:
