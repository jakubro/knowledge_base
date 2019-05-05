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
