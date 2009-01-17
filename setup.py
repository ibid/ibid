from setuptools import setup, find_packages
from subprocess import Popen, PIPE

def bzr_revision():
    bzr = Popen(('bzr', 'tags', '--sort', 'time'), stdout=PIPE)
    output, error = bzr.communicate()
    code = bzr.wait()

    if code != 0:
        raise Exception(u'Error running bzr tags')

    lines = output.splitlines()
    if len(lines) == 0:
        raise Exception(u"No Bazaar tags defined")

    (tag, revision) = lines[-1].split()

    bzr = Popen(('bzr', 'log', '--line', '-c', '-1'), stdout=PIPE)
    output, error = bzr.communicate()
    code = bzr.wait()

    if code != 0:
        raise Exception(u"Error running bzr log")

    latest = output.split(':')[0]

    if latest == revision:
        return tag
    else:
        return '%s-bzr%s' % (tag, latest)

setup(
    name='Ibid',
    version=bzr_revision(),
    description='A modular, extensible IRC/IM bot',
    url='http://ibid.omnia.za.net/',
    keywords='bot irc jabber',
    py_modules=['ibid'],
    setup_requires=['setuptools_bzr'],
    install_requires=[
        'SQLAlchemy>=0.4.6',
        'wokkel>=0.4',
        'ConfigObj>=4.5.3',
        'validate>=0.3.2',
    ],
    packages=find_packages(exclude=['lib']),
    scripts=['ibid.tac', 'ibid.py', 'populatedb.py'],
    include_package_data=True,
    package_data={
        '': ['*.ini'],
    },
    exclude_package_data={
        'lib': ['*'],
    }
)

# vi: set et sta sw=4 ts=4:
