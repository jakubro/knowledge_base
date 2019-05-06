import itertools

import pytest

import knowledge_base.resolution as resolution
import knowledge_base.syntax as syntax
import knowledge_base.utils as utils
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
    (['P'], 'P', True),
    (['P'], '!P', False),
    (['P'], 'Q', False),
    (['P'], '!Q', False),
    (['P'], 'P & Q', False),
    (['P'], 'P | Q', True),
    (['P'], 'P => Q', False),
    (['P'], 'Q => P', True),
    (['P'], 'P <=> Q', False),

    (['P & Q'], 'P', True), (['P', 'Q'], 'P', True),
    (['P & Q'], 'Q', True), (['P', 'Q'], 'Q', True),
    (['P & Q'], '!P', False), (['P', 'Q'], '!P', False),
    (['P & Q'], '!Q', False), (['P', 'Q'], '!Q', False),
    (['P & Q'], 'P & Q', True), (['P', 'Q'], 'P & Q', True),
    (['P & Q'], 'P | Q', True), (['P', 'Q'], 'P | Q', True),
    (['P & Q'], 'P => Q', True), (['P', 'Q'], 'P => Q', True),
    (['P & Q'], 'Q => P', True), (['P', 'Q'], 'Q => P', True),
    (['P & Q'], 'P <=> Q', True), (['P', 'Q'], 'P <=> Q', True),

    (['P | Q'], 'P', False),
    (['P | Q'], '!P', False),

    (['P => Q'], 'P', False),
    (['P => Q'], 'Q', False),

    (['P & Q', 'Q & R'], 'P & R', True),
    (['P | Q', 'Q | R'], 'P | R', False),
    (['P => Q', 'Q => R'], 'P => R', True),
    (['P <=> Q', 'Q <=> R'], 'P <=> R', True),

    # premises are tautologies
    (['P | !P'], 'P', False),
    (['P | !P'], '!P', False),
    (['P | !P'], 'P | !P', True),

    # premises are contradictions
    ([], 'P', True),
    (['P & !P'], 'P', True),
    (['P & !P'], '!P', True),
    (['P & !P'], 'Q', True),
    (['P & !P'], '!Q', True),
])
def test_resolve_propositional_logic(premises, conclusion, expected):
    entailed = _truth_table(premises, conclusion)
    assert entailed == expected
    entailed, _ = _resolve(premises, conclusion)
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
     '?x, ?y: human(x) & human(z) & !equal(x, z)', False),

    (caesar_model, 'hate(Marcus, Caesar)', True),
    (caesar_model, '!hate(Marcus, Caesar)', False),
    (caesar_model, 'loyal(Marcus, Caesar)', False),
    (caesar_model, '!loyal(Marcus, Caesar)', True),
])
def test_resolve_first_order_logic(premises, conclusion, expected):
    entailed, _ = _resolve(premises, conclusion)
    assert entailed == expected


@pytest.mark.parametrize('premises, conclusion, expected', [
    # Who hates Caesar?
    (caesar_model, '?x: hate(x, Caesar)', {'x': 'Marcus'}),

    # Who is not loyal to Caesar?
    (caesar_model, '?x: !loyal(x, Caesar)', {'x': 'Marcus'}),
])
def test_query_first_order_logic(premises, conclusion, expected):
    expected = parse_substitution(expected)
    entailed, binding = _resolve(premises, conclusion)
    assert entailed
    assert binding == expected


def _resolve(premises, conclusion):
    premises = [parse(k) for k in premises]
    conclusion = parse(conclusion)
    print('premises =', premises)
    print('conclusion =', conclusion)

    entailed, binding = resolution.resolve(premises, conclusion)
    print('entailed =', entailed)
    print('binding =', binding)

    return entailed, binding


def _truth_table(premises, conclusion):
    premises = [parse(k) for k in premises]
    conclusion = parse(conclusion)
    print('premises =', premises)
    print('conclusion =', conclusion)

    symbols = [list(_find_symbols(f)) for f in (*premises, conclusion)]
    symbols = [s for f in symbols for s in f]
    symbols = sorted(set(symbols))

    table = [[*symbols, "|", *premises, "|", conclusion]]

    entailed = True
    space = [[False, True]] * len(symbols)
    for values in itertools.product(*space):
        kws = {k: v for k, v in zip(symbols, values)}
        premises_rvs = [k.eval(**kws) for k in premises]
        conclusion_rv = conclusion.eval(**kws)

        row = [*values, "|", *premises_rvs, "|", conclusion_rv]
        table.append(row)

        if premises_rvs and all(premises_rvs) and not conclusion_rv:
            entailed = False
            row.append("<---")

    print(utils.justify_table(table))
    print('entailed =', entailed)

    return entailed


def _find_symbols(node: syntax.Node):
    if node.is_variable() or node.is_constant():
        yield node.value
    else:
        # ignoring node.value - does not make sense in propositional logic
        for x in node.children:
            yield from _find_symbols(x)
