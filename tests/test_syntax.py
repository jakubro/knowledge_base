import pytest

from knowledge_base.grammar import parse


@pytest.mark.parametrize('p, q', [
    # bracketing
    ('a', '(a)'),
    ('a & b', 'a & (b)'),
    ('a & b & c', 'a & (b & c)'),
    ('a & b & c', '(a & b) & c'),
    ('a | (b & c)', 'a | (b & c)'),

    # order
    ('x & y & z', 'z & y & x'),
])
def test_equivalent_expressions(p, q):
    assert parse(p) == parse(q)


@pytest.mark.parametrize('p, q', [
    # bracketing
    ('a & b | c', 'a & (b | c)'),

    # order
    ('a => b', 'b => a'),
])
def test_not_equivalent_expressions(p, q):
    assert parse(p) != parse(q)
