import pytest

from knowledge_base import cnf, syntax, unification, utils
from knowledge_base.grammar import parse, parse_substitution


@pytest.mark.parametrize('f', [
    'f(x) => f(y)',
    'f(x) <=> f(y)',
    '(f(a) | f(b)) => (f(x) => f(y))',

    '*x: f(x) & *y: (f(x) | f(y)) & *z: (f(x) | f(y) | f(z))',
    '*x: f(x) & *y: (f(x) | f(y)) & ?z: (f(x) | f(y) | f(z))',
    '*x: f(x) & ?y: (f(x) | f(y)) & *z: (f(x) | f(y) | f(z))',
    '*x: f(x) & ?y: (f(x) | f(y)) & ?z: (f(x) | f(y) | f(z))',
    '?x: f(x) & *y: (f(x) | f(y)) & *z: (f(x) | f(y) | f(z))',
    '?x: f(x) & *y: (f(x) | f(y)) & ?z: (f(x) | f(y) | f(z))',
    '?x: f(x) & ?y: (f(x) | f(y)) & *z: (f(x) | f(y) | f(z))',
    '?x: f(x) & ?y: (f(x) | f(y)) & ?z: (f(x) | f(y) | f(z))',

    # Already in CNF
    'f(x)',
    'f(x)',
    'f(x, y, P, Q)',
    'f(H(x, y, P, Q))',
    '!f(x)',
    'f(x) & f(y) & !f(z)',
    'f(x) | f(y) | !f(z)',
    '(f(x) | f(y) | !f(z)) & (!f(a) | f(b))',
])
def test_convert_to_cnf(f):
    f = parse(f)

    rv, replaced = cnf.convert_to_cnf(f)
    print('rv =', rv)
    assert rv.is_cnf()

    # Not testing truth tables, because variables might be ambiguous in the
    # original.


@pytest.mark.parametrize('f, expected', [
    ('f(x) <=> f(y)', '(f(x) => f(y)) & (f(y) => f(x))'),
    ('f(x) & f(y) <=> f(a) | f(b)', ('(f(x) & f(y) => f(a) | f(b)) & '
                                     '(f(a) | f(b) => f(x) & f(y))')),
])
def test_eliminate_biconditional(f, expected):
    f = parse(f)
    expected = parse(expected, True)

    rv = _walk(f, cnf._eliminate_biconditional)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected', [
    ('f(x) => f(y)', '!f(x) | f(y)'),
    ('f(x) & f(y) => f(a) | f(b)', '!(f(x) & f(y)) | (f(a) | f(b))'),
])
def test_eliminate_implication(f, expected):
    f = parse(f)
    expected = parse(expected, True)

    rv = _walk(f, cnf._eliminate_implication)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected', [
    ('!f(x)', '!f(x)'),
    ('!!f(x)', 'f(x)'),
    ('!(f(x) & f(y))', '!f(x) | !f(y)'),
    ('!(f(x) | f(y))', '!f(x) & !f(y)'),
    ('!(*x: f(x))', '?x: !f(x)'),
    ('!(?x: f(x))', '*x: !f(x)'),
])
def test_propagate_negation(f, expected):
    f = parse(f)
    expected = parse(expected, True)

    rv = _walk(f, cnf._propagate_negation)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected, expected_subst', [
    ('*x: f(x)', '*_x: f(_x)', {'x': '_x'}),
    ('*x: f(P)', '*_x: f(P)', {'x': '_x'}),
    ('*x: f(x) & *x: f(x)', '*_x: f(_x) & *_x: f(_x)', {'x': '_x'}),
    ('f(x)', 'f(x)', {}),  # free variable - no replacements here
])
def test_standardize_quantified_variables(f, expected, expected_subst):
    f = parse(f)
    expected = parse(expected, True)
    expected_subst = parse_substitution(expected_subst, True)

    rv = _walk(f, cnf._standardize_quantified_variables, expected_subst)
    assert rv == expected

    # Not testing truth tables, because variables might be ambiguous in the
    # original.


@pytest.mark.parametrize('f, expected, expected_subst', [
    ('f(x)', 'f(_x)', {'x': '_x'}),
    ('*x: f(y)', '*x: f(_y)', {'y': '_y'}),

    # Not testing that quantified variables (e.g. in `*x: x` don't get
    # rewritten, because that's not the case - we're expecting them to be
    # already rewritten in `_standardize_quantified_variables`.
])
def test_standardize_free_variables(f, expected, expected_subst):
    f = parse(f)
    expected = parse(expected, True)
    expected_subst = parse_substitution(expected_subst, True)

    rv = _walk(f, cnf._standardize_free_variables, expected_subst)
    assert rv == expected

    f_tt, rv_tt = (utils.truth_table(k) for k in (f, rv))
    assert f_tt == rv_tt


@pytest.mark.parametrize('f, expected, expected_subst', [
    ('*x: f(x)', 'f(x)', {}),
    ('*x: f(P)', 'f(P)', {}),

    ('?x: f(x)', 'f(_C1)', {'x': '_C1'}),
    ('?x: f(P)', 'f(P)', {}),

    ('*x, *y: f(x) & f(y)', 'f(x) & f(y)', {}),
    ('*x, ?y: f(x) & f(y)', 'f(x) & f(_H1(x))', {'y': '_H1(x)'}),
    ('?x, *y: f(x) & f(y)', 'f(_C1) & f(y)', {'x': '_C1'}),
    ('?x, ?y: f(x) & f(y)', 'f(_C1) & f(_C2)', {'x': '_C1', 'y': '_C2'}),

    ('*a: f(a) & ?x: f(x) & *b: f(b) & ?y: f(y)',
     'f(a) & f(_H1(a)) & f(b) & f(_H2(a, b))',
     {'x': '_H1(a)', 'y': '_H2(a, b)'}),
])
def test_skolemize(f, expected, expected_subst):
    f = parse(f)
    expected = parse(expected, True)
    expected_subst = parse_substitution(expected_subst, True)

    rv = _walk(f, cnf._skolemize, expected_subst)
    assert rv == expected

    # Not testing truth tables, because we changed the structure.


@pytest.mark.parametrize('f, expected', [
    ('!f(x) | (f(y) & f(z))', '(!f(x) | f(y)) & (!f(x) | f(z))'),
    ('!f(x) | (f(y) & (!f(z) | (f(a) & f(b))))',
     '(!f(x) | f(y)) & (!f(x) | !f(z) | f(a)) & (!f(x) | !f(z) | f(b))'),
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
        unification.compose(replaced, subst).items()
        if k in replaced
    }
    rv = rv.replace(replaced)
    print('rv (normalized) =', rv)

    return rv
