# Copyright 2017 Palantir Technologies, Inc.
import functools
import inspect
import logging
import os
import threading

log = logging.getLogger(__name__)

def find_parents(root, path, names):
    """Find files matching the given names relative to the given path.

    Args:
        path (str): The file path to start searching up from.
        names (List[str]): The file/directory names to look for.
        root (str): The directory at which to stop recursing upwards.

    Note:
        The path MUST be within the root.
    """
    if not root:
        return []

    if not os.path.commonprefix((root, path)):
        log.warning("Path %s not in %s", path, root)
        return []

    # Split the relative by directory, generate all the parent directories, then check each of them.
    # This avoids running a loop that has different base-cases for unix/windows
    # e.g. /a/b and /a/b/c/d/e.py -> ['/a/b', 'c', 'd']
    dirs = [root] + os.path.relpath(os.path.dirname(path), root).split(os.path.sep)

    # Search each of /a/b/c, /a/b, /a
    while dirs:
        search_dir = os.path.join(*dirs)
        existing = list(filter(os.path.exists, [os.path.join(search_dir, n) for n in names]))
        if existing:
            return existing
        dirs.pop()

    # Otherwise nothing
    return []


def is_process_alive(pid):
    """ Check whether the process with the given pid is still alive.

    Args:
        pid (int): process ID

    Returns:
        bool: False if the process is not alive or don't have permission to check, True otherwise.
    """
    try:
        os.kill(pid, 0)
    except OSError:
        # no such process or process is already dead
        return False
    else:
        return True
