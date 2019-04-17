from typing import List, Tuple, TypeVar, Union

import syntax
from utils import incrementdefault

T = TypeVar('T')
T_Value = Union[str, syntax.Node]
T_Children = List[syntax.Node]


# Verification
# -----------------------------------------------------------------------------

def is_cnf(node: syntax.Node) -> bool:
    return (_is_cnf_conjunction(node)
            or _is_cnf_disjunction(node)
            or _is_cnf_atom(node))


def _is_cnf_conjunction(node: syntax.Node) -> bool:
    return (node.is_conjunction()
            and all((_is_cnf_conjunction(x)
                     or _is_cnf_disjunction(x)
                     or _is_cnf_atom(x))
                    for x in node.children))


def _is_cnf_disjunction(node: syntax.Node) -> bool:
    return (_is_term(node)
            or (node.is_disjunction()
                and all((_is_cnf_disjunction(x)
                         or _is_cnf_atom(x))
                        for x in node.children)))


def _is_cnf_atom(node: syntax.Node) -> bool:
    return (_is_term(node)
            or (node.is_negation()
                and _is_term(node.children[0])))


def _is_term(node: syntax.Node) -> bool:
    return (node.is_variable()
            or (node.is_function()
                and all(_is_term(x) for x in node.children)))


# Conversion
# -----------------------------------------------------------------------------

def convert_to_cnf(node: T) -> T:
    """Converts node to CNF representation.

    :param node: The node to convert.
    :returns: Node in CNF.
    """

    for f in [_eliminate_biconditional,
              _eliminate_implication,
              _propagate_negation,
              _standardize_variables,
              _skolemize,
              _distribute_conjunction]:
        state = syntax.WalkState.make()
        node = syntax.walk(node, state, f)
    return node


def _eliminate_biconditional(node: syntax.Node, *args) -> syntax.Node:
    """Eliminates biconditional.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type `A <=> B` into `(A => B) & (B => A)`.

    """

    if not node.is_equivalence():
        return node

    a, b = node.children
    child1 = syntax.make_formula(syntax.IMPLICATION, [a, b])
    child2 = syntax.make_formula(syntax.IMPLICATION, [b, a])
    children = [child1, child2]
    return syntax.make_formula(syntax.CONJUNCTION, children)


def _eliminate_implication(node: syntax.Node, *args) -> syntax.Node:
    """Eliminates implication.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type `A => B` into `!A | B`.

    """

    if not node.is_implication():
        return node

    a, b = node.children
    children = [a.negate(), b]
    return syntax.make_formula(syntax.DISJUNCTION, children)


def _propagate_negation(node: syntax.Node, *args) -> syntax.Node:
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

    if not node.is_negation():
        return node

    rv = None
    child = node.children[0]

    # Double negation
    if child.is_negation():
        return child.children[0]

    # De Morgan
    elif child.is_conjunction():
        rv = syntax.DISJUNCTION

    # De Morgan
    elif child.is_disjunction():
        rv = syntax.CONJUNCTION

    # Flip Quantifiers
    elif child.is_quantified():
        qtype = (syntax.EXISTENTIAL_QUANTIFIER
                 if child.is_universal_quantifier()
                 else syntax.UNIVERSAL_QUANTIFIER)
        qname = child.get_quantified_variable().get_variable_name()
        rv = syntax.make_quantifier(qtype, qname)

    if rv is None:
        return node
    else:
        children = [x.negate() for x in child.children]
        return syntax.make_formula(rv, children)


def _standardize_variables(node: syntax.Node,
                           state: syntax.WalkState) -> syntax.Node:
    """Standardizes quantified variables by giving them to unique names.

    :param node: The node to rewrite.
    :param state: Rewriting state.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type:

    - `*x: A(x)` into `*var_1: A(var_1)`,
    - `?x: A(x)` into `?var_1: A(var_1)`.

    """

    seen: List[int] = state.context.setdefault('seen', [])

    if id(node) in seen:
        return node

    elif node.is_quantified():
        old = node.get_quantified_variable().get_variable_name()
        new = _new_variable_name(state)
        state.stack.append((old, new))
        qtype = node.get_quantifier_type()
        quant = syntax.make_quantifier(qtype, new)
        rv = syntax.make_formula(quant, node.children)
        seen.append(id(rv))
        return rv

    elif node.is_variable():
        # reversed, because we want to rename symbol to the last seen value.
        # Example: We want to rewrite `?x, ?x: x` into `?a: ?b: b`.
        for old, new in reversed(state.stack):
            if old == node.value:
                rv = syntax.make_variable(new)
                seen.append(id(rv))
                return rv

        return node

    else:
        return node


def _skolemize(node: syntax.Node, state: syntax.WalkState) -> syntax.Node:
    """Skolemizes sentences by replacing those enclosed only by existentially
    qualified variables with unique constants (Skolem constants), and those
    sentences enclosed by universally quantified variables with unique
    functions (Skolem functions).

    :param node: The node to rewrite.
    :param state: Rewriting state.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type:

    - `*x: A(x)` into `A(Func_1(x))`,
    - `?x: A(x)` into `A(CONST_1)`.

    """

    stack: List[Tuple[str, str, str]] = state.stack
    seen: List[int] = state.context.setdefault('seen', [])

    if id(node) in seen:
        return node

    elif node.is_quantified():
        qv = node.get_quantified_variable()
        old = qv.get_variable_name()
        qtype = node.get_quantifier_type()

        quantifiers = [t for t, n, _ in stack]
        for qt in (qtype, *quantifiers):
            if qt == syntax.UNIVERSAL_QUANTIFIER:
                new = _new_function_name(state)
                break
        else:
            new = _new_constant_name(state)

        seen.append(id(qv))
        stack.append((qtype, old, new))

        # drop quantifiers
        children = node.children
        assert len(children) == 1
        return children[0]

    elif node.is_variable():
        args = []  # enclosing universally quantified variables
        for qtype, old, new in stack:
            if qtype == syntax.UNIVERSAL_QUANTIFIER:
                args.append(old)
            if old == node.get_variable_name():
                if args:
                    # replace with a Skolem function
                    rv = syntax.make_function(new, args)
                    seen.extend(id(r) for r in rv.children)
                    return rv
                else:
                    # replace with a Skolem constant
                    return syntax.make_variable(new)
        return node

    else:
        return node


def _distribute_conjunction(node: syntax.Node, *args) -> syntax.Node:
    """Distributes conjunctions over disjunctions.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    **Remarks:**

    Rewrites sentences of type `(A & B) | C` into `(A | C) & (B | C)`.

    """

    if not node.is_disjunction():
        return node

    for child in node.children:
        other = next(x for x in node.children if x is not child)
        if child.is_conjunction():
            a, b = child.children
            rv1 = syntax.make_formula(syntax.DISJUNCTION, [a, other])
            rv2 = syntax.make_formula(syntax.DISJUNCTION, [b, other])
            rv = syntax.make_formula(syntax.CONJUNCTION, [rv1, rv2])
            return rv

    return node


# Renaming
# -----------------------------------------------------------------------------

def _new_variable_name(state: syntax.WalkState) -> str:
    """:returns: New unique variable name."""

    ctx = state.context
    counter = incrementdefault(ctx, 'var_counter')
    return f'_v{counter}'


def _new_constant_name(state: syntax.WalkState) -> str:
    """:returns: New unique constant name."""

    ctx = state.context
    counter = incrementdefault(ctx, 'const_counter')
    return f'_C{counter}'


def _new_function_name(state: syntax.WalkState) -> str:
    """:returns: New unique function name."""

    ctx = state.context
    counter = incrementdefault(ctx, 'func_counter')
    return f'_H{counter}'
