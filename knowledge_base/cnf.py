import copy
from typing import Callable, List, NamedTuple, TypeVar, Union

import syntax

T = TypeVar('T')
T_Value = Union[str, syntax.Node]
T_Children = List[syntax.Node]


# CNF
# -----------------------------------------------------------------------------

def convert_to_cnf(node: T) -> T:
    """Converts node to CNF representation.

    :param node: The node to convert.
    :returns: Node in CNF.
    """

    funcs = [eliminate_biconditional,
             eliminate_implication,
             propagate_negation,
             standardize_variables,
             skolemize,
             drop_quantifiers,
             distribute_conjunction]

    for f in funcs:
        state = WalkState.make()
        node = walk(node, state, f)

        maxlen = int(max((len(z.__name__) for z in funcs)))
        print(f.__name__.rjust(maxlen) + ':\t' + str(node))

    return node


def eliminate_biconditional(node: syntax.Node, *args, **kwargs) -> syntax.Node:
    """Eliminates biconditional.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type `A <=> B` into `(A => B) & (B => A)`.

    """

    if node.value == syntax.EQUIVALENCE:
        a, b = node.children
        child1 = make_formula(syntax.IMPLICATION, [a, b])
        child2 = make_formula(syntax.IMPLICATION, [b, a])
        children = [child1, child2]
        return make_formula(syntax.CONJUNCTION, children)
    return node


def eliminate_implication(node: syntax.Node, *args, **kwargs) -> syntax.Node:
    """Eliminates implication.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type `A => B` into `!A | B`.

    """

    if node.value == syntax.IMPLICATION:
        a, b = node.children
        children = [a.negate(), b]
        return make_formula(syntax.DISJUNCTION, children)
    return node


def propagate_negation(node: syntax.Node, *args, **kwargs) -> syntax.Node:
    """Propagates negations down the syntax tree.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type:

    - `!!A` into `A`,
    - `!(A & B)` into `!A | !B`,
    - `!(A | B)` into `!A & !B`,
    - `!(*x: A)` into `?x: !A`,`
    - `!(?x: A)` into `*x: !A`.

    """

    if node.value == syntax.NEGATION:
        assert len(node.children) == 1
        child = node.children[0]
        if isinstance(child, syntax.Node):
            rv = None

            # Double negation
            if child.value == syntax.NEGATION:
                return child.children[0]

            # De Morgan
            elif child.value == syntax.CONJUNCTION:
                rv = syntax.DISJUNCTION

            # De Morgan
            elif child.value == syntax.DISJUNCTION:
                rv = syntax.CONJUNCTION

            # Flip Quantifiers
            elif isinstance(child.value, syntax.Node):
                try:
                    qval, qname = child.value.as_quantifier()
                except ValueError:
                    pass
                else:
                    if qval == syntax.UNIVERSAL_QUANTIFIER:
                        rv = make_quantifier(syntax.EXISTENTIAL_QUANTIFIER,
                                             qname)

                    elif qval == syntax.EXISTENTIAL_QUANTIFIER:
                        rv = make_quantifier(syntax.UNIVERSAL_QUANTIFIER,
                                             qname)

            if rv is not None:
                children = [x.negate() for x in child.children]
                return make_formula(rv, children)

    return node


def standardize_variables(node: syntax.Node,
                          state: 'WalkState') -> syntax.Node:
    """Standardizes quantified variables by giving them to unique names.

    :param node: The node to rewrite.
    :param state: Rewriting state.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type:

    - `*x: A(x)` into `*var_1: A(var_1)`,
    - `?x: A(x)` into `?var_1: A(var_1)`.

    """

    try:
        value, name = node.get_quantifier()
    except ValueError:
        if node.type_ == syntax.VARIABLE:
            # reversed, because we want to rename symbol to last seen value.
            # Example: We want to rewrite `?x, ?x: x` into `?a: ?b: b`.
            for old, new in reversed(state.stack):
                if old == node.value:
                    return make_variable(new)
        return node
    else:
        new = new_variable_name(state)
        state.stack.append((name, new))
        quant = make_quantifier(value, new)
        return make_formula(quant, node.children)


def skolemize(node: syntax.Node, state: 'WalkState') -> syntax.Node:
    """Skolemizes sentences by replacing those enclosed only by existentially
    qualified variables with unique constants (Skolem constants), and those
    sentences enclosed by universally quantified variables with unique
    functions (Skolem functions).

    :param node: The node to rewrite.
    :param state: Rewriting state.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type:

    - `*x: A(x)` into `*x: A(Func_1(x))`,
    - `?x: A(x)` into `?x: A(CONST_1)`.

    """

    try:
        value, name = node.get_quantifier()
    except ValueError:
        seen = state.context.setdefault('seen', [])
        if node.type_ == syntax.VARIABLE and node not in seen:
            args = []  # enclosing universally quantified variables
            for qvalue, old, new in state.stack:
                if qvalue == syntax.UNIVERSAL_QUANTIFIER:
                    args.append(old)
                if old == node.value:
                    if args:
                        # replace with a Skolem function
                        rv = make_function(new, args)
                        seen.extend(rv.children)
                        return rv
                    else:
                        # replace with a Skolem constant
                        return make_variable(new)
        return node
    else:
        qvalues = [v for v, *_ in state.stack]
        for v in (value, *qvalues):
            if v == syntax.UNIVERSAL_QUANTIFIER:
                new = new_function_name(state)
                break
        else:
            new = new_constant_name(state)

        appenddefault(state.context, 'seen', node.value)
        state.stack.append((value, name, new))

        return node


def drop_quantifiers(node: syntax.Node, *args, **kwargs) -> syntax.Node:
    """Drops quantifiers from sentences.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type:

    - `*x: A(x)` into `A(x)`,
    - `?x: A(x)` into `A(x)`.

    """

    if (node.type_ == syntax.FORMULA
            and isinstance(node.value, syntax.Node)
            and node.value.type_ == syntax.QUANTIFIER):
        children = node.children
        assert len(children) == 1
        return children[0]
    return node


def distribute_conjunction(node: syntax.Node, *args, **kwargs) -> syntax.Node:
    """Distributes conjunctions over disjunctions.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type `(A & B) | C` into `(A | C) & (B | C)`.

    """

    if node.value == syntax.DISJUNCTION:
        for child in node.children:
            other = next(x for x in node.children if x is not child)
            if child.value == syntax.CONJUNCTION:
                a, b = child.children
                rv1 = make_formula(syntax.DISJUNCTION, [a, other])
                rv2 = make_formula(syntax.DISJUNCTION, [b, other])
                return make_formula(syntax.CONJUNCTION, [rv1, rv2])
    return node


# Renaming
# -----------------------------------------------------------------------------

# todo: disable first char to be "_" in syntax.py

def new_variable_name(state: 'WalkState') -> str:
    """:returns: New unique variable name."""

    ctx = state.context
    counter = incrementdefault(ctx, 'var_counter')
    return f'_v{counter}'


def new_constant_name(state: 'WalkState') -> str:
    """:returns: New unique constant name."""

    ctx = state.context
    counter = incrementdefault(ctx, 'const_counter')
    return f'_C{counter}'


def new_function_name(state: 'WalkState') -> str:
    """:returns: New unique function name."""

    ctx = state.context
    counter = incrementdefault(ctx, 'func_counter')
    return f'_H{counter}'


# Syntax Tree Navigation
# -----------------------------------------------------------------------------

def walk(node: T,
         state: 'WalkState',
         func: Callable[[syntax.Node, 'WalkState'], syntax.Node]) -> T:
    """Invokes `func` on each node and then recurses into node's value and
    children.

    :param node: The node to traverse.
    :param state: Traversing state.
    :param func: Function to apply to each node traversed. (This function
        returns the same or a modified node.)
    :returns: Traversed node.
    """

    if isinstance(node, syntax.Node):
        node = func(node, state)
        value = walk(node.value, state, func)
        children = walk(node.children, state, func)
        return syntax.Node(type_=node.type_,
                           value=value,
                           children=children)

    elif isinstance(node, list):
        rv = []
        for child in node:
            ctx = state.copy()
            child = walk(child, ctx, func)
            rv.append(child)
        return rv

    else:
        return node


class WalkState(NamedTuple):
    #: Global dictionary.
    context: dict

    #: List maintained only within parent-child hierarchy.
    stack: list

    def copy(self):
        return WalkState(context=self.context,
                         stack=copy.deepcopy(self.stack))

    @classmethod
    def make(cls, state: 'WalkState' = None) -> 'WalkState':
        return (state.copy()
                if state
                else WalkState(context={}, stack=[]))


# Syntax Tree Builders
# -----------------------------------------------------------------------------

def make_formula(value: T_Value, children: T_Children) -> syntax.Node:
    return syntax.Node(type_=syntax.FORMULA,
                       value=value,
                       children=children)


def make_quantifier(value: T_Value, name: str) -> syntax.Node:
    return syntax.Node(type_=syntax.QUANTIFIER,
                       value=value,
                       children=[make_variable(name)])


def make_function(value: T_Value, args: List[T_Value]) -> syntax.Node:
    return syntax.Node(type_=syntax.FUNCTIONAL,
                       value=value,
                       children=[make_variable(a) for a in args])


def make_variable(name: str) -> syntax.Node:
    return syntax.Node(type_=syntax.VARIABLE,
                       value=name,
                       children=[])


# Helpers
# -----------------------------------------------------------------------------

def incrementdefault(obj: dict, key, default: int = 0):
    val = obj.setdefault(key, default) + 1
    obj[key] = val
    return val


def appenddefault(obj: dict, key, val, default: list = None) -> list:
    default = [] if default is None else default
    arr = obj.setdefault(key, default)
    arr.append(val)
    return arr
