import pytest

import knowledge_base.syntax as syntax
from knowledge_base.grammar import parse


@pytest.mark.parametrize('p, q, expected', [
    # bracketing

    ('x', '(x)', True),
    ('x & y', 'x & (y)', True),
    ('x | y', 'x | (y)', True),
    ('x => y', 'x => (y)', True),
    ('x <=> y', 'x <=> (y)', True),
    ('(x & y) & z', 'x & (y & z)', True),
    ('(x | y) | z', 'x | (y | z)', True),
    ('(x => y) => z', 'x => (y => z)', True),
    ('(x <=> y) <=> z', 'x <=> (y <=> z)', True),
    ('x & y | z', '(x & y) | z', True),

    ('x & y | z', 'x & (y | z)', False),

    # order

    ('x & y & z', 'z & y & x', True),
    ('x & !y & !z', '!z & !y & x', True),
    ('x | y | z', 'z | y | x', True),
    ('x | !y | !z', '!z | !y | x', True),
    ('x <=> y <=> z', 'z <=> y <=> x', True),
    ('x <=> !y <=> !z', '!z <=> !y <=> x', True),

    ('x => y', 'y => x', False),
    ('H(x, y)', 'H(y, x)', False),
    ('f(x, y)', 'f(y, x)', False),
])
def test_equivalent_expressions(p, q, expected):
    rv = parse(p) == parse(q)
    assert rv == expected


@pytest.mark.parametrize('p, q, expected', [
    ('x', 'x', False),
    ('x', 'H(y)', False),
    ('x', 'f(y)', False),

    ('x', 'H(x)', True),
    ('x', 'f(x)', True),
    ('x', 'f(y, J(x))', True),
    ('x', 'H(y, J(x))', True),

    ('C', 'H(C)', None),
    ('C', 'f(C)', None),
])
def test_occurs_in(p, q, expected):
    p = parse(p)
    q = parse(q)
    try:
        assert p.occurs_in(q) == expected
    except TypeError as e:
        assert expected is None


@pytest.mark.parametrize('p, q, expected', [
    ('f(x)', {'x': 'a'}, 'f(a)'),
    ('f(x)', {'x': 'a', 'a': 'x'}, 'f(a)'),
    ('f(x, a)', {'x': 'a', 'a': 'x'}, 'f(a, x)'),

    ('f(x, y, H(P, z))',
     {'x': 'a', 'y': 'b', 'z': 'c'},
     'f(a, b, H(P, c))'),
])
def test_apply_substitution(p, q, expected):
    p = parse(p)
    q = _parse_subsitution(q)
    expected = parse(expected)
    assert p.apply(q) == expected


def _parse_subsitution(subs):
    return ({k: parse(v) for k, v in subs.items()}
            if subs is not None
            else None)


@pytest.mark.parametrize('p', [
    'P',
    'x',
    'H(x, y, P, Q)',
    'f(x, y, P, Q)',
    'H(x, P, J(y, Q))',
    '!x',
    '!!x',
    '!!!x',
    '!(x & !P)',
    'a & b',
    'a & b & c & d',
    'a | b',
    'a | b | c | d',
    'a => b',
    'a => b => c => d',
    'a <=> b',
    'a <=> b <=> c <=> d',
    'a = b',
    'a = b = c = d',
    'a != b',
    'a != b != c != d',
    '*x: x',
    '?x: x',
    '*x, ?y, ?z: x',
    '*x: ?y: ?z: x',
])
def test_serialization(p):
    f = parse(p)
    assert f == syntax.Node.loads(f.dumps())
    assert f == parse(str(f))
