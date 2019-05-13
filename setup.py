#!/usr/bin/env python
import os.path
from setuptools import find_packages, setup

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md')) as f:
    long_description = f.read()


setup(
    name='mypyls',
    version='0.1',
    description='Type checking and rich language features for Python using mypy.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/matangover/mypy-language-server',
    author='Matan Gover',
    packages=find_packages(),

    install_requires=[
        'python-jsonrpc-server>=0.1.0'
    ],
    extras_require={
        'default-mypy': [
            'mypy==0.701'
        ],
        'patched-mypy': [
            'mypy @ https://github.com/matangover/mypy/archive/master.zip'
        ]
    },
    python_requires='>=3.5',
    entry_points={
        'console_scripts': [
            'mypyls = mypyls.__main__:main',
        ]
    },
)
