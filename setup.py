from subprocess import Popen, PIPE

from setuptools import setup, find_packages

def bzr_revision():
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

    bzr = Popen(('bzr', 'log', '--line', '-c', '-1'), stdout=PIPE)
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
    license='TBD',
    py_modules=['ibid'],
    setup_requires=['setuptools_bzr'],
    install_requires=[
        'SQLAlchemy>=0.4.6',
        'wokkel>=0.4',
        #'ConfigObj>=4.5.3',
        'jinja',
        #'validate>=0.3.2',
    ],
    packages=find_packages(exclude=['lib']),
    entry_points={
        'trac.plugins': ['tracibid = tracibid.notifier'],
    },
    scripts=['scripts/ibid', 'scripts/ibid-setup', 'scripts/ibid-factpack', 'scripts/ibid_pb', 'scripts/ibid_import'],
    include_package_data=True,
    exclude_package_data={
        'lib': ['*'],
    }
)

# vi: set et sta sw=4 ts=4:
