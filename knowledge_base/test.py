import pyparsing as pp

import cnf
import grammar

pp.ParserElement.enablePackrat()

tests = """
    x
    !x

    x & y
    x | y
    x => y
    x <=> y

    x = y
    x != y

    number(x)
    similar(x, y)
    child(x, parent(x))

    ?x: x
    *x: x
    *x, ?y: x = y
    *x, *x: x(x)

    a | b | c & d
    a | b | c | d
    a = b = c = d
    !!!!a
    a | b | c & d
    
    *x, ?y: (p(x) | q(x)) & r(x, y) => ?z: (r(x, z) = r(y, z)) & (p(z) = q(z))
    
    _foo        # symbol cannot start with an underscore
"""


def main():
    for s in tests.strip().split("\n"):
        s = s.strip()
        if s.startswith('#'):
            continue
        s = s.split('#')[0]
        s = s.strip()
        if not s:
            continue

        print("Input:\t", s)
        try:
            test_cnf(s)
        except pp.ParseBaseException as e:
            # Suppress traceback, because usually it is too long.
            print(e.__class__.__module__ + '.' +
                  e.__class__.__name__ + ": " +
                  str(e) + "\n")
        finally:
            print("\n" + "".ljust(79, "-") + "\n")


def test_cnf(s: str) -> None:
    node = grammar.Formula.parseString(s)
    assert len(node) == 1
    node = node[0]
    print("Parsed:\t", node)

    converted = cnf.convert_to_cnf(node)
    print("CNF:\t", converted)
    assert cnf.is_cnf(converted)


if __name__ == '__main__':
    main()
