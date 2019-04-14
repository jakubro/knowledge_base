import pyparsing as pp

import grammar

pp.ParserElement.enablePackrat()

tests = """
    x
    True
    False
    True & False
    True | False
    True => False
    True <=> False
    x = x
    x != x
    x != y
    number(x)
    succ(x) != 0
    *x: succ(x) != 0
    *x, *y: (succ(x) = succ(y)) => x = y
    *x: (x = 0 | ?y: x = succ(y))
    *x: add(x, 0) = x
    *x, *y: add(x, succ(y)) = succ(add(x, y))
    *x: mul(x, 0) = 0
    *x, *y: mul(x, succ(y)) = add(mul(x, y), x)
    *x, *x: x(x)
    ?x, ?y: x = y
    ?x, ?y, *z: (x = y) => Add(y, z) = Add(x, z) 
    *x, *y: (x != y) => ?z: x = Add(y, z) 
    *x: (*y: Animal(y) => Loves(x, y)) => ?y: Loves(y, x)
"""


def main():
    for s in tests.strip().split("\n"):
        s = s.strip()
        print(s, "\n")

        try:
            node = grammar.Formula.parseString(s)
        except Exception as e:
            print(e, "\n")
        else:
            assert len(node) == 1
            node = node[0]
            print(node, "\n")
            print(repr(node), "\n")
        finally:
            print("".ljust(79, "-"), "\n")


if __name__ == '__main__':
    main()
