import copy

import pytest

from knowledge_base import utils
from knowledge_base.grammar import parse


@pytest.mark.parametrize('before', [None, 0, 1])
@pytest.mark.parametrize('default', [None, 0, 1])
def test_incrementdefault(before, default):
    obj = {'key': before}
    obj = {k: v for k, v in obj.items() if v is not None}

    args = (x for x in (obj, 'key', default) if x is not None)
    rv = utils.incrementdefault(*args)
    assert obj['key'] == rv

    if before is not None:
        assert rv == before + 1
    elif default is not None:
        assert rv == default + 1
    else:
        assert rv == 1


@pytest.mark.parametrize('before', [None, [], ['foo']])
@pytest.mark.parametrize('default', [None, [], ['foo']])
def test_appenddefault(before, default):
    orig_before = copy.copy(before)
    orig_default = copy.copy(default)

    obj = {'key': before}
    obj = {k: v for k, v in obj.items() if v is not None}

    val = object()
    args = (x for x in (obj, 'key', val, default) if x is not None)
    rv = utils.appenddefault(*args)
    assert obj['key'] is rv
    assert val in rv

    if before is not None:
        assert rv is before
        assert rv == [*orig_before, val]
    elif default is not None:
        assert rv is default
        assert rv == [*orig_default, val]
    else:
        assert rv == [val]


@pytest.mark.parametrize('table, expected', [
    ([[0, 1, 2],
      ['aa', 'b', 'c'],
      ['x', 123, '']],
     ('0 \t1  \t2\t\n'
      'aa\tb  \tc\t\n'
      'x \t123\t \t\n')),
])
def test_justify_table(table, expected):
    assert utils.justify_table(table) == expected


@pytest.mark.parametrize('expr, kwargs, expected', [
    ('C', {'C': [-1, 1]}, [[-1, '|', -1], [1, '|', 1]]),
    ('x', {'x': [-1, 1]}, [[-1, '|', -1], [1, '|', 1]]),

    ('H(y, x)', {
        'x': [2],
        'y': [1],
        'H': lambda x, y: x + y
    },
     [[2, 1, '|', 3]]),

    ('p(y, x)', {
        'x': [2],
        'y': [1],
        'p': lambda x, y: x + y
    },
     [[2, 1, '|', 3]]),

    ('p(x) & p(y)', {
        'x': [-1, 1],
        'y': [-1, 1],
        'p': lambda i: i > 0
    },
     [[-1, -1, '|', False],
      [-1, 1, '|', False],
      [1, -1, '|', False],
      [1, 1, '|', True]]),

    ('*x, *y: x = y', {
        'x': [0, 1],
        'y': [1, 2]
    },
     [[0, 1, '|', False],
      [0, 2, '|', False],
      [1, 1, '|', True],
      [1, 2, '|', False]]),
])
def test_truth_table(expr, kwargs, expected):
    expr = parse(expr, _allow_partial_expression=True)
    rv = utils.truth_table(expr, **kwargs)
    print(utils.justify_table(rv))
    assert rv == expected
