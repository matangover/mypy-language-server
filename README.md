# Mypy Language Server

Runs mypy on Python code to provide type checking, go to definition, and hover.

## Installation

### Installation in VS Code
To use this language server in VS Code, use the [Mypy extension for VS Code](https://github.com/matangover/mypy-vscode/blob/master/README.md).

### Usage with other language server hosts

#### Basic installation (type checking only)

Requires Python 3.5 or later.
```shell
$ pip install mypyls
```

#### Installation with hover and go to definition

These features require Python 3.8 (currently in pre-release) and a patched version of mypy.

1. Install [Python 3.8 pre-release](https://www.python.org/download/pre-releases/) (you may choose to use [pyenv](https://github.com/pyenv/pyenv).
2. Create a Python 3.8 virtualenv and install mypyls in it:
    ```shell
    $ python3.8 -m venv ~/.mypyls
    $ ~/.mypyls/bin/pip install mypyls
    ```
3. Install the patched version of mypy in the virtualenv:
    ```shell
    $ ~/.mypyls/bin/pip install git+https://github.com/matangover/mypy
    ```

## License

This project is made available under the MIT License.
It is based on Palantir's [python-language-server](https://github.com/palantir/python-language-server) and uses [mypy](https://github.com/python/mypy>).