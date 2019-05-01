import pytest

from knowledge_base.grammar import parse


@pytest.mark.parametrize('p, q', [
    # bracketing
    ('x', '(x)'),
    ('x & y', 'x & (y)'),
    ('x | y', 'x | (y)'),
    ('x => y', 'x => (y)'),
    ('x <=> y', 'x <=> (y)'),
    ('(x & y) & z', 'x & (y & z)'),
    ('(x | y) | z', 'x | (y | z)'),
    ('(x => y) => z', 'x => (y => z)'),
    ('(x <=> y) <=> z', 'x <=> (y <=> z)'),
    ('x & y | z', '(x & y) | z'),

    # order
    ('x & y & z', 'z & y & x'),
    ('x & !y & !z', '!z & !y & x'),
    ('x | y | z', 'z | y | x'),
    ('x | !y | !z', '!z | !y | x'),
    ('x <=> y <=> z', 'z <=> y <=> x'),
    ('x <=> !y <=> !z', '!z <=> !y <=> x'),
])
def test_equivalent_expressions(p, q):
    assert parse(p) == parse(q)


@pytest.mark.parametrize('p, q', [
    # bracketing
    ('x & y | z', 'x & (y | z)'),

    # order
    ('x => y', 'y => x'),
    ('H(x, y)', 'H(y, x)'),
    ('f(x, y)', 'f(y, x)'),
])
def test_not_equivalent_expressions(p, q):
    assert parse(p) != parse(q)
