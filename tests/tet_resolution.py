import itertools

import pytest

import knowledge_base.resolution as resolution
import knowledge_base.syntax as syntax
import knowledge_base.utils as utils
from knowledge_base.grammar import parse


@pytest.mark.parametrize('premises, conclusion, expected', [
    (['P'], 'P', True),
    (['P'], '!P', False),
    (['P'], 'Q', False),
    (['P'], '!Q', False),
    (['P'], 'P & Q', False),  # p=T, q=F
    (['P'], 'P | Q', True),
    (['P'], 'P => Q', False),  # p=T, q=F
    (['P'], 'Q => P', True),
    (['P'], 'P <=> Q', False),  # p=T, q=F

    (['P & Q'], 'P', True), (['P', 'Q'], 'P', True),
    (['P & Q'], 'Q', True), (['P', 'Q'], 'Q', True),
    (['P & Q'], '!P', False), (['P', 'Q'], '!P', False),  # p=T, q=T
    (['P & Q'], '!Q', False), (['P', 'Q'], '!Q', False),  # p=T, q=T
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
    (['P | Q', 'Q | R'], 'P | R', False),  # p=F, q=T, r=F
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
    _test_truth_table(premises, conclusion, expected)
    _test_resolve(premises, conclusion, expected)


def _test_resolve(premises, conclusion, expected):
    premises = [parse(k) for k in premises]
    conclusion = parse(conclusion)
    print('premises =', premises)
    print('conclusion =', conclusion)

    rv = resolution.resolve(premises, conclusion)
    print('rv:', rv)
    assert rv == expected


def _test_truth_table(premises, conclusion, expected):
    premises = [parse(k) for k in premises]
    conclusion = parse(conclusion)
    print('premises =', premises)
    print('conclusion =', conclusion)

    symbols = [list(_find_symbols(f)) for f in (*premises, conclusion)]
    symbols = [s for f in symbols for s in f]
    symbols = sorted(set(symbols))

    table = [[*symbols, "|", *premises, "|", conclusion]]

    actual = True
    space = [[False, True]] * len(symbols)
    for values in itertools.product(*space):
        kws = {k: v for k, v in zip(symbols, values)}
        premises_rvs = [k.eval(**kws) for k in premises]
        conclusion_rv = conclusion.eval(**kws)

        row = [*values, "|", *premises_rvs, "|", conclusion_rv]
        table.append(row)

        if premises_rvs and all(premises_rvs) and not conclusion_rv:
            actual = False
            row.append("<---")

    print(utils.justify_table(table))
    assert actual == expected


def _find_symbols(node: syntax.Node):
    if node.is_variable() or node.is_constant():
        yield node.value
    else:
        # ignoring node.value - does not make sense in propositional logic
        for x in node.children:
            yield from _find_symbols(x)
