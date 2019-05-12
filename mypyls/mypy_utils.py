import functools
from mypy.util import short_type
from mypy.nodes import (
    ARG_POS, ARG_STAR, ARG_NAMED, ARG_STAR2, ARG_NAMED_OPT, FuncDef, MypyFile, SymbolTable,
    SymbolNode, TypeInfo, Node, Expression, ReturnStmt, NameExpr, SymbolTableNode, Var,
    AssignmentStmt, Context, RefExpr, FuncBase, MemberExpr
)
from mypy.types import (
    Type, AnyType, TypeOfAny, CallableType, UnionType, NoneTyp, Instance, is_optional,
)
from mypy.traverser import TraverserVisitor
from typing import Optional, Dict, Tuple
import mypy

class NameFinder(TraverserVisitor):
    node: Optional[NameExpr] = None
    def __init__(self, line, column) -> None:
        super().__init__()
        self.line = line
        self.column = column

    def visit_name_expr(self, node: 'mypy.nodes.NameExpr') -> None:
        if node_contains_offset(node, self.line, self.column):
            self.node = node
    
    # TODO: visit_var, visit_func_def etc.


class NodeFound(Exception):
    pass

def universal_visitor():
    def decorator(visitor):
        visit_funcs = [func for func in dir(visitor) if func.startswith('visit_')]
        class UniversalVisitor(visitor):
            pass

        for func in visit_funcs:
            def wrap(f):
                orig_func = getattr(visitor, f)
                @functools.wraps(orig_func)
                def wrapped(self, node, *args, **kwargs):
                    orig_func(self, node, *args, **kwargs)
                    self.process_node(node)
                return wrapped
            setattr(UniversalVisitor, func, wrap(func))

        return UniversalVisitor
    return decorator


@universal_visitor()
class NodeFinderByLocation(TraverserVisitor):
    node: Optional[Context] = None

    def __init__(self, line, column) -> None:
        self.line = line
        self.column = column

    def process_node(self, node: Context):
        if node_contains_offset(node, self.line, self.column):
            self.node = node
            raise NodeFound()

    def visit_assignment_stmt(self, o: AssignmentStmt):
        if o.type:
            self.process_node(o.type)
        super().visit_assignment_stmt(o)

    def visit_func_def(self, o: FuncDef):
        if o.type:
            if isinstance(o.type, CallableType):
                for arg_type in o.type.arg_types:
                    self.process_node(arg_type)
                self.process_node(o.type.ret_type)
        return super().visit_func_def(o)


def get_definition(node: MemberExpr, typemap: Dict[Expression, Type]) -> Optional[Node]:
    symbol_table_node: Optional[SymbolTableNode] = None

    typ = typemap.get(node.expr)
    if typ is not None:
        if isinstance(typ, Instance):
            symbol_table_node = get_symbol(typ.type, node.name)
        else:
            return None
    else:
        symbol_table_node = get_member(node.expr, node.name)

    if symbol_table_node is None:
        return None
    return symbol_table_node.node

def get_member(node: Optional[object], name: str) -> Optional[SymbolTableNode]:
    if isinstance(node, MypyFile):
        return node.names.get(name)
    elif isinstance(node, NameExpr):
        return get_member(node.node, name)
    elif isinstance(node, Var):
        return get_member(node.type, name)
    elif isinstance(node, Instance):
        return get_member(node.type, name)
    else:
        return None

def get_symbol(typeinfo: Optional[TypeInfo], name) -> Optional[SymbolTableNode]:
    if typeinfo is None:
        return None
    return typeinfo.get(name)

@universal_visitor()
class NodeFinder(TraverserVisitor):
    def __init__(self, node_to_find: Node):
        self.node_to_find = node_to_find
        self.found = False

    def process_node(self, node: Node):
        if self.node_to_find == node:
            self.found = True



def node_contains_offset(node, line, column):
    if (line < node.line or line > node.end_line) or (
        node.line == line and column < node.column) or (
        node.end_line == line and column > node.end_column):
        return False
    
    return True



# Copied from mypy.lookup but adjusted to return containing module as well.
def lookup_fully_qualified(name: str, modules: Dict[str, MypyFile],
                           raise_on_missing: bool = False) -> Optional[Tuple[SymbolTableNode, MypyFile]]:
    """Find a symbol using it fully qualified name.

    The algorithm has two steps: first we try splitting the name on '.' to find
    the module, then iteratively look for each next chunk after a '.' (e.g. for
    nested classes).

    This function should *not* be used to find a module. Those should be looked
    in the modules dictionary.
    """
    head = name
    rest = []
    # 1. Find a module tree in modules dictionary.
    while True:
        if '.' not in head:
            if raise_on_missing:
                assert '.' in head, "Cannot find module for %s" % (name,)
            return None
        head, tail = head.rsplit('.', maxsplit=1)
        rest.append(tail)
        mod = modules.get(head)
        if mod is not None:
            break
    names = mod.names
    # 2. Find the symbol in the module tree.
    if not rest:
        # Looks like a module, don't use this to avoid confusions.
        if raise_on_missing:
            assert rest, "Cannot find %s, got a module symbol" % (name,)
        return None
    while True:
        key = rest.pop()
        if key not in names:
            if raise_on_missing:
                assert key in names, "Cannot find component %r for %r" % (key, name)
            return None
        stnode = names[key]
        if not rest:
            return stnode, mod
        node = stnode.node
        # In fine-grained mode, could be a cross-reference to a deleted module
        # or a Var made up for a missing module.
        if not isinstance(node, TypeInfo):
            if raise_on_missing:
                assert node, "Cannot find %s" % (name,)
            return None
        names = node.names


def find_name_expr(fgmanager, path: str, line: int, column: int) -> Tuple[Optional[Context], MypyFile]:
    states = [t for t in fgmanager.graph.values() if t.path == path]
    if not states:
        loaded = '\n'.join([t.path or '<None>' for t in fgmanager.graph.values()])
        return None, None
    tree = states[0].tree
    assert tree is not None

    finder = NodeFinderByLocation(line, column)
    try:
        tree.accept(finder)
    except NodeFound:
        pass
    
    return finder.node, tree

def get_file(manager, node: Node, mypy_file: MypyFile) -> Optional[str]:
    # print(f'looking for {type(node)}')
    if isinstance(node, MypyFile):
        return node.path

    mypy_files = [mypy_file]

    if isinstance(node, Var):
        tup = lookup_fully_qualified(node.fullname(), manager.modules)
        if tup is None:
            # print('Var not found in modules')
            return None
        else:
            var, mod = tup
            if var.node == node:
                return mod.path
            else:
                # print(f'Found var but not identical. Found type is {short_type(var.node)}')
                if mod != mypy_file:
                    mypy_files.append(mod)

    # Search in current file first because the definition is usually in the same file.
    mypy_files.extend([f for f in manager.modules.values() if f not in mypy_files])
    
    if isinstance(node, TypeInfo):
        node = node.defn
    finder = NodeFinder(node)
    for file in mypy_files:
        # print('looking in %s' % file.path)
        file.accept(finder)
        if finder.found:
            return file.path

    return None

class ModuleNotAnalyzed(Exception):
    pass