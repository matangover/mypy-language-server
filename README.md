# Mypy Language Server

Runs mypy on Python code to provide type checking.

## Installation

Follow the installation instructions in [Mypy extension for VS Code](https://github.com/matangover/mypy-vscode/blob/master/README.md). Using the VS Code extension itself is not required -- the language server may be used with any editor that supports the Language Server Protocol.

## Experimental IDE features

Originally this language server was also an attempt to implement IDE features on top of mypy's analysis engine. A basic go-to-definition and hover implementation still exists. However, it is tied to internal mypy APIs and uses a forked version of mypy which is hard to maintain. I have abandoned this work because other language servers do a better job at implementing these IDE features for now. Mypy remains focused on its core task of type checking, as does this language server.

## License

This project is made available under the MIT License.
It is based on Palantir's [python-language-server](https://github.com/palantir/python-language-server) and uses [mypy](https://github.com/python/mypy).
