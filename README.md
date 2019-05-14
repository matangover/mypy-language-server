# Mypy Language Server

Runs mypy on Python code to provide type checking, go to definition, and hover.

## Installation

Follow the installation instructions in [Mypy extension for VS Code](https://github.com/matangover/mypy-vscode/blob/master/README.md). Using the VS Code extension itself is not required -- the language server may be used with any editor that supports the Language Server Protocol.

## Motivation

Why another language server for Python? There are already at least Palantir's python-language-server (uses jedi), pyright (uses analysis engine written in TypeScript), Microsoft's python-language-server (uses analysis engine written in C#), and PyCharm (does not provide language server conforming to Language Server Protocol; uses analysis engine written in Java).

Mypy has a robost type checking engine that is focused on correctness. Other IDE tools use custom analysis engines and the provided language features do not always match mypy's analysis. In a future where type-annotated Python is more common, it would be useful to have mypy's robust analysis provide the basis for IDE features as 'one source truth'. This language server is a proof of concept for that, although it is currently quite hacky and uses private mypy APIs. The mypy team [might be working](https://github.com/palantir/python-language-server/issues/194#issuecomment-484134414) on an official integration in the future.

## License

This project is made available under the MIT License.
It is based on Palantir's [python-language-server](https://github.com/palantir/python-language-server) and uses [mypy](https://github.com/python/mypy>).