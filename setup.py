#!/usr/bin/env python
import sys
import os.path
from setuptools import find_packages, setup
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md')) as f:
    long_description = f.read()

sys.path.insert(0, this_directory)
from mypyls.version import __version__

setup(
    name='mypyls',
    version=__version__,
    description='Type checking and rich language features for Python using mypy.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/matangover/mypyls',
    author='Matan Gover',
    packages=find_packages(),

    install_requires=[
        'python-jsonrpc-server>=0.1.0'
    ],
    extras_require={
        'default-mypy': [
            'mypy==0.800'
        ],
        'patched-mypy': [
            # Cannot use zip archive because we must include the typeshed submodule.
            'mypy @ git+https://github.com/matangover/mypy'
        ]
    },
    python_requires='>=3.5',
    entry_points={
        'console_scripts': [
            'mypyls = mypyls.__main__:main',
        ]
    },
)
