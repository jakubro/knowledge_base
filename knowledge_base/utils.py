import itertools
from typing import List


def incrementdefault(obj: dict, key, default: int = 0) -> int:
    val = obj.setdefault(key, default) + 1
    obj[key] = val
    return val


def appenddefault(obj: dict, key, val, default: list = None) -> list:
    default = [] if default is None else default
    arr = obj.setdefault(key, default)
    arr.append(val)
    return arr


def justify_table(table: List[list], fillchar=" ", separator="\t") -> str:
    table = [[str(col) for col in row] for row in table]

    maxlens = []
    for row in table:
        for i, col in enumerate(row):
            len_ = len(col)
            try:
                maxlens[i] = max(maxlens[i], len_)
            except IndexError:
                maxlens.append(len_)

    rv = ""
    for row in table:
        for i, col in enumerate(row):
            rv += col.ljust(maxlens[i], fillchar) + separator
        rv += "\n"
    return rv


def truth_table(node, **kwargs) -> List[list]:
    # assumes that the variables are already standardized (there are no
    # nested variables with the same name - `?x: ?x: x`)

    quant_symbols = sorted(set(_find_quantified_symbols(node)))
    free_symbols = sorted(set(_find_symbols(node)) - set(quant_symbols))
    symbols = free_symbols + quant_symbols

    space = [[False, True]] * len(free_symbols)
    for k in quant_symbols:
        space.append(kwargs[k])

    rv = []
    for values in itertools.product(*space):
        kws = {k: v for k, v in zip(symbols, values)}
        kws = {**kwargs, **kws}
        evaled = node.eval(**kws)
        rv.append([*values, evaled])
    return rv


def _find_symbols(node):
    if node.is_variable() or node.is_constant():
        yield node.value
    else:
        for x in node.children:
            yield from _find_symbols(x)


def _find_quantified_symbols(node):
    if node.is_quantified():
        yield node.get_quantified_variable().value
    else:
        for x in node.children:
            yield from _find_quantified_symbols(x)
