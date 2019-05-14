import pytest

from knowledge_base import unification
from knowledge_base.grammar import parse, parse_substitution


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
    p = parse(p, _allow_partial_expression=True)
    q = parse(q, _allow_partial_expression=True)
    expected = parse_substitution(expected)

    print('p=', p)
    print('q=', q)
    print('expected mgu(p,q)=', expected)

    try:
        subst = unification.unify(p, q)
    except unification.NotUnifiable:
        subst = None

    print('mgu(p,q)=', subst)

    if subst is None:
        assert p != q  # not unifiable
    elif subst == {}:
        assert p == q  # already unified
    else:
        # Applying unifier to both expressions should yield the same result.
        p1 = p.apply(subst)
        q1 = q.apply(subst)
        print('mgu(p,q)(p)=', p1)
        print('mgu(p,q)(q)=', q1)
        assert p1 == q1

    assert subst == expected


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
])
def test_compose(r, s, expected):
    expr = ' & '.join({*r.keys(), *r.values(), *s.keys(), *s.values()})
    r = parse_substitution(r)
    s = parse_substitution(s)
    expected = parse_substitution(expected)

    print('r=', r)
    print('s=', s)
    print('expected r*s=', expected)
    print('expr=', expr)

    subst = unification.compose(r, s)
    print('r*s=', subst)

    # Applying the composed substitution should yield the same result
    # as applying substitutions piecewise.
    if expr:
        expr = expr1 = parse(expr, _allow_partial_expression=True)
        for k in (r, s):
            expr1 = expr1.apply(k)
        print('r*s(expr)=', expr1)
        assert expr.apply(subst) == expr1
    else:
        assert not r and not s

    assert subst == expected
