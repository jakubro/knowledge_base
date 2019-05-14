import copy
import uuid
from typing import List, Tuple, Union

from knowledge_base import syntax, unification

T_Value = Union[str, syntax.Node]
T_Children = List[syntax.Node]


def convert_to_cnf(node: syntax.Node) -> Tuple[syntax.Node,
                                               syntax.T_Substitution]:
    """Converts node to CNF representation.

    :param node: The node to convert.
    :returns: Node in CNF.
    """

    if not node.is_formula():
        raise ValueError()  # todo: custom exc

    rv = {}
    node = node.denormalize()
    assert node.is_formula()

    for f in (_eliminate_biconditional,
              _eliminate_implication,
              _propagate_negation,
              _standardize_quantified_variables,
              _standardize_free_variables,
              _skolemize,
              _distribute_conjunction):
        state = syntax.WalkState.make()
        node = syntax.walk(node, f, state=state)

        replaced = state.context.get('replaced', {})
        assert not (replaced.keys() & rv.keys())
        rv = unification.compose(rv, replaced)

    node = node.normalize()
    assert node.is_formula()
    assert node.is_cnf()
    return node, rv


def _eliminate_biconditional(node: syntax.Node, *args) -> syntax.Node:
    """Eliminates biconditional.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    Rewrites expressions of type `A <=> B` into `(A => B) & (B => A)`.
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

    Rewrites expressions of type `A => B` into `!A | B`.
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

    Rewrites expressions of type:

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
        qtype = next(k for k in [syntax.UNIVERSAL_QUANTIFIER,
                                 syntax.EXISTENTIAL_QUANTIFIER]
                     if k != child.get_quantifier_type())
        qname = child.get_quantified_variable().value
        rv = syntax.make_quantifier(qtype, qname)

    if rv is None:
        return node
    else:
        children = [x.negate() for x in child.children]
        return syntax.make_formula(rv, children)


def _standardize_quantified_variables(node: syntax.Node,
                                      state: syntax.WalkState) -> syntax.Node:
    """Standardizes quantified variables by giving them unique names.

    :param node: The node to rewrite.
    :param state: Rewriting state.
    :returns: Rewritten node.

    Rewrites expressions of type:

    - `*x: A(x)` into `*var_1: A(var_1)`,
    - `?x: A(x)` into `?var_1: A(var_1)`.
    """

    seen: List[syntax.Node] = state.context.setdefault('seen', [])
    replaced: syntax.T_Substitution = state.context.setdefault('replaced', {})

    # todo: replaced would not work with nested quantified formulas that
    #  reuse the same symbol, but actually never mind - it's a corner case
    #  I don't want to fiddle with now

    if node in seen:
        return node

    if node.is_quantified():
        old = node.get_quantified_variable().value
        if old.startswith('_'):
            return node  # already renamed

        new = _new_variable_name()
        qtype = node.get_quantifier_type()
        quant = syntax.make_quantifier(qtype, new)
        rv = syntax.make_formula(quant, node.children)

        replaced[new] = node.get_quantified_variable()
        state.stack.append((old, new))
        seen.append(rv)
        return rv

    elif node.is_variable():
        # reversed, because we want to rename symbol to the last seen value.
        # Example: We want to rewrite `?x, ?x: x` into `?a: ?b: b`.
        for old, new in reversed(state.stack):
            if old == node.value:
                rv = syntax.make_variable(new)
                seen.append(rv)
                return rv

        return node

    else:
        return node


def _standardize_free_variables(node: syntax.Node,
                                state: syntax.WalkState) -> syntax.Node:
    """Standardizes free variables by giving them unique names.

    :param node: The node to rewrite.
    :param state: Rewriting state.
    :returns: Rewritten node.
    """

    seen: List[syntax.Node] = state.context.setdefault('seen', [])
    replaced: syntax.T_Substitution = state.context.setdefault('replaced', {})

    if node in seen:
        return node

    if node.is_variable():
        old = node.value
        if old.startswith('_'):
            return node  # already renamed

        try:
            new = next(k for k, v in replaced.items() if v.value == old)
        except StopIteration:
            new = _new_variable_name()
            replaced[new] = node

        rv = syntax.make_variable(new)
        seen.append(rv)
        return rv

    else:
        return node


def _skolemize(node: syntax.Node, state: syntax.WalkState) -> syntax.Node:
    """Skolemizes expressions and drops quantifiers.

    :param node: The node to rewrite.
    :param state: Rewriting state.
    :returns: Rewritten node.

    Rewrites expressions of type:

    - `?x: x` into `C1`,
    - `*a: a & ?x: x` into `a & F1(a)`,
    - `*a: a & ?x: x & *b: b & ?y: y` into `a & F1(a) & b & F2(a, b)`,
    """

    if not state.stack:
        state.stack.extend([[], []])

    # enclosing universally quantified variables
    universal: List[str] = state.stack[0]
    replacements: List[Tuple[str, syntax.Node]] = state.stack[1]

    replaced: syntax.T_Substitution = state.context.setdefault('replaced', {})

    if node.is_quantified():
        qtype = node.get_quantifier_type()
        if qtype == syntax.UNIVERSAL_QUANTIFIER:
            qv = node.get_quantified_variable()
            universal.append(qv.value)
        else:
            assert qtype == syntax.EXISTENTIAL_QUANTIFIER

            # store what to replace (actual replacement happens in the
            # elif branch below)

            qv = node.get_quantified_variable()
            old = qv.value

            if universal:
                name = _new_function_name()
                new = syntax.make_function(name, *universal)
            else:
                name = _new_constant_name()
                new = syntax.make_constant(name)

            replaced[new.value] = qv

            replacements.append((old, new))

        # drop quantifiers
        children = node.children
        assert len(children) == 1
        return children[0]

    elif node.is_variable():
        for old, new in replacements:
            if old == node.value:
                return copy.deepcopy(new)
        return node

    else:
        return node


def _distribute_conjunction(node: syntax.Node, *args) -> syntax.Node:
    """Distributes conjunctions over disjunctions.

    :param node: The node to rewrite.
    :returns: Rewritten node.

    Rewrites expressions of type `(A & B) | C` into `(A | C) & (B | C)`.
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

def _new_variable_name() -> str:
    """:returns: New unique variable name."""

    id_ = uuid.uuid4().int
    return f'_v{id_}'


def _new_constant_name() -> str:
    """:returns: New unique constant name."""

    id_ = uuid.uuid4().int
    return f'_C{id_}'


def _new_function_name() -> str:
    """:returns: New unique function name."""

    id_ = uuid.uuid4().int
    return f'_H{id_}'
