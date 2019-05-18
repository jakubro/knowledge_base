**This is a work in progress.**

An inference engine for First-Order Logic with Equality.

Notes:

* The grammar and its documentation is in `grammar.py`. Data structures for representing the syntax tree is in 
`syntax.py`. 
* `cnf.py` contains code for converting syntax trees into CNF, `unification.py` contains implementation of the 
Robinson's unification algorithm and `inference.py` performs the inference via binary resolution and paramodulation.
* Note that this only a self-pedagogical tool. It is rather too slow for anything practical.

To get started, run `main.py`:

```
$ python main.py -h
usage: main.py [-h] [-v] [-vv]

Knowledge base

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Be verbose.
  -vv, --debug   Be even more verbose.
``` 

Example session:

```
$ python main.py
Knowledge base

Usage:

        help                Show this help screen
        list                List content of the knowledge base
        axiom <formula>     Add axiom to the knowledge base
        lemma <formula>     Prove and add lemma to the knowledge base
        prove <formula>     Prove formula
        query <formula>     Shows binding list that satisfies the formula

>> axiom man(Marcus)
>> axiom roman(Marcus)
>> axiom *x: man(x) => person(x)
>> axiom ruler(Caesar)
>> axiom *x: roman(x) => loyal(x, Caesar) | hate(x, Caesar)
>> axiom *x, ?y: loyal(x, y)
>> axiom *x, *y: person(x) & ruler(y) & tryAssassin(x, y) => !loyal(x, y)
>> axiom tryAssassin(Marcus, Caesar)
>> list
man(Marcus)
roman(Marcus)
*x: (man(x) => person(x))
ruler(Caesar)
*x: (roman(x) => hate(x, Caesar) | loyal(x, Caesar))
*x: ?y: loyal(x, y)
*x: *y: (person(x) & ruler(y) & tryAssassin(x, y) => !loyal(x, y))
tryAssassin(Marcus, Caesar)

>> prove hate(Marcus, Caesar)
Formula is entailed by the knowledge base.

>> prove loyal(Marcus, Caesar)
Formula is not entailed by the knowledge base.

>> query ?x: hate(x, Caesar)
x = Marcus

>> query ?x: !loyal(x, Caesar)
x = Marcus
```
