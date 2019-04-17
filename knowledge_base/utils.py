def incrementdefault(obj: dict, key, default: int = 0) -> int:
    val = obj.setdefault(key, default) + 1
    obj[key] = val
    return val


def appenddefault(obj: dict, key, val, default: list = None) -> list:
    default = [] if default is None else default
    arr = obj.setdefault(key, default)
    arr.append(val)
    return arr
