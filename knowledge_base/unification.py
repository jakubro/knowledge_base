from knowledge_base import common, syntax


class NotUnifiable(common.KnowledgeBaseError):
    pass


def unify(p: syntax.Node, q: syntax.Node) -> syntax.T_Substitution:
    """Unifies two expressions via Robinson's unification algorithm."""

    if not p.is_term() and not p.is_atom():
        raise TypeError(f"'{p}' is not a term and neither an atom")

    if not q.is_term() and not q.is_atom():
        raise TypeError(f"'{q}' is not a term and neither an atom")

    if p.is_constant() and q.is_constant():
        if p.value != q.value:
            raise NotUnifiable()
        else:
            return {}  # already unified

    elif p.is_variable():
        if p.occurs_in(q):
            raise NotUnifiable()
        else:
            return {p.value: q}

    elif q.is_variable():
        if q.occurs_in(p):
            raise NotUnifiable()
        else:
            return {q.value: p}

    else:
        if (p.type_ != q.type_
                or p.value != q.value
                or len(p.children) != len(q.children)):
            raise NotUnifiable()
        else:
            rv = {}
            for x, y in zip(p.children, q.children):
                x = x.apply(rv)
                y = y.apply(rv)
                rv = compose(rv, unify(x, y))
            return rv


def compose(*args: syntax.T_Substitution) -> syntax.T_Substitution:
    rv = {}
    for k in args:
        rv = _compose(rv, k)
    return rv


def _compose(r: syntax.T_Substitution,
             s: syntax.T_Substitution) -> syntax.T_Substitution:
    """Composes two substitutions."""

    r1 = {}
    for v, t in r.items():
        assert t.is_term()
        t = t.apply(s)
        r1[v] = t

    s1 = {}
    for v, t in s.items():
        assert t.is_term()
        if v in r:
            continue
        s1[v] = t

    rv = {}
    for v, t in {**r1, **s1}.items():
        if t.is_variable() and t.value == v:
            continue
        rv[v] = t

    return rv
