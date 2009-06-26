import csv
import datetime
import time
import gc
import gzip
import logging
import os
import os.path

from ibid.plugins import Processor, handler
from ibid.config import Option

class MemoryLog(Processor):
    filename = Option('filename', 'Memory log filename', 'logs/memory.log')

    def setup(self):
        if os.path.isfile(self.filename + '.10.gz'):
            os.remove(self.filename + '.10.gz')
        for i in range(9, 0, -1):
            if os.path.isfile('%s.%i.gz' % (self.filename, i)):
                os.rename('%s.%i.gz' % (self.filename, i),
                        '%s.%i.gz' % (self.filename, i+1))
        if os.path.isfile(self.filename):
            o = gzip.open(self.filename + '.1.gz', 'wb')
            i = open(self.filename, 'rb')
            o.write(i.read())
            o.close()
            i.close()
            stat = os.stat(self.filename)
            os.utime(self.filename + '.1.gz', (stat.st_atime, stat.st_mtime))

        self._file = file('logs/memory.log', 'w+')
        self._csv = csv.writer(self._file)
        self._startup = time.clock()

    def process(self, event):
        status = file('/proc/%i/status' % os.getpid(), 'r').readlines()
        status = dict(x.strip().split(':', 1) for x in status)

        gc.collect()

        self._csv.writerow((
            datetime.datetime.utcnow().isoformat(),
            time.clock() - self._startup,
            len(gc.get_objects()),
            status['VmSize'].strip().split()[0],
            status['VmRSS'].strip().split()[0],
            status['VmData'].strip().split()[0],
        ))
        self._file.flush()

# vi: set et sta sw=4 ts=4:
