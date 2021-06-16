# Mypy Language Server

Runs mypy on Python code to provide type checking, and supports the Language Server Protocol to enable integrating mypy into various editors.

**NOTE:** This language server was used in the past in the [Mypy extension for VS Code](https://github.com/matangover/mypy-vscode). However, that extension now uses the mypy daemon directly instead.

## Experimental IDE features

Originally this language server was also an attempt to implement IDE features on top of mypy's analysis engine. A basic go-to-definition and hover implementation still exists. However, it is tied to internal mypy APIs and uses a forked version of mypy which is hard to maintain. I have abandoned this work because other language servers do a better job at implementing these IDE features.

## License

This project is made available under the MIT License.
It is based on Palantir's [python-language-server](https://github.com/palantir/python-language-server) and uses [mypy](https://github.com/python/mypy).
