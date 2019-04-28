import pytest

import knowledge_base.syntax as syntax
from knowledge_base.grammar import parse


@pytest.mark.parametrize('p, q', [
    # Symbols
    # -------------------------------------------------------------------------

    # Constants and Variables
    ('P', {'Constant': {'Value': 'P'}}),
    ('x', {'Variable': {'Value': 'x'}}),

    # Functions and Predicates of arity >= 1
    ('H(x, y, P, Q)', {
        'Function': {
            'Value': 'H',
            'Children': [{'Variable': {'Value': 'x'}},
                         {'Variable': {'Value': 'y'}},
                         {'Constant': {'Value': 'P'}},
                         {'Constant': {'Value': 'Q'}}]
        }
    }),
    ('f(x, y, P, Q)', {
        'Predicate': {
            'Value': 'f',
            'Children': [{'Variable': {'Value': 'x'}},
                         {'Variable': {'Value': 'y'}},
                         {'Constant': {'Value': 'P'}},
                         {'Constant': {'Value': 'Q'}}]
        }
    }),

    # Function nesting
    ('H(x, P, J(y, Q))', {
        'Function': {
            'Value': 'H',
            'Children': [{'Variable': {'Value': 'x'}},
                         {'Constant': {'Value': 'P'}},
                         {
                             'Function': {
                                 'Value': 'J',
                                 'Children': [{'Variable': {'Value': 'y'}},
                                              {'Constant': {'Value': 'Q'}}]
                             }
                         }]
        }
    }),

    # Functions and Predicates must be of arity >= 1
    ('H()', None),
    ('f()', None),

    # Only Constants, Variables and Functions can appear inside Functions and
    # Predicates
    ('H(f(x))', None),
    ('H(x & y)', None),
    ('H(*x: foo)', None),
    ('f(f(x))', None),
    ('f(x & y)', None),
    ('f(*x: foo)', None),

    # Boolean operators
    # -------------------------------------------------------------------------

    # Negation
    ('!x', {
        'Formula': {
            'Value': 'Not',
            'Children': [{'Variable': {'Value': 'x'}}]
        }
    }),
    ('!!x', {
        'Formula': {
            'Value': 'Not',
            'Children': [{
                'Formula': {
                    'Value': 'Not',
                    'Children': [{'Variable': {'Value': 'x'}}]
                }
            }]
        }
    }),
    ('!!!x', {
        'Formula': {
            'Value': 'Not',
            'Children': [{
                'Formula': {
                    'Value': 'Not',
                    'Children': [{
                        'Formula': {
                            'Value': 'Not',
                            'Children': [{'Variable': {'Value': 'x'}}]
                        }
                    }]
                }
            }]
        }
    }),
    ('!(x & !P)', {
        'Formula': {
            'Value': 'Not',
            'Children': [{
                'Formula': {
                    'Value': 'And',
                    'Children': [{'Variable': {'Value': 'x'}},
                                 {
                                     'Formula': {
                                         'Value': 'Not',
                                         'Children': [
                                             {'Constant': {'Value': 'P'}}
                                         ]
                                     }
                                 }]
                }
            }]
        }
    }),

    # Conjunction
    ('a & b', {
        'Formula': {
            'Value': 'And',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}}]
        }
    }),
    ('a & b & c & d', {
        'Formula': {
            'Value': 'And',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}},
                         {'Variable': {'Value': 'c'}},
                         {'Variable': {'Value': 'd'}}]
        }
    }),

    # Disjunction
    ('a | b', {
        'Formula': {
            'Value': 'Or',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}}]
        }
    }),
    ('a | b | c | d', {
        'Formula': {
            'Value': 'Or',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}},
                         {'Variable': {'Value': 'c'}},
                         {'Variable': {'Value': 'd'}}]
        }
    }),

    # Implication
    ('a => b', {
        'Formula': {
            'Value': 'Implies',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}}]
        }
    }),
    ('a => b => c => d', {
        'Formula': {
            'Value': 'Implies',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}},
                         {'Variable': {'Value': 'c'}},
                         {'Variable': {'Value': 'd'}}]
        }
    }),

    # Equivalence
    ('a <=> b', {
        'Formula': {
            'Value': 'Equals',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}}]
        }
    }),
    ('a <=> b <=> c <=> d', {
        'Formula': {
            'Value': 'Equals',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}},
                         {'Variable': {'Value': 'c'}},
                         {'Variable': {'Value': 'd'}}]
        }
    }),

    # Equality
    # -------------------------------------------------------------------------

    # Equals
    ('a = b', {
        'Function': {
            'Value': 'Equality',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}}]
        }
    }),
    ('a = b = c = d', {
        'Function': {
            'Value': 'Equality',
            'Children': [{'Variable': {'Value': 'a'}},
                         {'Variable': {'Value': 'b'}},
                         {'Variable': {'Value': 'c'}},
                         {'Variable': {'Value': 'd'}}]
        }
    }),

    # Not equals
    ('a != b', {
        'Formula': {
            'Value': 'Not',
            'Children': [{
                'Function': {
                    'Value': 'Equality',
                    'Children': [{'Variable': {'Value': 'a'}},
                                 {'Variable': {'Value': 'b'}}]
                }
            }]
        }
    }),
    ('a != b != c != d', {
        'Formula': {
            'Value': 'Not',
            'Children': [{
                'Function': {
                    'Value': 'Equality',
                    'Children': [{'Variable': {'Value': 'a'}},
                                 {'Variable': {'Value': 'b'}},
                                 {'Variable': {'Value': 'c'}},
                                 {'Variable': {'Value': 'd'}}]
                }
            }]
        }
    }),

    # Quantifiers
    # -------------------------------------------------------------------------

    # Universal
    ('*x: x', {
        'Formula': {
            'Value': {
                'Quantifier': {
                    'Value': 'ForAll',
                    'Children': [{'Variable': {'Value': 'x'}}]
                }
            },
            'Children': [{'Variable': {'Value': 'x'}}]
        }
    }),

    # Existential
    ('?x: x', {
        'Formula': {
            'Value': {
                'Quantifier': {
                    'Value': 'Exists',
                    'Children': [{'Variable': {'Value': 'x'}}]
                }
            },
            'Children': [{'Variable': {'Value': 'x'}}]
        }
    }),

    # Nesting
    ('*x, ?y, ?z: x', {
        'Formula': {
            'Value': {
                'Quantifier': {
                    'Value': 'ForAll',
                    'Children': [{'Variable': {'Value': 'x'}}]
                }
            },
            'Children': [{
                'Formula': {
                    'Value': {
                        'Quantifier': {
                            'Value': 'Exists',
                            'Children': [{'Variable': {'Value': 'y'}}]
                        }
                    },
                    'Children': [{
                        'Formula': {
                            'Value': {
                                'Quantifier': {
                                    'Value': 'Exists',
                                    'Children': [{'Variable': {'Value': 'z'}}]
                                }
                            },
                            'Children': [{'Variable': {'Value': 'x'}}]
                        }
                    }]
                }
            }]
        }
    }),

])
def test_parse(p, q):
    if q is not None:
        q = syntax.Node.loads(q)

    try:
        p = parse(p)
    except ValueError as e:
        if q is not None:
            raise e
        else:
            p = None

    try:
        assert p == q
    except AssertionError as e:
        print("Actual:")
        print(p and p.dumps())
        print("Expected:")
        print(q and q.dumps())
        raise e
