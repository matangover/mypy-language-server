# Copyright 2017 Palantir Technologies, Inc.
import logging
from pyls import hookimpl, _utils
from mypy.suggestions import SuggestionEngine, get_definition
from mypy.nodes import (
    FuncDef, MypyFile, SymbolTable,
    SymbolNode, TypeInfo, Node, Expression, ReturnStmt, NameExpr, SymbolTableNode, Var,
    AssignmentStmt, Context, RefExpr, FuncBase, MemberExpr, Import
)
from typing import Optional
from mypy.types import (
    Type, AnyType, TypeOfAny, CallableType, UnionType, NoneTyp, Instance, is_optional,
)
from mypy.util import short_type
from .mypy_definition import get_import_definition

log = logging.getLogger(__name__)


@hookimpl
def pyls_hover(workspace, document, position):
    engine = SuggestionEngine(workspace.mypy_server.fine_grained_manager)
    hover = get_hover(engine, document.path, position['line'], position['character'])
    return {'contents': hover or ''}


def get_hover(engine, path, line, column) -> Optional[str]:
    # Columns are zero based in the AST, but rows are 1-based.
    line = line + 1
    node, mypy_file = engine.find_name_expr(path, line, column)

    if node is None:
        log.info('No name expression at this location')
        return None

    def_node: Optional[Node] = None
    if isinstance(node, NameExpr):
        def_node = node.node
    elif isinstance(node, Instance):
        def_node = node.type
    elif isinstance(node, MemberExpr):
        def_node = get_definition(node, engine.manager.all_types)
    elif isinstance(node, Import):
        def_node = get_import_definition(node, mypy_file, line, column, path)
    else:
        log.info(f'Unknown expression: {short_type(node)}')
        return None

    if isinstance(def_node, Var):
        var_type = 'Unknown' if def_node.type is None else str(def_node.type)
        return f'{def_node.name()}: {var_type}'

        # if isinstance(def_node.type, AnyType):
        #     return 'Any'
        # if isinstance(def_node.type, Instance):
        #     return def_node.type.type.fullname()
        # return short_type(def_node.type)

    if isinstance(def_node, TypeInfo):
        return def_node.fullname()

    if isinstance(def_node, MypyFile):
        return f'{def_node.fullname()}: module'

    if isinstance(def_node, FuncBase):
        result = f'function {def_node.fullname()}'
        if isinstance(def_node, FuncDef):
            result += f'({", ".join(def_node.arg_names)})'
        return result

    return None
