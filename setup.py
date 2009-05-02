#!/usr/bin/env python

from os.path import exists
from subprocess import Popen, PIPE

from setuptools import setup

def bzr_revision():
    if not exists('.bzr'):
        return

    bzr = Popen(('bzr', 'tags', '--sort', 'time'), stdout=PIPE)
    output, error = bzr.communicate()
    code = bzr.wait()

    if code != 0:
        raise Exception(u'Error running bzr tags')

    lines = output.splitlines()
    if len(lines) == 0:
        tag = '0.0.0'
        revision = '0'
    else:
        tag, revision = lines[-1].split()

    bzr = Popen(('bzr', 'log', '--line', '-r', '-1'), stdout=PIPE)
    output, error = bzr.communicate()
    code = bzr.wait()

    if code != 0:
        raise Exception(u"Error running bzr log")

    latest = output.split(':')[0]

    versionstring = latest == revision and tag or '%s-bzr%s' % (tag, latest)

    f = open('ibid/.version', 'w')
    f.write(versionstring)
    f.close()

    return versionstring

setup(
    name='Ibid',
    version=bzr_revision(),
    description='A modular, extensible IRC/IM bot',
    url='http://ibid.omnia.za.net/',
    keywords='bot irc jabber',
    author='Ibid Developers',
    author_email='ibid@omnia.za.net',
    license='MIT',
    py_modules=['ibid'],
    install_requires=[
        'SQLAlchemy>=0.4.6',
        'wokkel==0.4',
        'jinja',
        'html2text',
        #'pinder',
        #'pysilc',
        #'SOAPpy',
        'simplejson',
        #'MySQLdb', #?
        #'pysqlite2', #?
        #'ConfigObj>=4.5.3',
        #'validate>=0.3.2',
    ],
    dependency_links=['http://wokkel.ik.nu/downloads'],
    packages=['ibid', 'tracibid', 'lib', 'twisted', 'contrib', 'factpacks'],
    entry_points={
        'trac.plugins': ['tracibid = tracibid.notifier'],
    },
    scripts=['scripts/ibid', 'scripts/ibid-setup', 'scripts/ibid-factpack', 'scripts/ibid_pb', 'scripts/ibid_import', 'scripts/ibid.tac', 'scripts/ibid-plugin'],
    include_package_data=True,
    zip_safe=False,
)

# vi: set et sta sw=4 ts=4:
