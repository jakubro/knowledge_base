import pytest

from knowledge_base import syntax
from knowledge_base.grammar import parse, parse_substitution


@pytest.mark.parametrize('p, q, expected', [
    # bracketing (equivalent)
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

    # bracketing (not equivalent)
    ('x & y | z', 'x & (y | z)', False),

    # ordering (equivalent)
    ('x & y & z', 'z & y & x', True),
    ('x & !y & !z', '!z & !y & x', True),
    ('x | y | z', 'z | y | x', True),
    ('x | !y | !z', '!z | !y | x', True),
    ('x <=> y <=> z', 'z <=> y <=> x', True),
    ('x <=> !y <=> !z', '!z <=> !y <=> x', True),

    # ordering (not equivalent)
    ('x => y', 'y => x', False),
    ('H(x, y)', 'H(y, x)', False),
    ('f(x, y)', 'f(y, x)', False),
])
def test_equivalent_expressions(p, q, expected):
    p = parse(p, _allow_partial_expression=True)
    q = parse(q, _allow_partial_expression=True)
    assert (p == q) == expected


@pytest.mark.parametrize('p, q, expected', [
    ('x', 'H(x)', True),
    ('x', 'f(x)', True),
    ('x', 'f(y, J(x))', True),
    ('x', 'H(y, J(x))', True),

    ('x', 'x', False),
    ('x', 'H(y)', False),
    ('x', 'f(y)', False),

    # must be variable

    ('C', 'H(C)', None),
    ('C', 'f(C)', None),
    ('H(c)', 'f(H(c))', None),
])
def test_occurs_in(p, q, expected):
    p = parse(p, _allow_partial_expression=True)
    q = parse(q, _allow_partial_expression=True)
    try:
        assert p.occurs_in(q) == expected
    except TypeError:
        assert expected is None


@pytest.mark.parametrize('p, q, expected', [
    ('f(x)', {'x': 'a'}, 'f(a)'),
    ('f(x)', {'x': 'a', 'a': 'x'}, 'f(a)'),
    ('f(x, a)', {'x': 'a', 'a': 'x'}, 'f(a, x)'),

    ('f(x, y, H(P, z))', {'x': 'a', 'y': 'b', 'z': 'c'}, 'f(a, b, H(P, c))'),
])
def test_apply_substitution(p, q, expected):
    p = parse(p, _allow_partial_expression=True)
    q = parse_substitution(q)
    expected = parse(expected)
    assert p.apply(q) == expected


@pytest.mark.parametrize('p', [
    # Symbols
    'P',
    'x',
    'H(x, y, P, Q)',
    'f(x, y, P, Q)',
    'H(x, P, J(y, Q))',

    # Boolean operators
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

    # Equality
    'a = b',
    'a = b = c = d',
    'a != b',
    'a != b != c != d',

    # Quantifiers
    '*x: x',
    '?x: x',
    '*x, ?y, ?z: x',
    '*x: ?y: ?z: x',
])
def test_serialization(p):
    f = parse(p, _allow_partial_expression=True)

    # Methods 'loads' and 'dumps' are inversed.
    assert f == syntax.Node.loads(f.dumps())

    # Methods 'parse' and '__str__' are inversed.
    assert f == parse(str(f), _allow_partial_expression=True)
