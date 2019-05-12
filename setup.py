#!/usr/bin/env python
from setuptools import find_packages, setup

README = open('README.rst', 'r').read()


setup(
    name='mypy-language-server',
    version='0.1',
    description='Type checking and rich language features for Python using mypy.',
    long_description=README,
    url='https://github.com/matangover/mypy-language-server',
    author='Matan Gover',
    packages=find_packages(),

    install_requires=[
        'python-jsonrpc-server>=0.1.0',
    ],
    entry_points={
        'console_scripts': [
            'pyls = pyls.__main__:main',
        ]
    },
)
