#!/usr/bin/env python
from setuptools import find_packages, setup
import versioneer

README = open('README.rst', 'r').read()


setup(
    name='mypy-language-server',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),

    description='Type checking and rich language features for Python using mypy.',

    long_description=README,

    # The project's main homepage.
    url='https://github.com/matangover/mypy-language-server',

    author='Matan Gover',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'test', 'test.*']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'configparser; python_version<"3.0"',
        'future>=0.14.0',
        'futures; python_version<"3.2"',
        'backports.functools_lru_cache; python_version<"3.2"',
        'python-jsonrpc-server>=0.1.0',
    ],
    entry_points={
        'console_scripts': [
            'pyls = pyls.__main__:main',
        ]
    },
)
