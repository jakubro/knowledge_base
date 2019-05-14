import itertools
import logging
from typing import List, Optional, Set, Tuple

from knowledge_base import common, syntax, unification

T_Substitution = syntax.T_Substitution
Node = syntax.Node

_log = logging.getLogger()


class _NotInferable(common.KnowledgeBaseError):
    pass


def infer(premises: List[Node], conclusion: Node) -> Optional[T_Substitution]:
    # break down the expressions into disjunctions

    _log.debug(" CNF ".center(80, "="))

    clauses = []
    input_subst = {}  # to map intermediary results into original input

    for k in (*premises, conclusion.negate()):
        if not k.is_formula():
            raise ValueError(f"'{k}' is not a well-formed formula")

        f, subst = k.to_cnf()
        c = f.to_clause_form()

        _log.debug(f"{k} -> {set(_str_clause(j, subst) for j in c)}")

        clauses.extend(c)
        input_subst = unification.compose(input_subst, subst)

    clauses = frozenset(clauses)
    conclusion_subst = subst  # to map query result into original input

    if not premises:
        return {}

    # derive new clauses
    _log.debug(" Inference ".center(80, "="))
    answer = {}
    seen = []
    while True:
        restart = False

        for i, func in ((2, _resolve),
                        (1, _resolve_reflexivity),
                        (2, _paramodulate)):
            if not restart:
                for args in itertools.combinations(clauses, i):
                    if args in seen:
                        continue
                    seen.append(args)

                    try:
                        subst, inferred = func(*args)
                    except _NotInferable:
                        continue
                    else:
                        inferred = frozenset(inferred)

                    input_subst = unification.compose(input_subst, subst)
                    answer = unification.compose(answer, subst)

                    if _log.level <= logging.DEBUG:
                        _log.debug(" + ".join(_str_clause(a, input_subst)
                                              for a in args) +
                                   " -> " + (_str_clause(inferred, input_subst)
                                             if inferred
                                             else '■') +
                                   f" ({func.__name__})")

                    if not inferred:
                        return _apply(conclusion_subst, answer)

                    if not inferred.issubset(clauses):
                        # clauses = [frozenset(k.apply(subst) for k in j)
                        #            for j in clauses]
                        clauses = frozenset([*clauses, inferred])
                        restart = True
                        break

        if not restart:
            return None


def _apply(p: T_Substitution, q: T_Substitution) -> T_Substitution:
    rv = {}
    for k, v in p.items():
        k2 = p[k]
        assert k2.is_variable()
        k2 = k2.value
        v2 = q[k]
        rv[k2] = v2
    return rv


def _str_clause(a, subst):
    return str(set(j.replace(subst) for j in a))


# Binary Resolution
# -----------------------------------------------------------------------------

def _resolve(p: Set[Node], q: Set[Node]) -> Tuple[T_Substitution, List[Node]]:
    # assume: {A | C} + {!B | D}
    # infer:  {C | D} * mgu(A, B)
    #
    # notes:
    #   {C | D} is variable 'resolvents'
    #   mgu(A, B) is variable 'subst'

    for x, y in itertools.product(p, q):
        # resolve if x and y are complementary (one of them is positive,
        # and the another is its negation)

        try:
            subst = _unify_complementary(x, y)
        except unification.NotUnifiable:
            continue

        rv = [*p, *q]
        rv.remove(x)
        rv.remove(y)
        rv = [k.apply(subst) for k in rv]

        return subst, rv

    raise _NotInferable()


def _unify_complementary(x: Node, y: Node) -> T_Substitution:
    x_neg = x.is_negation()
    y_neg = y.is_negation()

    if x_neg == y_neg:
        raise unification.NotUnifiable()
    elif x_neg:
        x = x.children[0]
    else:
        assert y_neg
        y = y.children[0]

    # todo
    if x.is_equality() or y.is_equality():
        raise unification.NotUnifiable()

    return x.unify(y)


# Binary Paramodulation
# -----------------------------------------------------------------------------

def _paramodulate(p: Set[Node], q: Set[Node]) -> Tuple[T_Substitution,
                                                       List[Node]]:
    # assume: {s = t | C} + {L[r] | D}
    # infer:  {L[t] | C | D} * mgu(s, r)
    #
    # notes:
    #   L[x] is an atom containing a term x
    #   premises have no variables in common

    for c1, c2 in ((p, q), (q, p)):
        rv = [*c1, *c2]

        # find equality
        for x1 in c1:
            if x1.is_equality():
                rv.remove(x1)
                s, t = x1.children
                break
        else:
            continue

        # find term that unifies with one of the equality operands
        for x2 in c2:
            for s, t in ((s, t), (t, s)):
                try:
                    subst, r = _unify_recursively(s, x2)
                except unification.NotUnifiable:
                    pass
                else:
                    rv.remove(x2)
                    rv.append(x2.replace2(r, t))
                    rv = [k.apply(subst) for k in rv]
                    return subst, rv

    raise _NotInferable()


def _unify_recursively(s: Node, in_: Node) -> Tuple[T_Substitution, Node]:
    # assert s.is_term()
    # assert in_.is_literal() or in_.is_term()

    if in_.is_negation():
        in_ = in_.children[0]

    for r in in_.children:
        try:
            return _unify_recursively(s, r)
        except unification.NotUnifiable:
            pass

        try:
            return s.unify(r), r
        except unification.NotUnifiable:
            pass

    raise unification.NotUnifiable()


# Reflexivity Resolution
# -----------------------------------------------------------------------------

def _resolve_reflexivity(clauses: Set[Node]) -> Tuple[T_Substitution,
                                                      List[Node]]:
    # assume: {s != t | D}
    # infer:  {D} * mgu(s, t)

    for c in clauses:
        if not c.is_negation():
            continue
        child = c.children[0]
        if not child.is_equality():
            continue
        s, t = child.children
        # assert s.is_term()
        # assert t.is_term()
        try:
            subst = s.unify(t)
        except unification.NotUnifiable:
            pass
        else:
            rv = [*clauses]
            rv.remove(c)
            rv = [k.apply(subst) for k in rv]
            return subst, rv

    raise _NotInferable()
