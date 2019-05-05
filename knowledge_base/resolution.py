import itertools
import logging
from typing import List, Optional, Set, Tuple

import knowledge_base.cnf as cnf
import knowledge_base.syntax as syntax
import knowledge_base.unification as unification

_log = logging.getLogger()


def resolve(premises: List[syntax.Node], conclusion: syntax.Node) -> bool:
    if not premises:
        return True

    # breaks down the sentence into disjunction clauses
    clauses = []
    for f in (*premises, conclusion.negate()):
        f = cnf.convert_to_cnf(f)
        clauses.extend(f.clause_form())
    clauses = frozenset(clauses)

    seen = []
    while True:
        for p, q in itertools.combinations(clauses, 2):
            if (p, q) in seen:
                continue
            seen.append((p, q))

            try:
                subst, resolvents = _resolve_disjunctions(p, q)
            except StopIteration:
                # cannot resolve p and q
                continue
            else:
                resolvents = frozenset(resolvents)

            _log.debug(f"{set(p)} + {set(q)} -> " + (str(set(resolvents)
                                                         if resolvents
                                                         else '■')))

            # new = {k.apply(subst) for k in new}
            # clauses = {k.apply(subst) for k in clauses}

            if not resolvents:
                # we found a contradiction therefore, therefore
                # the conclusion is entailed by premises
                return True

            if not resolvents.issubset(clauses):
                clauses = frozenset({*clauses, resolvents})
                break
        else:
            # no new clauses can be derived, therefore
            # the conclusion is not entailed by premises
            return False


# todo: temporary renaming before resolving

def _resolve_disjunctions(p: Set[syntax.Node],
                          q: Set[syntax.Node]) -> Tuple[syntax.T_Substitution,
                                                        Set[syntax.Node]]:
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

    for x, y in itertools.product(p, q):
        subst = _resolve_literals(x, y)
        if subst is None:
            continue

        resolvents = [*p, *q]
        resolvents.remove(x)
        resolvents.remove(y)
        resolvents = {k.apply(subst) for k in resolvents}
        return subst, resolvents

    raise StopIteration()


def _resolve_literals(x: syntax.Node,
                      y: syntax.Node) -> Optional[syntax.T_Substitution]:
    """If the arguments are complementary (one is positive literal, and the
    another is its negation) literals, then returns their unifier, otherwise
    returns None."""

    assert x.is_atomic()
    assert y.is_atomic()

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
