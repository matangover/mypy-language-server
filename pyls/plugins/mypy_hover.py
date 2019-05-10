# Copyright 2017 Palantir Technologies, Inc.
import logging
from pyls import hookimpl, _utils
from mypy.nodes import (
    FuncDef, MypyFile, SymbolTable,
    SymbolNode, TypeInfo, Node, Expression, ReturnStmt, NameExpr, SymbolTableNode, Var,
    AssignmentStmt, Context, RefExpr, FuncBase, MemberExpr, ImportBase
)
from typing import Optional
from mypy.types import (
    Type, AnyType, TypeOfAny, CallableType, UnionType, NoneTyp, Instance, is_optional,
)
from mypy.util import short_type
from .mypy_definition import get_import_definition
from . import mypy_utils

log = logging.getLogger(__name__)


@hookimpl
def pyls_hover(workspace, document, position):
    fgmanager = workspace.mypy_server.fine_grained_manager
    hover = get_hover(fgmanager, document.path, position['line'], position['character'])
    if hover:
        return {'contents': hover}
    else:
        return None


def get_hover(fgmanager, path, line, column) -> Optional[str]:
    # Columns are zero based in the AST, but rows are 1-based.
    line = line + 1
    node, mypy_file = mypy_utils.find_name_expr(fgmanager, path, line, column)

    if node is None:
        log.info('No name expression at this location')
        return None

    def_node: Optional[Node] = None
    if isinstance(node, NameExpr):
        def_node = node.node
    elif isinstance(node, Instance):
        def_node = node.type
    elif isinstance(node, MemberExpr):
        def_node = mypy_utils.get_definition(node, fgmanager.manager.all_types)
    elif isinstance(node, ImportBase):
        def_node = get_import_definition(fgmanager.manager, node, mypy_file, line, column, path)
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
