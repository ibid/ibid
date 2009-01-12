from setuptools import find_packages, setup

setup(
    name='TracIbidPlugin',
    version='0.1',
    packages=find_packages(),
    entry_points = {
        'trac.plugins': ['ibidtrac = ibidtrac.notifier']
    },
)

# vi: set et sta sw=4 ts=4:
