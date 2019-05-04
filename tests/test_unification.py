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
        subs = unification.unify(p, q)
    except ValueError:
        subs = None

    print('mgu(p,q)=', subs)

    if subs is None:
        assert p != q  # not unifiable
    elif subs == {}:
        assert p == q  # already unified
    else:
        # Applying unifier to both expressions should yield the same result.
        p1 = p.apply(subs)
        q1 = q.apply(subs)
        print('mgu(p,q)(p)=', p1)
        print('mgu(p,q)(q)=', q1)
        assert p1 == q1

    assert subs == expected


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

    # Applying the composed substitution should yield the same result
    # as applying substitutions piecewise.
    if expr:
        expr = expr1 = parse(expr)
        for k in (r, s):
            expr1 = expr1.apply(k)
        print('r*s(expr)=', expr1)
        assert expr.apply(subs) == expr1
    else:
        assert not r and not s

    assert subs == expected


def _parse_subsitution(subs):
    return ({k: parse(v) for k, v in subs.items()}
            if subs is not None
            else None)
