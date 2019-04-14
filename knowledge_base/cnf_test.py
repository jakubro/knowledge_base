import pyparsing as pp

import cnf
import grammar

pp.ParserElement.enablePackrat()

tests = """
    x
    ?x: x
    *x: x
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
            print("Parsed")
            print("".ljust(20, "-"), "\n")

            assert len(node) == 1
            node = node[0]
            print(node, "\n")
            print(repr(node), "\n")

            print("CNF")
            print("".ljust(20, "-"), "\n")

            converted = cnf.convert_to_cnf(node)
            print("\n")
            print(converted, "\n")
            print(repr(converted), "\n")
        finally:
            print("".ljust(79, "-"), "\n")


if __name__ == '__main__':
    main()
