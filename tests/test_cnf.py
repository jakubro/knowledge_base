import pytest

import knowledge_base.cnf as cnf
import knowledge_base.syntax as syntax
import knowledge_base.unification as unification
import knowledge_base.utils as utils
from knowledge_base.grammar import parse, parse_substitution


@pytest.mark.parametrize('f', [
    'x => y',
    'x <=> y',
    '(a | b) => (x => y)',

    '*x: x & *y: (x | y) & *z: (x | y | z)',
    '*x: x & *y: (x | y) & ?z: (x | y | z)',
    '*x: x & ?y: (x | y) & *z: (x | y | z)',
    '*x: x & ?y: (x | y) & ?z: (x | y | z)',
    '?x: x & *y: (x | y) & *z: (x | y | z)',
    '?x: x & *y: (x | y) & ?z: (x | y | z)',
    '?x: x & ?y: (x | y) & *z: (x | y | z)',
    '?x: x & ?y: (x | y) & ?z: (x | y | z)',

    # Already in CNF
    'x',
    'P',
    'H(x, y, P, Q)',
    'f(x, y, P, Q)',
    '!x',
    'x & y & !z',
    'x | y | !z',
    '(x | y | !z) & (!a | b)',
])
def test_convert_to_cnf(f):
    f = parse(f)

    rv, replaced = cnf.convert_to_cnf(f)
    print('rv =', rv)
    assert rv.is_cnf()


@pytest.mark.parametrize('f, expected', [
    ('x <=> y', '(x => y) & (y => x)'),
    ('x & y <=> a | b', '(x & y => a | b) & (a | b => x & y)'),
])
def test_eliminate_biconditional(f, expected):
    f = parse(f)
    expected = parse(expected, True)

    rv = _walk(f, cnf._eliminate_biconditional)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected', [
    ('x => y', '!x | y'),
    ('x & y => a | b', '!(x & y) | (a | b)'),
])
def test_eliminate_implication(f, expected):
    f = parse(f)
    expected = parse(expected, True)

    rv = _walk(f, cnf._eliminate_implication)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected, eval_kwargs', [
    ('!x', '!x', {}),
    ('!!x', 'x', {}),
    ('!(x & y)', '!x | !y', {}),
    ('!(x | y)', '!x & !y', {}),
    ('!(*x: x)', '?x: !x', {'x': [0, 1]}),
    ('!(?x: x)', '*x: !x', {'x': [0, 1]}),
])
def test_propagate_negation(f, expected, eval_kwargs):
    f = parse(f)
    expected = parse(expected, True)

    rv = _walk(f, cnf._propagate_negation)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k, **eval_kwargs) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected, expected_subst, eval_kwargs', [
    ('*x: x', '*_x: _x', {'x': '_x'}, {'_x': [0, 1]}),
    ('*x: P', '*_x: P', {'x': '_x'}, {'_x': [0, 1]}),
    ('*x: x & *x: x', '*_x: _x & *_x: _x', {'x': '_x'}, {'_x': [0, 1]}),
    ('x', 'x', {}, {}),  # free variable - no replacements here
])
def test_standardize_quantified_variables(f,
                                          expected,
                                          expected_subst,
                                          eval_kwargs):
    f = parse(f)
    expected = parse(expected, True)
    expected_subst = parse_substitution(expected_subst, True)

    rv = _walk(f, cnf._standardize_quantified_variables, expected_subst)
    assert rv == expected

    # Not testing truth tables, because variables might be ambiguous in the
    # original.


@pytest.mark.parametrize('f, expected, expected_subst, eval_kwargs', [
    ('x', '_x', {'x': '_x'}, {}),
    ('*x: y', '*x: _y', {'y': '_y'}, {'x': [0, 1]}),

    # Not testing that quantified variables (e.g. in `*x: x` don't get
    # rewritten, because that's not the case - we're expecting them to be
    # already rewritten in `_standardize_quantified_variables`.
])
def test_standardize_free_variables(f, expected, expected_subst, eval_kwargs):
    f = parse(f)
    expected = parse(expected, True)
    expected_subst = parse_substitution(expected_subst, True)

    rv = _walk(f, cnf._standardize_free_variables, expected_subst)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k, **eval_kwargs) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected, expected_subst', [
    ('*x: x', 'x', {}),
    ('*x: P', 'P', {}),

    ('?x: x', '_C1', {'x': '_C1'}),
    ('?x: P', 'P', {}),

    ('*x, *y: x & y', 'x & y', {}),
    ('*x, ?y: x & y', 'x & _H1(x)', {'y': '_H1(x)'}),
    ('?x, *y: x & y', '_C1 & y', {'x': '_C1'}),
    ('?x, ?y: x & y', '_C1 & _C2', {'x': '_C1', 'y': '_C2'}),

    ('*a: a & ?x: x & *b: b & ?y: y',
     'a & _H1(a) & b & _H2(a, b)',
     {'x': '_H1(a)', 'y': '_H2(a, b)', }),
])
def test_skolemize(f, expected, expected_subst):
    f = parse(f)
    expected = parse(expected, True)
    expected_subst = parse_substitution(expected_subst, True)

    rv = _walk(f, cnf._skolemize, expected_subst)
    assert rv == expected

    # Not testing truth tables, because we changed the structure.


@pytest.mark.parametrize('f, expected', [
    ('!x | (y & z)', '(!x | y) & (!x | z)'),
    ('!x | (y & (!z | (a & b)))', '(!x | y) & (!x | !z | a) & (!x | !z | b)'),
])
def test_distribute_conjunction(f, expected):
    f = parse(f)
    expected = parse(expected, True)

    rv = _walk(f, cnf._distribute_conjunction)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k) for k in (f, rv))
    assert f_tt == rv_tt


# Helpers
# -----------------------------------------------------------------------------

def _walk(f, func, subst=None):
    rv = f.denormalize()
    state = syntax.WalkState.make()
    # noinspection PyTypeChecker
    rv = syntax.walk(rv, func, state)
    rv = rv.normalize()
    print('rv (original) =', rv)
    replaced = state.context.get('replaced', {})
    rv = _normalize(rv, replaced, subst)
    return rv


def _normalize(rv, replaced, subst):
    # Convert rv into a normalized form.
    #
    # Example:
    #
    # 1. original node `x & *x: x` was converted into `x & *vA: vA` where
    #    `A` is some arbitrary ID.
    # 2. state.context['replaced'] is {'vA': x}
    # 3. we want to check whether the quantified variable `x` was replaced,
    #    therefore we set `subst` to {'x': _x}
    # 4. here we convert `rv` into a normalized form, i.e.
    #    `x & *_x: _x` which we can simply compare with the expected
    #    value
    #
    # Unfortunately this approach would work only with well-behaved
    # expressions, e.g. `*x: (x & *x: x)` results in `*vA: (vA & *vB: vB)`
    # and state.context['replaced'] is {'vA': x, 'vB': x}.

    subst = subst or {}
    replaced = {
        k: v for k, v in
        unification.compose_substitutions(replaced, subst).items()
        if k in replaced
    }
    rv = rv.replace(replaced)
    print('rv (normalized) =', rv)

    return rv
