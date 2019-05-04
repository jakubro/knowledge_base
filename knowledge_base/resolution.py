import itertools
import logging
from typing import List, Optional, Set

import knowledge_base.cnf as cnf
import knowledge_base.syntax as syntax
import knowledge_base.unification as unification

_log = logging.getLogger()


def resolve(facts: List[syntax.Node], probe: syntax.Node) -> bool:
    f = syntax.make_formula(syntax.CONJUNCTION, [*facts, probe.negate()])
    f = cnf.convert_to_cnf(f)

    # breaks down the sentence into disjunction clauses
    clauses: Set[syntax.Node] = ({*f.children}
                                 if f.is_conjunction()
                                 else {f})

    new = set()

    while True:
        for p, q in itertools.combinations(clauses, 2):
            resolvents = _resolve_disjunctions(p, q)

            if resolvents is None:
                continue

            if _log.level >= logging.DEBUG:
                res = syntax.make_formula(syntax.CONJUNCTION, resolvents)
                _log.debug(f"p: {p}")
                _log.debug(f"q: {q}")
                _log.debug(f"resolvents: {res}")

            if not resolvents:
                # f is unsatisfiable, therefore probe is entailed in facts
                return True

            new = {*new, *resolvents}

        if new.issubset(clauses):
            # f is satisfiable, therefore probe is not entailed in facts
            return False

        clauses = {*clauses, *new}


# todo: temporary renaming before resolving

def _resolve_disjunctions(p: syntax.Node,
                          q: syntax.Node) -> List[syntax.Node]:
    """If the arguments are resolvable, then returns their resolvent, otherwise
    returns None.

    **Remarks:**

    First-order resolution rule of inference

    Example 1:

    - assume: (x | y) & (!y | z)
    - infer:  x | z

    Example 2:

    - assume: (f(x) | g(x)) & (!g(y) | h(y))
    - infer:  f(x) | h(x)

    """

    assert p.is_disjunction() or p.is_atomic()
    assert q.is_disjunction() or q.is_atomic()

    # break down sentences into atoms
    p = ({*p.children} if p.is_disjunction() else {p})
    q = ({*q.children} if q.is_disjunction() else {q})

    found = False
    resolvents = [*p, *q]
    for x, y in itertools.product(p, q):
        subst = _resolve_atoms(x, y)

        if subst is None:
            continue

        found = True

        resolvents.remove(x)
        resolvents.remove(y)

        resolvents = [r.apply(subst) for r in resolvents]

    return resolvents if found else None


def _resolve_atoms(x: syntax.Node,
                   y: syntax.Node) -> Optional[syntax.T_Substitution]:
    """If the arguments are resolvable, then returns their unifier used to
    produce the resolvent, otherwise returns None."""

    assert x.is_atomic()
    assert y.is_atomic()

    # first-order resolution rule of inference
    # assume: x & !x

    x_neg = x.is_negation()
    y_neg = y.is_negation()

    if x_neg == y_neg:
        return None
    elif x_neg:
        x = x.children[0]
    else:
        assert y_neg
        y = y.children[0]

    try:
        return unification.unify(x, y)
    except ValueError:
        return None
