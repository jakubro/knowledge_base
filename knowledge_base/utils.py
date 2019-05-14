import itertools
from typing import List


def incrementdefault(obj: dict, key, default: int = 0) -> int:
    """Increments value stored in the `obj` under `key`.

    Returns the incremented value.

    If value with specified key does not exist, then initializes it with
    `default` and then increments it.
    """

    val = obj.setdefault(key, default) + 1
    obj[key] = val
    return val


def appenddefault(obj: dict, key, val, default: list = None) -> list:
    """Appends `val` to list stored in the `obj` under `key`.

    Returns the updated list.

    If value with specified key does not exist, then initializes it with
    `default` (or an empty list, if `default` is None) and then appends the
    `val` to the list.
    """

    default = [] if default is None else default
    arr = obj.setdefault(key, default)
    arr.append(val)
    return arr


def justify_table(table: List[list], fillchar=" ", separator="\t") -> str:
    """:returns: String representation of the table with justified cells."""

    table = [[str(col) for col in row] for row in table]

    widths = []  # by columns
    for row in table:
        for i, col in enumerate(row):
            len_ = len(col)
            try:
                widths[i] = max(widths[i], len_)
            except IndexError:
                widths.append(len_)

    rv = ""
    for row in table:
        for i, col in enumerate(row):
            rv += col.ljust(widths[i], fillchar) + separator
        rv += "\n"
    return rv


def truth_table(*nodes, header=False, **kwargs) -> List[list]:
    symbols = []
    quantified = []
    for k in nodes:
        quantified.extend(_find_quantified_symbols(k))
        symbols.extend(_find_symbols(k))

    # ex. `?x: ?x: x` (note that this does not handle `x & ?x: x`)
    assert len(set(quantified)) == len(quantified)

    free = sorted(set(symbols) - set(quantified))
    quantified = sorted(set(quantified))
    symbols = free + quantified

    # space of values supplied to free/quantified variables

    space = [*(kwargs.get(k, [False, True]) for k in free),
             *(kwargs.get(k, [False, True]) for k in quantified)]

    rv = []

    if header:
        rv.append([*symbols, "|", *nodes])

    for values in itertools.product(*space):
        kws = {k: v for k, v in zip(symbols, values)}
        kws = {**kwargs, **kws}
        evaled = [k.eval(**kws) for k in nodes]
        rv.append([*values, "|", *evaled])

    return rv


def _find_symbols(node):
    if node.is_variable() or node.is_constant():
        yield node.value
    for x in node.children:
        yield from _find_symbols(x)


def _find_quantified_symbols(node):
    if node.is_quantified():
        yield node.get_quantified_variable().value
    for x in node.children:
        yield from _find_quantified_symbols(x)
