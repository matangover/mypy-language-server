# Copyright 2017 Palantir Technologies, Inc.
import logging
import os
import re
from collections import defaultdict
import pyls.uris

from mypy.dmypy_server import Server
from mypy.dmypy_util import DEFAULT_STATUS_FILE
from mypy.options import Options
from typing import Set

from pyls import hookimpl, lsp
from threading import Thread

line_pattern = r"([^:]+):(?:(\d+):)?(?:(\d+):)? (\w+): (.*)"

log = logging.getLogger(__name__)

@hookimpl
def pyls_initialize(config, workspace):
    options = Options()
    options.show_column_numbers = True
    options.follow_imports = 'error'
    options.check_untyped_defs = True
    workspace.mypy_server = Server(options, DEFAULT_STATUS_FILE)

    thread = Thread(target=mypy_check, args=(workspace, ))
    thread.start()

def mypy_check(workspace):
    log.info('Checking mypy...')
    try:
        result = workspace.mypy_server.cmd_check([workspace.root_path])
        log.info(f'mypy done, exit code {result["status"]}')
        if result['err']:
            log.info(f'mypy stderr:\n{result["err"]}')
        if result['out']:
            log.info(f'mypy stdout:\n{result["out"]}')
            publish_diagnostics(workspace, result['out'])
    except Exception:
        log.exception('Error in mypy check:')
    except SystemExit:
        log.exception('Oopsy, mypy tried to exit.')


def parse_line(line):
    result = re.match(line_pattern, line)
    if result is None:
        log.info(f'Skipped unrecognized mypy line: {line}')
        return None, None

    path, lineno, offset, severity, msg = result.groups()
    lineno = int(lineno or 1)
    offset = int(offset or 0)

    errno = lsp.DiagnosticSeverity.Error if severity == 'error' else lsp.DiagnosticSeverity.Information
    diag = {
        'source': 'mypy',
        'range': {
            'start': {'line': lineno - 1, 'character': offset},
            # There may be a better solution, but mypy does not provide end
            'end': {'line': lineno - 1, 'character': offset}
        },
        'message': msg,
        'severity': errno
    }

    return path, diag


def parse_mypy_output(mypy_output):
    diagnostics = defaultdict(list)
    for line in mypy_output.splitlines():
        path, diag = parse_line(line)
        if diag:
            diagnostics[path].append(diag)

    return diagnostics


documents_with_diagnostics: Set[str] = set()

def publish_diagnostics(workspace, mypy_output):
    diagnostics_by_path = parse_mypy_output(mypy_output)
    previous_documents_with_diagnostics = documents_with_diagnostics.copy()
    documents_with_diagnostics.clear()
    for path, diagnostics in diagnostics_by_path.items():
        uri = pyls.uris.from_fs_path(os.path.join(workspace.root_path, path))
        documents_with_diagnostics.add(uri)
        # TODO: If mypy is really fast, it may finish before initialization is complete,
        #       and this call will have no effect. (?)
        workspace.publish_diagnostics(uri, diagnostics)

    documents_to_clear = previous_documents_with_diagnostics - documents_with_diagnostics
    for uri in documents_to_clear:
        workspace.publish_diagnostics(uri, [])
