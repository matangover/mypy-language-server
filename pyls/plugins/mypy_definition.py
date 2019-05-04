# Copyright 2017 Palantir Technologies, Inc.
import logging
from pyls import hookimpl, uris
from mypy.suggestions import SuggestionEngine, get_definition
from mypy.util import short_type

from mypy.nodes import (
    FuncDef, MypyFile, SymbolTable,
    SymbolNode, TypeInfo, Node, Expression, ReturnStmt, NameExpr, SymbolTableNode, Var,
    AssignmentStmt, Context, RefExpr, FuncBase, MemberExpr, Import
)
from mypy.types import (
    Type, AnyType, TypeOfAny, CallableType, UnionType, NoneTyp, Instance, is_optional,
)

from typing import Optional, Tuple, List
import parser
import symbol
import token

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
    elif isinstance(node, Import):
        log.info("Find definition of import (%s:%s)" % (node.line, node.column + 1))
        def_node = get_import_definition(node, mypy_file, line, column, path)
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

def get_import_definition(import_node: Node, mypy_file: MypyFile, line: int, column: int, path: str) -> Optional[Node]:
    # lines are 1 based, cols 0 based.

    with open(path) as file:
        code_lines: List[str] = file.readlines()

    if import_node.line == import_node.end_line:
        import_code = code_lines[import_node.line-1][import_node.column:import_node.end_column]
    else:
        first_line = code_lines[import_node.line-1][import_node.column:]
        intermediate_lines = ''.join(code_lines[import_node.line:import_node.end_line-1])
        last_line = code_lines[import_node.end_line-1][:import_node.end_column]
        import_code = first_line + intermediate_lines + last_line
    
    suite = parser.suite(import_code).tolist(True, True)
    line_relative_to_import = line - import_node.line + 1
    column_relative_to_import = column
    if line == import_node.line:
        column_relative_to_import -= import_node.column
    name = find_import_name(line_relative_to_import, column_relative_to_import, suite)
    if not name:
        return None
    return mypy_file.names[name].node

def find_import_name(line, column, suite):
    if token.ISTERMINAL(suite[0]):
        return None

    for element in suite[1:]:
        if element[0] == symbol.dotted_name:
            for dotted_name_part in element[1:]:
                token_type, name, name_line, name_column = dotted_name_part
                if token_type == token.NAME and token_contains_offset(name_line, name_column, len(name), line, column):
                    return name
            # TODO: dotted names (e.g. import os.path).
        else:
            result = find_import_name(line, column, element)
            if result:
                return result

    return None

def token_contains_offset(token_line, token_column, token_length, line, column):
    if token_line != line:
        return False
    
    return token_column <= column <= token_column + token_length
