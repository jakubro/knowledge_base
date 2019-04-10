import pyparsing as pp

import knowledge_base.grammar

pp.ParserElement.enablePackrat()

knowledge_base.grammar.Formula.runTests("""
    *x: succ(x) != 0
    *x, *y: (succ(x) = succ(y)) => x = y
    *x: (x = 0 | ?y: x = succ(y))
    *x: add(x, 0) = x
    *x, *y: add(x, succ(y)) = succ(add(x, y))
    *x: mul(x, 0) = 0
    *x, *y: mul(x, succ(y)) = add(mul(x, y), x)
""")
