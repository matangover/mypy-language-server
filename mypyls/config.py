# Copyright 2017 Palantir Technologies, Inc.
import logging
from . import _utils, uris

log = logging.getLogger(__name__)

class Config(object):
    def __init__(self, root_uri, init_opts, process_id, capabilities):
        self._root_path = uris.to_fs_path(root_uri)
        self._root_uri = root_uri
        self._init_opts = init_opts
        self._process_id = process_id
        self._capabilities = capabilities
        self._settings = {} # type: dict

    @property
    def init_opts(self):
        return self._init_opts

    @property
    def root_uri(self):
        return self._root_uri

    @property
    def process_id(self):
        return self._process_id

    @property
    def capabilities(self):
        return self._capabilities

    def settings(self, document_path=None):
        return self._settings

    def find_parents(self, path, names):
        root_path = uris.to_fs_path(self._root_uri)
        return _utils.find_parents(root_path, path, names)

    def update(self, settings):
        """Recursively merge the given settings into the current settings."""
        self._settings = settings
        log.info("Updated settings to %s", self._settings)
