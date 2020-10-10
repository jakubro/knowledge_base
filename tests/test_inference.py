import pytest

from knowledge_base import inference, utils
from knowledge_base.grammar import parse, parse_substitution

caesar_model = [
    'man(Marcus)',
    'roman(Marcus)',
    '*x: man(x) => person(x)',
    'ruler(Caesar)',
    '*x: roman(x) => loyal(x, Caesar) | hate(x, Caesar)',
    '*x, ?y: loyal(x, y)',
    '*x, *y: person(x) & ruler(y) & tryAssassin(x, y) => !loyal(x, y)',
    'tryAssassin(Marcus, Caesar)',
]


@pytest.mark.parametrize('premises, conclusion, expected', [
    (['f(P)'], 'f(P)', True),
    (['f(P)'], '!f(P)', False),
    (['f(P)'], 'f(Q)', False),
    (['f(P)'], '!f(Q)', False),
    (['f(P)'], 'f(P) & f(Q)', False),
    (['f(P)'], 'f(P) | f(Q)', True),
    (['f(P)'], 'f(P) => f(Q)', False),
    (['f(P)'], 'f(Q) => f(P)', True),
    (['f(P)'], 'f(P) <=> f(Q)', False),

    (['f(P) & f(Q)'], 'f(P)', True),
    (['f(P) & f(Q)'], 'f(Q)', True),
    (['f(P) & f(Q)'], '!f(P)', False),
    (['f(P) & f(Q)'], '!f(Q)', False),
    (['f(P) & f(Q)'], 'f(P) & f(Q)', True),
    (['f(P) & f(Q)'], 'f(P) | f(Q)', True),
    (['f(P) & f(Q)'], 'f(P) => f(Q)', True),
    (['f(P) & f(Q)'], 'f(Q) => f(P)', True),
    (['f(P) & f(Q)'], 'f(P) <=> f(Q)', True),

    (['f(P)', 'f(Q)'], 'f(P)', True),
    (['f(P)', 'f(Q)'], 'f(Q)', True),
    (['f(P)', 'f(Q)'], '!f(P)', False),
    (['f(P)', 'f(Q)'], '!f(Q)', False),
    (['f(P)', 'f(Q)'], 'f(P) & f(Q)', True),
    (['f(P)', 'f(Q)'], 'f(P) | f(Q)', True),
    (['f(P)', 'f(Q)'], 'f(P) => f(Q)', True),
    (['f(P)', 'f(Q)'], 'f(Q) => f(P)', True),
    (['f(P)', 'f(Q)'], 'f(P) <=> f(Q)', True),

    (['f(P) | f(Q)'], 'f(P)', False),
    (['f(P) | f(Q)'], '!f(P)', False),

    (['f(P) => f(Q)'], 'f(P)', False),
    (['f(P) => f(Q)'], 'f(Q)', False),

    (['f(P) & f(Q)', 'f(Q) & f(R)'], 'f(P) & f(R)', True),
    (['f(P) | f(Q)', 'f(Q) | f(R)'], 'f(P) | f(R)', False),
    (['f(P) => f(Q)', 'f(Q) => f(R)'], 'f(P) => f(R)', True),
    (['f(P) <=> f(Q)', 'f(Q) <=> f(R)'], 'f(P) <=> f(R)', True),

    # premises are tautologies
    (['f(P) | !f(P)'], 'f(P)', False),
    (['f(P) | !f(P)'], '!f(P)', False),
    (['f(P) | !f(P)'], 'f(P) | !f(P)', True),

    # premises are contradictions
    ([], 'f(P)', True),
    (['f(P) & !f(P)'], 'f(P)', True),
    (['f(P) & !f(P)'], '!f(P)', True),
    (['f(P) & !f(P)'], 'f(Q)', True),
    (['f(P) & !f(P)'], '!f(Q)', True),
])
def test_infer_propositional_logic(premises, conclusion, expected):
    print(" Truth Table ".center(80, "="))
    entailed = _truth_table(premises, conclusion)
    assert entailed == expected

    print(" Inference ".center(80, "="))
    entailed, _ = _infer(premises, conclusion)
    assert entailed == expected


@pytest.mark.parametrize('premises, conclusion, expected', [
    (['human(Socrates)', '*x: human(x) => mortal(x)'],
     'mortal(Socrates)', True),
    (['human(Socrates)', '*x: human(x) => mortal(x)'],
     'immortal(Socrates)', False),
    (['human(Socrates)', '*x: human(x) => mortal(x) | !mortal(x)'],
     'mortal(Socrates)', False),  # Socrates might be immortal as well
    (['human(Socrates)', '*x: human(x) => mortal(x) | !mortal(x)'],
     '!mortal(Socrates)', False),  # Socrates might be mortal as well

    # all Men are created equal
    (['*x, *y: human(x) & human(y) => equal(x, y)',
      'human(Jane)',
      'human(Frank)'],
     'equal(Jane, Frank)', True),
    # there's no such Man who is not equal to another Man
    (['*x, *y: human(x) & human(y) => equal(x, y)'],
     '?x, ?y: human(x) & human(y) & !equal(x, y)', False),

    (caesar_model, 'hate(Marcus, Caesar)', True),
    (caesar_model, '!hate(Marcus, Caesar)', False),
    (caesar_model, 'loyal(Marcus, Caesar)', False),
    (caesar_model, '!loyal(Marcus, Caesar)', True),
])
def test_infer_first_order_logic(premises, conclusion, expected):
    entailed, _ = _infer(premises, conclusion)
    assert entailed == expected


@pytest.mark.parametrize('premises, conclusion, expected', [
    (['*x: Succ(x) != 0',
      '*x, *y: (Succ(x) = Succ(y)) => x = y',
      '*x: (x = 0 | ?y: x = Succ(y))',
      '*x: Add(x, 0) = x',
      '*x, *y: Add(x, Succ(y)) = Succ(Add(x, y))',
      '*x: Mul(x, 0) = 0',
      '*x, *y: Mul(x, Succ(y)) = Add(Mul(x, y), x)'],
     'Mul(Succ(0), Succ(0)) = Succ(0)', True),

    # all Men are created equal
    (['*x, *y: human(x) & human(y) => x = y',
      '*x, *y: x = y <=> y = x',  # todo: reflexivity axiom
      'human(Jane)',
      'human(Frank)'],
     'Jane = Frank', True),

    # there's no such Man who is not equal to another Man
    (['*x, *y: human(x) & human(y) => x = y'],
     '?x, ?y: human(x) & human(y) & x != y', False),
])
def test_infer_first_order_logic_equality(premises, conclusion, expected):
    entailed, _ = _infer(premises, conclusion)
    assert entailed == expected


@pytest.mark.parametrize('premises, conclusion, expected', [
    # Who hates Caesar?
    (caesar_model, '?x: hate(x, Caesar)', {'x': 'Marcus'}),

    # Who is not loyal to Caesar?
    (caesar_model, '?x: !loyal(x, Caesar)', {'x': 'Marcus'}),
])
def test_query_first_order_logic(premises, conclusion, expected):
    expected = parse_substitution(expected)
    entailed, binding = _infer(premises, conclusion)
    assert entailed
    assert binding == expected


# Helpers
# -----------------------------------------------------------------------------

def _infer(premises, conclusion):
    premises = [parse(k) for k in premises]
    conclusion = parse(conclusion)
    print('premises =', premises)
    print('conclusion =', conclusion)

    binding = inference.infer(premises, conclusion)
    entailed = binding is not None
    print('entailed =', entailed)
    print('binding =', binding)

    return entailed, binding


def _truth_table(premises, conclusion, **kwargs):
    premises = [parse(k) for k in premises]
    conclusion = parse(conclusion)
    print('premises =', premises)
    print('conclusion =', conclusion)

    table = utils.truth_table(*premises, conclusion,
                              header=True,
                              **kwargs)

    entailed = True
    for row in table[1:]:
        premises_rvs = row[-len(premises) - 1:-1]
        conclusion_rv = row[-1]
        if premises_rvs and all(premises_rvs) and not conclusion_rv:
            entailed = False
            row.append("<---")

    print(utils.justify_table(table))
    print('entailed =', entailed)

    return entailed
