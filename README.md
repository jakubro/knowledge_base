**This is a work in progress.**

An inference engine for First-Order Logic.

Notes:

* The grammar is in `grammar.py` and data structures for representing the syntaxt tree is in `syntax.py`. `cnf.py` 
contains code for converting syntax tree into CNF and `unification.py` contains implementation of the Robinson's 
unification algorithm.

Example grammar of first-order Peano arithmetic:

```
*x: succ(x) != 0
*x, *y: (succ(x) = succ(y)) => x = y
*x: (x = 0 | ?y: x = succ(y))
*x: add(x, 0) = x
*x, *y: add(x, succ(y)) = succ(add(x, y))
*x: mul(x, 0) = 0
*x, *y: mul(x, succ(y)) = add(mul(x, y), x)
```
