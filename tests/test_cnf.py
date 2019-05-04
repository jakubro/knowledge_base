import pytest

import knowledge_base.cnf as cnf
import knowledge_base.syntax as syntax
from knowledge_base.grammar import parse


@pytest.mark.parametrize('f, expected', [
    ('(a | b) => (x => y)', '(!a | !x | y) & (!b | !x | y)'),

    ('*x: x & *y: (x | y) & *z: (x | y | z)',
     '(_v1 | _v2) & (_v1 | _v2 | _v3) & _v1'),

    ('*x: x & *y: (x | y) & ?z: (x | y | z)',
     '(_H1(_v1, _v2) | _v1 | _v2) & (_v1 | _v2) & _v1'),

    ('*x: x & ?y: (x | y) & *z: (x | y | z)',
     '(_H1(_v1) | _v1) & (_H1(_v1) | _v1 | _v3) & _v1'),

    ('*x: x & ?y: (x | y) & ?z: (x | y | z)',
     '(_H1(_v1) | _H2(_v1) | _v1) & (_H1(_v1) | _v1) & _v1'),

    ('?x: x & *y: (x | y) & *z: (x | y | z)',
     '_C1 & (_C1 | _v2) & (_C1 | _v2 | _v3)'),

    ('?x: x & *y: (x | y) & ?z: (x | y | z)',
     '_C1 & (_C1 | _H1(_v2) | _v2) & (_C1 | _v2)'),

    ('?x: x & ?y: (x | y) & *z: (x | y | z)',
     '_C1 & (_C1 | _C2) & (_C1 | _C2 | _v3)'),

    ('?x: x & ?y: (x | y) & ?z: (x | y | z)',
     '_C1 & (_C1 | _C2) & (_C1 | _C2 | _C3)'),

    # Already in CNF
    ('x', 'x'),
    ('P', 'P'),
    ('H(x, y, P, Q)', 'H(x, y, P, Q)'),
    ('f(x, y, P, Q)', 'f(x, y, P, Q)'),
    ('!x', '!x'),
    ('x & y & !z', 'x & y & !z'),
    ('x | y | !z', 'x | y | !z'),
    ('(x | y | !z) & (!a | b)', '(x | y | !z) & (!a | b)'),
])
def test_convert_to_cnf(f, expected):
    f = parse(f)

    rv = cnf.convert_to_cnf(f)
    print(rv)

    expected = parse(expected, _allow_private_symbols=True)
    assert rv == expected


@pytest.mark.parametrize('f, expected', [
    ('x <=> y', '(x => y) & (y => x)'),
    ('x & y <=> a | b', '(x & y => a | b) & (a | b => x & y)'),
])
def test_eliminate_biconditional(f, expected):
    f = parse(f)

    rv = f.denormalize()
    state = syntax.WalkState.make()
    # noinspection PyTypeChecker
    rv = syntax.walk(rv, cnf._eliminate_biconditional, state)
    rv = rv.normalize()
    print(rv)

    expected = parse(expected, _allow_private_symbols=True)
    assert rv == expected


@pytest.mark.parametrize('f, expected', [
    ('x => y', '!x | y'),
    ('x & y => a | b', '!(x & y) | (a | b)'),
])
def test_eliminate_implication(f, expected):
    f = parse(f)

    rv = f.denormalize()
    state = syntax.WalkState.make()
    # noinspection PyTypeChecker
    rv = syntax.walk(rv, cnf._eliminate_implication, state)
    rv = rv.normalize()
    print(rv)

    expected = parse(expected, _allow_private_symbols=True)
    assert rv == expected


@pytest.mark.parametrize('f, expected', [
    ('!x', '!x'),
    ('!!x', 'x'),
    ('!!!x', '!x'),
    ('!!!!x', 'x'),

    ('!(x & y)', '!x | !y'),
    ('!(x | y)', '!x & !y'),

    ('!((x | y | z) & !(!a & !b & !c))', '(!x & !y & !z) | (!a & !b & !c)'),

    ('!(*x: T(x))', '?x: !T(x)'),
    ('!(?x: T(x))', '*x: !T(x)'),

    ('!(*x, ?y, *z: T(x))', '?x, *y, ?z: !T(x)'),
])
def test_propagate_negation(f, expected):
    f = parse(f)

    rv = f.denormalize()
    state = syntax.WalkState.make()
    # noinspection PyTypeChecker
    rv = syntax.walk(rv, cnf._propagate_negation, state)
    rv = rv.normalize()
    print(rv)

    expected = parse(expected, _allow_private_symbols=True)
    assert rv == expected


@pytest.mark.parametrize('f, expected', [
    ('*x: x', '*_v1: _v1'),
    ('*x: P', '*_v1: P'),
    ('*x: f(x, P)', '*_v1: f(_v1, P)'),
    ('*x: H(x, P)', '*_v1: H(_v1, P)'),

    ('*x: x & *x: x', '*_v1: ((*_v2: _v2) & _v1)'),
    ('*x: x & ?y: x & y & *z: x & y & z',
     '*_v1: ((?_v2: ((*_v3: (_v1 & _v2 & _v3)) & _v1 & _v2)) & _v1)'),
])
def test_standardize_variables(f, expected):
    f = parse(f)

    rv = f.denormalize()
    state = syntax.WalkState.make()
    # noinspection PyTypeChecker
    rv = syntax.walk(rv, cnf._standardize_variables, state)
    rv = rv.normalize()
    print(rv)

    expected = parse(expected, _allow_private_symbols=True)
    assert rv == expected


@pytest.mark.parametrize('f, expected', [
    ('*x: x', 'x'),
    ('*x: P', 'P'),
    ('*x: f(x, P)', 'f(x, P)'),
    ('*x: H(x, P)', 'H(x, P)'),
    ('?x: x', '_C1'),
    ('?x: P', 'P'),
    ('?x: f(x, P)', 'f(_C1, P)'),
    ('?x: H(x, P)', 'H(_C1, P)'),

    ('*x, *y: x & y', 'x & y'),
    ('*x, ?y: x & y', '_H1(x) & x'),
    ('?x, *y: x & y', '_C1 & y'),
    ('?x, ?y: x & y', '_C1 & _C2'),
    ('*a: a & ?x: x & *b: b & ?y: y', '_H1(a) & _H2(a, b) & a & b'),
])
def test_skolemize(f, expected):
    f = parse(f)

    rv = f.denormalize()
    state = syntax.WalkState.make()
    # noinspection PyTypeChecker
    rv = syntax.walk(rv, cnf._skolemize, state)
    rv = rv.normalize()
    print(rv)

    expected = parse(expected, _allow_private_symbols=True)
    assert rv == expected


@pytest.mark.parametrize('f, expected', [
    ('!x | (y & z)', '(!x | y) & (!x | z)'),
    ('!x | (y & (!z | (a & b)))', '(!x | y) & (!x | !z | a) & (!x | !z | b)'),
])
def test_distribute_conjunction(f, expected):
    f = parse(f)

    rv = f.denormalize()
    state = syntax.WalkState.make()
    # noinspection PyTypeChecker
    rv = syntax.walk(rv, cnf._distribute_conjunction, state)
    rv = rv.normalize()
    print(rv)

    expected = parse(expected, _allow_private_symbols=True)
    assert rv == expected
