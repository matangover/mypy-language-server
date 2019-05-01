# Copyright 2017 Palantir Technologies, Inc.
import contextlib
import logging
import os
import re
import sys

from mypy.dmypy_server import Server
from mypy.dmypy_util import DEFAULT_STATUS_FILE
from mypy.options import Options

from pyls import hookimpl, lsp

log = logging.getLogger(__name__)

@hookimpl
def pyls_initialize(config, workspace):
    workspace.dmypy = Server(Options(), DEFAULT_STATUS_FILE)
    log.info('Checking mypy...')
    try:
        result = workspace.dmypy.cmd_check([workspace.root_path])
        log.info(f'mypy done, exit code {result["status"]}')
        if result['err']:
            log.info(f'mypy stderr:\n{result["err"]}')
        if result['out']:
            log.info(f'mypy stdout:\n{result["out"]}')
    except Exception:
        log.exception('Error in mypy check:')
    except SystemExit:
        log.exception('Oopsy, mypy tried to exit.')
