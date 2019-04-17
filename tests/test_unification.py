import pytest

import knowledge_base.unification as unification
from knowledge_base.grammar import parse


@pytest.mark.parametrize('p, q, expected', [
    ('P', 'P', {}),
    ('P', 'Q', None),

    ('x', 'x', {'x': 'x'}),
    ('x', 'y', {'x': 'y'}),
])
def test_unify(p, q, expected):
    p = parse(p)
    q = parse(q)
    expected = _parse_subsitution(expected)

    try:
        rv = unification.unify(p, q)
    except ValueError:
        rv = None

    print(rv)
    assert rv == expected


@pytest.mark.parametrize('r, s', [
    ({'X': 'f(X)'}, {'X': 'Y'}),
])
def test_compose_substitutions(r, s):
    r = _parse_subsitution(r)
    s = _parse_subsitution(s)

    print(unification.compose_substitutions(r, s))


def _parse_subsitution(subs):
    return ({k: parse(v) for k, v in subs.items()}
            if subs is not None
            else None)
