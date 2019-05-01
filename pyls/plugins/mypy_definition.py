# Copyright 2017 Palantir Technologies, Inc.
import logging
from pyls import hookimpl, uris
from mypy.suggestions import SuggestionEngine, get_definition
from mypy.util import short_type

from mypy.nodes import (
    FuncDef, MypyFile, SymbolTable,
    SymbolNode, TypeInfo, Node, Expression, ReturnStmt, NameExpr, SymbolTableNode, Var,
    AssignmentStmt, Context, RefExpr, FuncBase, MemberExpr
)
from mypy.types import (
    Type, AnyType, TypeOfAny, CallableType, UnionType, NoneTyp, Instance, is_optional,
)
from typing import Optional, Tuple
log = logging.getLogger(__name__)


@hookimpl
def pyls_definitions(config, workspace, document, position):
    engine = SuggestionEngine(workspace.mypy_server.fine_grained_manager)
    definition = find_definition(engine, document.path, position['line'], position['character'])
    if definition is None:
        return []
    path, line, column = definition
    return [{
        'uri': uris.from_fs_path(path),
        'range': {
            'start': {'line': line - 1, 'character': column},
            'end': {'line': line - 1, 'character': column}
        }
    }]

def find_definition(engine, path, line, column) -> Optional[Tuple[str, int, int]]:
    # Columns are zero based in the AST, but rows are 1-based.
    line = line + 1
    node, mypy_file = engine.find_name_expr(path, line, column)

    if node is None:
        log.info('No name expression at this location')
        return None

    def_node = None
    result = ''
    if isinstance(node, NameExpr):
        log.info("Find definition of '%s' (%s:%s)" % (node.name, node.line, node.column + 1))
        def_node = node.node
    elif isinstance(node, Instance):
        log.info("Find definition of '%s' at (%s:%s)" % (node.type.fullname(), node.line, node.column + 1))
        def_node = node.type.defn
    elif isinstance(node, MemberExpr):
        log.info("Find definition of '%s' (%s:%s)" % (node.name, node.line, node.column + 1))
        def_node = get_definition(node, engine.manager.all_types)
    else:
        logging.error(f'Unknown expression: {short_type(node)}')
        
    if def_node is None:
        logging.error('Definition not found')
        return None
    
    filename = engine.get_file(def_node, mypy_file)
    if filename is None:
        log.info("Could not find file name, guessing symbol is defined in same file.")
        filename = path
    # Column is zero-based. Sometimes returns -1 :\
    column = 0 if def_node.column == -1 else def_node.column
    log.info("Definition at %s:%s:%s (%s)" % (filename, def_node.line, column, short_type(def_node)))
    
    return filename, def_node.line, column