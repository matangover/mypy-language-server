import logging
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
import re

log = logging.getLogger(__name__)

def hover(workspace, document, position):
    fgmanager = workspace.mypy_server.fine_grained_manager
    if not fgmanager:
        return None
    hover = get_hover(fgmanager, document.path, position['line'], position['character'])
    if hover:
        return {
            'contents': {
                'kind': 'markdown',
                'value': python_highlight(hover)
            }
        }
    else:
        return None


def get_hover(fgmanager, path, line, column) -> Optional[str]:
    # Columns are zero based in the AST, but rows are 1-based.
    line = line + 1
    node, mypy_file = mypy_utils.find_name_expr(fgmanager, path, line, column)

    if mypy_file is None:
        log.error(f'Module not analyzed by mypy: {path}')
        return None

    if node is None:
        log.info('No name expression at this location')
        return None

    def_node: Optional[Node] = None
    if isinstance(node, NameExpr):
        if node.fullname == 'builtins.None':
            return None
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
        var_type = 'Unknown' if def_node.type is None else type_to_string(def_node.type)
        return f'{def_node.name()}: {var_type}'

    if isinstance(def_node, TypeInfo):
        return f'class {fullname(def_node)}'

    if isinstance(def_node, MypyFile):
        return f'{def_node.fullname()} (module)'

    if isinstance(def_node, FuncBase):
        type_str = ''
        node_type = fgmanager.manager.all_types.get(node) or def_node.type
        if node_type:
            type_str = type_to_string(node_type)
            if type_str.startswith('def '):
                type_str = type_str[4:]
        return fullname(def_node) + type_str

    return None

def python_highlight(value):
    return f'```python\n{value}\n```'

def type_to_string(typ: Type) -> str:
    type_str = str(typ)
    # Strip any occurrence of 'builtins.' unless it's part of an identifier.
    # (e.g. don't strip some_builtins.blah or a.builtins.hello )
    # This might miss some cases with Unicode identifiers, but it's
    # sufficiently rare to have a type called שלום_builtins.טירוף.
    # https://docs.python.org/3/reference/lexical_analysis.html#identifiers
    return re.sub(r'([^.a-zA-Z0-9_]|^)builtins\.', r'\1', type_str)

def fullname(node: SymbolNode) -> str:
    name = node.fullname()
    if name.startswith('builtins.'):
        return name[9:]
    else:
        return name
