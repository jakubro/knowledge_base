"""First-Order Logic Grammar

Unary operators:

    !x                          Negation

Binary operators:

    x & y                       Conjunction
    x | y                       Disjunction
    x => y                      Implication
    x <=> y                     Equivalence

Constants and variables:

    Length

Functions and predicates:

    Closed(arg1, arg2, ...)
    x = y                       Equality
    x != y                      Negated equality

Quantifiers:

    *x: Number(x)               Universal quantification
    ?x: Number(x)               Existential quantification
    *x, ?y: x = y               Nesting (for all x, there exists y, ...)

Parenthesis:

    (x | y | z) & (g | h)

"""

import pyparsing as pp

import syntax


# Helpers
# -----------------------------------------------------------------------------

def make_list(expr: pp.ParserElement,
              optional=True, opener='(', closer=')',
              delim=', ', combine=False) -> pp.ParserElement:
    inner = pp.delimitedList(expr, delim=delim, combine=combine)
    outer = pp.Optional(inner) if optional else inner

    return (pp.Suppress(opener) +
            outer +
            pp.Suppress(closer))


def named(expr: pp.ParserElement, name: str) -> pp.ParserElement:
    expr.setName(name)
    expr.addParseAction(pp.replaceWith(name))
    return expr


# Syntax tree
# -----------------------------------------------------------------------------

def make_node(type_: str):
    def parse_action(tokens):
        return syntax.Node(type_=type_,
                           value=tokens[0],
                           children=tokens[1:])

    return parse_action


def unary_operator(type_: str):
    def parse_action(tokens):
        tokens = tokens[0]
        return syntax.Node(type_=type_,
                           value=tokens[0],
                           children=tokens[1:])

    return parse_action


def binary_operator(type_: str):
    def parse_action(tokens):
        tokens = tokens[0]
        return nest_binary_operators(type_=type_,
                                     operator=tokens[1],
                                     operands=tokens[::2])

    return parse_action


def nest_binary_operators(type_: str, operator: str, operands: list):
    previous = operands.pop()
    for h in reversed(operands):
        previous = syntax.Node(type_=type_,
                               value=operator,
                               children=[h, previous])
    return previous


def negated_binary_infix_operator(type_: str, expr: pp.ParserElement):
    def parse_action(tokens):
        tokens = tokens[0]
        rv = syntax.Node(type_=type_,
                         value=expr.name,
                         children=tokens[::2])
        return rv.negate()

    return parse_action


def nest_formulas(type_: str):
    def parse_action(tokens):
        assert len(tokens) == 2
        quantifiers = tokens[0]
        formula = tokens[1]

        previous = formula
        for h in reversed(quantifiers):
            previous = syntax.Node(type_=type_,
                                   value=h,
                                   children=[previous])
        return previous

    return parse_action


# Grammar
# -----------------------------------------------------------------------------

Symbol = pp.Forward()
Variable = pp.Forward()
Formula = pp.Forward()
QuantifiedFormula = pp.Forward()
QuantifiedVariable = pp.Forward()
Term = pp.Forward()
Function = pp.Forward()

# Keywords
# -----------------------------

# Equality
VALUE_EQUAL = named(pp.Literal('='),
                    syntax.EQUALITY)
NOT_VALUE_EQUAL = pp.Literal('!=')

# Unary operators
NOT = named(pp.CaselessKeyword('Not') ^ pp.Literal('!'),
            syntax.NEGATION)

# Binary operators
AND = named(pp.CaselessKeyword('And') ^ pp.Literal('&'),
            syntax.CONJUNCTION)
OR = named(pp.CaselessKeyword('Or') ^ pp.Literal('|'),
           syntax.DISJUNCTION)
IMPLIES = named(pp.CaselessKeyword('Implies') ^ pp.Literal('=>'),
                syntax.IMPLICATION)
EQUALS = named(pp.CaselessKeyword('Equals') ^ pp.Literal('<=>'),
               syntax.EQUIVALENCE)

# Quantifiers
FOR_ALL = named(pp.CaselessKeyword('ForAll') ^ pp.Literal('*'),
                syntax.UNIVERSAL_QUANTIFIER)
EXISTS = named(pp.CaselessKeyword('Exists') ^ pp.Literal('?'),
               syntax.EXISTENTIAL_QUANTIFIER)

# Grammar
# -----------------------------

Keyword = (NOT | VALUE_EQUAL | NOT_VALUE_EQUAL |
           AND | OR | IMPLIES | EQUALS |
           FOR_ALL | EXISTS)

Symbol << (~Keyword + ~pp.Literal('_') + pp.Word(pp.alphanums))

Variable << Symbol.copy().addParseAction(make_node(syntax.VARIABLE))

Formula << pp.infixNotation((Term ^ QuantifiedFormula), [
    (VALUE_EQUAL, 2, pp.opAssoc.LEFT, binary_operator(syntax.FUNCTION)),
    (NOT_VALUE_EQUAL, 2, pp.opAssoc.LEFT,
     negated_binary_infix_operator(syntax.FUNCTION, VALUE_EQUAL)),
    (NOT, 1, pp.opAssoc.RIGHT, unary_operator(syntax.FORMULA)),
    (AND, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
    (OR, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
    (EQUALS, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
    (IMPLIES, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
])

QuantifiedFormula << (pp.Group(pp.delimitedList(QuantifiedVariable)) +
                      pp.Suppress(':') +
                      Formula).addParseAction(nest_formulas(syntax.FORMULA))

QuantifiedVariable << ((FOR_ALL ^ EXISTS) +
                       Variable).addParseAction(make_node(syntax.QUANTIFIER))

Term << (Function ^ Variable)

Function << (Symbol +
             make_list(Term)).addParseAction(make_node(syntax.FUNCTION))
