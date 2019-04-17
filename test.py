import pyparsing as pp
import pytest

import knowledge_base.cnf
import knowledge_base.grammar

pp.ParserElement.enablePackrat()

tests = """
    MaxInt32                # Constant
    person_1                # Variable
    FatherOf(x)             # Function
    livesIn(x, Paris)       # Predicate
    
    x
    !x                      # Negation
    x & y                   # Conjunction
    x | y                   # Disjunction
    x => y                  # Implication
    x <=> y                 # Equivalence

    x = y                   # Equation
    x != y

    child(x, parent(x), Loves(Paris))

    ?x: x = x
    *x: x = x
    *x, ?y: x = y
    *x, *x: x(x)

    a | b | c & d
    a | b | c | d
    a = b = c = d
    a != b != c != d
    !!!!a
    
    d & c & b | a
    d & c & (b | a)
    
    *x, ?y: (p(x) | q(x)) & r(x, y) => ?z: (r(x, z) = r(y, z)) & (p(z) = q(z))
    
    r(x, F(x), M(B))
    r(B, F(B), y)
"""


def parse_tests():
    for s in tests.strip().split("\n"):
        s = s.strip()
        if s.startswith('#'):
            continue
        s = s.split('#')[0]
        s = s.strip()
        if not s:
            continue
        yield s


def main():
    for s in parse_tests():
        print("Input:\t", s)
        try:
            make_cnf(s)
        except Exception as e:
            print(e.__class__.__module__ + '.' +
                  e.__class__.__name__ + ": " +
                  str(e) + "\n")
        finally:
            print("\n" + "".ljust(79, "-") + "\n")


@pytest.mark.parametrize('s', list(parse_tests()))
def test(s: str):
    print("Input:\t", s)
    make_cnf(s)
    print("\n" + "".ljust(79, "-") + "\n")


def make_cnf(s: str):
    node = knowledge_base.grammar.parse(s)
    print("Parsed:\t", node)
    # print("\n" + node.dumps(compact=False) + "\n")

    converted = knowledge_base.cnf.convert_to_cnf(node)
    print("CNF:\t", converted)
    # print("\n" + converted.dumps(compact=False) + "\n")


if __name__ == '__main__':
    main()
