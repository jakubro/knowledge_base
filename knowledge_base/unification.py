import syntax


def unify(p: syntax.Node, q: syntax.Node) -> syntax.T_Subsitution:
    """Unifies two sentences via Robinson's unification algorithm"""

    if p.is_constant() and q.is_constant():
        if p.value != q.value:
            raise ValueError('Not unifiable')
        else:
            return {}  # already unified

    elif p.is_variable():
        if p.occurs_in(q):
            raise ValueError('Not unifiable')
        else:
            return {p.value: q}

    elif q.is_variable():
        if q.occurs_in(p):
            raise ValueError('Not unifiable')
        else:
            return {q.value: p}

    else:
        if (p.type_ != q.type_
                or p.value != q.value
                or len(p.children) != len(q.children)):
            raise ValueError('Not unifiable')
        else:
            rv = {}
            for x, y in zip(p.children, q.children):
                x = x.apply(rv)
                y = y.apply(rv)
                rv = compose_substitutions(rv, unify(x, y))
            return rv


def compose_substitutions(r: syntax.T_Subsitution,
                          s: syntax.T_Subsitution) -> syntax.T_Subsitution:
    s1 = {k: v for k, v in s.items() if k not in r}
    r1 = {}
    for k, v in r.items():
        v = v.apply(s)
        if v.is_variable() and v.value == k:
            continue
        r1[k] = v
    return {**r1, **s1}
