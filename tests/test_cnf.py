import pytest

import knowledge_base.cnf as cnf
from knowledge_base.grammar import parse


@pytest.mark.parametrize('f, expected', [
    ('a', 'a'),
    ('a & b', 'a & b'),
    ('a | b & c', '(a | b) & (a | c)'),
    ('a => b', '!a | b'),
    ('a <=> b', '(!a | b) & (!b | a)'),
])
def test_convert_to_cnf(f, expected):
    f = parse(f)
    expected = parse(expected)

    rv = cnf.convert_to_cnf(f)
    print(rv)
    assert rv == expected
