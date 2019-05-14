# Copyright 2017 Palantir Technologies, Inc.
import logging
import socketserver
import threading
import sys
from typing import Optional, Any

from pyls_jsonrpc.dispatchers import MethodDispatcher
from pyls_jsonrpc.endpoint import Endpoint
from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import lsp, _utils, uris
from . import config
from .workspace import Workspace

log = logging.getLogger(__name__)


PARENT_PROCESS_WATCH_INTERVAL = 10  # 10 s
MAX_WORKERS = 64
PYTHON_FILE_EXTENSIONS = ('.py', '.pyi')
CONFIG_FILEs = ('pycodestyle.cfg', 'setup.cfg', 'tox.ini', '.flake8')


class _StreamHandlerWrapper(socketserver.StreamRequestHandler, object):
    """A wrapper class that is used to construct a custom handler class."""

    delegate = None # type: Optional[Any]

    def setup(self):
        super(_StreamHandlerWrapper, self).setup()
        # pylint: disable=no-member
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)

    def handle(self):
        self.delegate.start()


def start_tcp_lang_server(bind_addr, port, handler_class):
    if not issubclass(handler_class, PythonLanguageServer):
        raise ValueError('Handler class must be an instance of PythonLanguageServer')

    # Construct a custom wrapper class around the user's handler_class
    wrapper_class = type(
        handler_class.__name__ + 'Handler',
        (_StreamHandlerWrapper,),
        {'DELEGATE_CLASS': handler_class}
    )

    server = socketserver.TCPServer((bind_addr, port), wrapper_class)
    server.allow_reuse_address = True

    try:
        log.info('Serving %s on (%s, %s)', handler_class.__name__, bind_addr, port)
        server.serve_forever()
    finally:
        log.info('Shutting down')
        server.server_close()


def start_io_lang_server(rfile, wfile, check_parent_process, handler_class):
    if not issubclass(handler_class, PythonLanguageServer):
        raise ValueError('Handler class must be an instance of PythonLanguageServer')
    log.info('Starting %s IO language server', handler_class.__name__)
    log.info(f'sys.executable = {sys.executable}')
    log.info(f'sys.version = {sys.version}')
    log.info(f'__file__ = {__file__}')
    
    # import ptvsd
    # log.info("Waiting for debugger attach on port 5678...")
    # ptvsd.enable_attach(address=('localhost', 5678), redirect_output=True)
    # ptvsd.wait_for_attach()
    # log.info("Debugger attached, starting...")

    server = handler_class(rfile, wfile, check_parent_process)
    server.start()


class PythonLanguageServer(MethodDispatcher):
    """ Implementation of the Microsoft VSCode Language Server Protocol
    https://github.com/Microsoft/language-server-protocol/blob/master/versions/protocol-1-x.md
    """

    # pylint: disable=too-many-public-methods,redefined-builtin

    def __init__(self, rx, tx, check_parent_process=False):
        self.workspace = None
        self.config = None

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._check_parent_process = check_parent_process
        self._endpoint = Endpoint(self, self._jsonrpc_stream_writer.write, max_workers=MAX_WORKERS)
        self._shutdown = False

    def start(self):
        """Entry point for the server."""
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def __getitem__(self, item):
        """Override getitem to fallback through multiple dispatchers."""
        if self._shutdown and item != 'exit':
            # exit is the only allowed method during shutdown
            log.debug("Ignoring non-exit method during shutdown: %s", item)
            raise KeyError

        return super(PythonLanguageServer, self).__getitem__(item)

    def m_shutdown(self, **_kwargs):
        self._shutdown = True
        return None

    def m_exit(self, **_kwargs):
        self._endpoint.shutdown()
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()

    def capabilities(self):
        from . import mypy_server
        is_patched_mypy = mypy_server.is_patched_mypy()
        if not is_patched_mypy:
            log.info('Using non-patched mypy, rich language features not available.')
        python_38 = sys.version_info >= (3, 8)
        if not python_38:
            log.info('Using Python before 3.8, rich language features not available.')
        rich_analysis_available = is_patched_mypy and python_38

        server_capabilities = {
            'definitionProvider': rich_analysis_available,
            'hoverProvider': rich_analysis_available,
            'textDocumentSync': lsp.TextDocumentSyncKind.INCREMENTAL
        }
        log.info('Server capabilities: %s', server_capabilities)
        return server_capabilities

    def m_initialize(self, processId=None, rootUri=None, rootPath=None, initializationOptions=None, **_kwargs):
        log.debug('Language server initialized with %s %s %s %s', processId, rootUri, rootPath, initializationOptions)
        if rootUri is None:
            rootUri = uris.from_fs_path(rootPath) if rootPath is not None else ''

        self.workspace = Workspace(rootUri, self._endpoint)
        self.config = config.Config(rootUri, initializationOptions or {},
                                    processId, _kwargs.get('capabilities', {}))

        try:
            import mypy
        except ImportError:
            self.workspace.show_message('Mypy is not installed. Follow mypy-vscode installation instructions.', lsp.MessageType.Warning)
            log.error(f'mypy is not installed. sys.path:\n{sys.path}')
            return {'capabilities': None}

        if self._check_parent_process and processId is not None:
            def watch_parent_process(pid):
                # exist when the given pid is not alive
                if not _utils.is_process_alive(pid):
                    log.info("parent process %s is not alive", pid)
                    self.m_exit()
                log.debug("parent process %s is still alive", pid)
                threading.Timer(PARENT_PROCESS_WATCH_INTERVAL, watch_parent_process, args=[pid]).start()

            watching_thread = threading.Thread(target=watch_parent_process, args=(processId,))
            watching_thread.daemon = True
            watching_thread.start()

        # Get our capabilities
        return {'capabilities': self.capabilities()}

    def m_initialized(self, **_kwargs):
        pass

    def get_document(self, doc_uri):
        return self.workspace.get_document(doc_uri) if doc_uri else None

    def m_text_document__did_close(self, textDocument=None, **_kwargs):
        self.workspace.rm_document(textDocument['uri'])

    def m_text_document__did_open(self, textDocument=None, **_kwargs):
        self.workspace.put_document(textDocument['uri'], textDocument['text'], version=textDocument.get('version'))

    def m_text_document__did_change(self, contentChanges=None, textDocument=None, **_kwargs):
        for change in contentChanges:
            self.workspace.update_document(
                textDocument['uri'],
                change,
                version=textDocument.get('version')
            )

    def m_text_document__did_save(self, textDocument=None, **_kwargs):
        from . import mypy_server
        mypy_server.mypy_check(self.workspace, self.config)

    def m_text_document__definition(self, textDocument=None, position=None, **_kwargs):
        from . import mypy_definition
        return mypy_definition.get_definitions(
            self.config,
            self.workspace,
            self.get_document(textDocument['uri']),
            position)

    def m_text_document__hover(self, textDocument=None, position=None, **_kwargs):
        from . import mypy_hover
        return mypy_hover.hover(self.workspace, self.get_document(textDocument['uri']), position)

    def m_workspace__did_change_configuration(self, settings=None):
        from . import mypy_server
        self.config.update((settings or {}).get('mypy', {}))
        mypy_server.configuration_changed(self.config, self.workspace)

    # def TODO_m_workspace__did_change_watched_files(self, changes=None, **_kwargs):
    #     changed_py_files = set()
    #     config_changed = False
    #     for d in (changes or []):
    #         if d['uri'].endswith(PYTHON_FILE_EXTENSIONS):
    #             changed_py_files.add(d['uri'])
    #         elif d['uri'].endswith(CONFIG_FILEs):
    #             config_changed = True
    #
    #     if config_changed:
    #         self.config.settings.cache_clear()
    #     elif not changed_py_files:
    #         # Only externally changed python files and lint configs may result in changed diagnostics.
    #         return
    #
    #     for doc_uri in self.workspace.documents:
    #         # Changes in doc_uri are already handled by m_text_document__did_save
    #         if doc_uri not in changed_py_files:
    #             # self.lint(doc_uri, is_saved=False)
    #             pass
