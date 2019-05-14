**This is a work in progress.**

An inference engine for First-Order Logic.

Notes:

* The grammar is in `grammar.py` and data structures for representing the syntaxt tree is in `syntax.py`. `cnf.py` 
contains code for converting syntax tree into CNF and `unification.py` contains implementation of the Robinson's 
unification algorithm.
* Note that this only a self-pedagogical tool. It is rather too slow for anything practical.

Example grammar of first-order Peano arithmetic:

```
*x: Succ(x) != 0
*x, *y: (Succ(x) = Succ(y)) => x = y
*x: (x = 0 | ?y: x = Succ(y))
*x: Add(x, 0) = x
*x, *y: Add(x, Succ(y)) = Succ(Add(x, y))
*x: Mul(x, 0) = 0
*x, *y: Mul(x, Succ(y)) = Add(Mul(x, y), x)
```
