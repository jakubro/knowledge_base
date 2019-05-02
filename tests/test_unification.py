import pytest

import knowledge_base.unification as unification
from knowledge_base.grammar import parse


@pytest.mark.parametrize('p, q, expected', [
    ('P', 'P', {}),
    ('P', 'Q', None),

    ('x', 'x', {'x': 'x'}),
    ('x', 'y', {'x': 'y'}),
    ('x', 'P', {'x': 'P'}),

    ('P', 'H(P)', None),
    ('P', 'H(Q)', None),
    ('P', 'H(x)', None),

    ('x', 'H(x)', None),
    ('H(x)', 'x', None),
    ('x', 'H(y)', {'x': 'H(y)'}),
    ('x', 'H(P)', {'x': 'H(P)'}),

    ('x', 'G(H(x))', None),
    ('H(x, y)', 'H(a, b, c)', None),

    ('G(x, J(x), H(A))', 'G(A, J(A), y)', {'x': 'A', 'y': 'H(A)'}),
    ('H(x)', 'H(a)', {'x': 'a'}),
])
def test_unify(p, q, expected):
    p = parse(p)
    q = parse(q)
    expected = _parse_subsitution(expected)
    print('p=', p)
    print('q=', q)
    print('expected mgu(p,q)=', expected)

    try:
        rv = unification.unify(p, q)
    except ValueError:
        rv = None
    print('mgu(p,q)=', rv)

    # Applying unifier to both expressions should yield the same result.
    if rv is not None:
        p1 = p.apply(rv)
        q1 = q.apply(rv)
        print('mgu(p,q)(p)=', p1)
        print('mgu(p,q)(q)=', q1)
        assert p1 == q1
    else:
        assert p != q

    assert rv == expected


@pytest.mark.parametrize('r, s, expected', [
    ({}, {}, {}),
    ({}, {'x': 'x'}, {}),
    ({}, {'x': 'y'}, {'x': 'y'}),
    ({}, {'x': 'P'}, {'x': 'P'}),
    ({'x': 'x'}, {}, {}),
    ({'x': 'P'}, {}, {'x': 'P'}),

    ({'x': 'F(y)', 'y': 'z'},
     {'x': 'a', 'y': 'b', 'z': 'y'},
     {'x': 'F(b)', 'z': 'y'}),

    ({'x': 'F(y)', 'y': 'z'},
     {'x': 'a', 'y': 'b', 'z': 'y'},
     {'x': 'F(b)', 'z': 'y'}),
])
def test_compose_substitutions(r, s, expected):
    expr = ' & '.join({*r.keys(), *r.values(), *s.keys(), *s.values()})
    r = _parse_subsitution(r)
    s = _parse_subsitution(s)
    expected = _parse_subsitution(expected)
    print('r=', r)
    print('s=', s)
    print('expected r*s=', expected)
    print('expr=', expr)

    subs = unification.compose_substitutions(r, s)
    print('r*s=', subs)
    assert subs == expected

    # Applying substitutions piecewise should yield the same result
    # as applying composed substitution.
    if expr:
        expr = parse(expr)
        rv = expr
        for k in (r, s):
            rv = rv.apply(k)
        print('r*s(expr)=', rv)
        assert expr.apply(subs) == rv


def _parse_subsitution(subs):
    return ({k: parse(v) for k, v in subs.items()}
            if subs is not None
            else None)
