import csv
from datetime import datetime, timedelta
import gc
import gzip
import os
import os.path

import simplejson
import objgraph

import ibid
from ibid.plugins import Processor, match
from ibid.config import Option, IntOption

help = {}

help['memory'] = u'Debugging module that keeps track of memory usage'

def get_memusage():
    status = file('/proc/%i/status' % os.getpid(), 'r').readlines()
    status = [x.strip().split(':', 1) for x in status if x.startswith('Vm')]
    return dict((x, int(y.split()[0])) for (x, y) in status)

class MemoryLog(Processor):
    
    feature = 'memory'

    mem_filename = Option('mem_filename', 'Memory log filename', 'logs/memory.log')
    mem_interval = IntOption('mem_interval', 'Interval between memory stat logging', 0)
    obj_filename = Option('obj_filename', 'Object Statistics log filename', 'logs/objstats.log')
    obj_interval = IntOption('obj_interval', 'Interval between logging object statistics', 0)

    def setup(self):
        fns = []
        if self.mem_interval:
            fns.append(self.mem_filename)
        if self.obj_interval:
            fns.append(self.obj_filename)
        for filename in fns:
            if os.path.isfile(filename + '.10.gz'):
                os.remove(filename + '.10.gz')
            for i in range(9, 0, -1):
                if os.path.isfile('%s.%i.gz' % (filename, i)):
                    os.rename('%s.%i.gz' % (filename, i),
                            '%s.%i.gz' % (filename, i+1))
            if os.path.isfile(filename):
                o = gzip.open(filename + '.1.gz', 'wb')
                i = open(filename, 'rb')
                o.write(i.read())
                o.close()
                i.close()
                stat = os.stat(filename)
                os.utime(filename + '.1.gz', (stat.st_atime, stat.st_mtime))

        if self.mem_interval:
            self.mem_file = file(self.mem_filename, 'w+')
            self.mem_file.write('Ibid Memory Log v2: %s\n' % ibid.config['botname'])
            self.mem_csv = csv.writer(self.mem_file)
            self.mem_last = datetime.utcnow()

        if self.obj_interval:
            self.obj_file = file(self.obj_filename, 'w+')
            self.obj_file.write('Ibid Object Log v1: %s\n' % ibid.config['botname'])
            self.obj_last = datetime.utcnow()

    def process(self, event):
        now = datetime.utcnow()
        if self.mem_interval and now - self.mem_last >= timedelta(seconds=self.mem_interval):
            self.mem_log()
            self.mem_last = now
        if self.obj_interval and now - self.obj_last >= timedelta(seconds=self.obj_interval):
            self.obj_log()
            self.obj_last = now

    def mem_log(self):
        status = get_memusage()
        gc.collect()

        self.mem_csv.writerow((
            datetime.utcnow().isoformat(),
            len(gc.get_objects()),
            status['VmSize'],
            status['VmRSS'],
        ))
        self.mem_file.flush()

    def obj_log(self):
        stats = objgraph.typestats()
        self.obj_file.write('%s %s\n' % (
            datetime.utcnow().isoformat(),
            simplejson.dumps(objgraph.typestats())
        ))
        self.obj_file.flush()

class MemoryInfo(Processor):
    u"memory usage"

    feature = 'memory'

    @match('^memory\s+usage$')
    def memory_usage(self, event):
        event.addresponse(u"Today, I weigh in at %(VmSize)i kiB Virtual, %(VmRSS)s kiB RSS", get_memusage())

# vi: set et sta sw=4 ts=4:
