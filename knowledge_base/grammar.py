"""First order logic grammar."""

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


def Named(expr: pp.ParserElement, name: str) -> pp.ParserElement:
    expr.setName(name)
    expr.addParseAction(pp.replaceWith(name))
    return expr


# Syntax tree
# -----------------------------------------------------------------------------

def make_node(type_: str):
    def _parse_action(tokens):
        tokens = tokens.asList()
        return syntax.Node(type_=type_,
                           value=tokens[0],
                           children=tokens[1:])

    return _parse_action


def make_unary_node(type_: str):
    def _parse_action(tokens):
        tokens = tokens.asList()
        return syntax.Node(type_=type_,
                           value=tokens[0][0],
                           children=tokens[0][1:])

    return _parse_action


def make_binary_node(type_: str):
    def _parse_action(tokens):
        tokens = tokens.asList()
        return syntax.Node(type_=type_,
                           value=tokens[0][1],
                           children=tokens[0][::2])

    return _parse_action


def negate_binary_infix(type_: str, expr: pp.ParserElement):
    def _parse_action(tokens):
        inner = syntax.Node(type_=type_,
                            value=expr.name,
                            children=tokens[0][::2])
        return inner.negate()

    return _parse_action


def nest(type_: str):
    def _parse_action(tokens):
        assert len(tokens) == 2
        head = tokens[0]
        tail = tokens[1]

        previous = tail
        for h in reversed(head):
            previous = syntax.Node(type_=type_,
                                   value=h,
                                   children=[previous])
        return previous

    return _parse_action


# Grammar
# -----------------------------------------------------------------------------

Symbol = pp.Forward()
Variable = pp.Forward()
Formula = pp.Forward()
QuantifiedFormula = pp.Forward()
QuantifiedVariable = pp.Forward()
Term = pp.Forward()
Functional = pp.Forward()

# Keywords
# -----------------------------

# Truth literals
TRUE = Named(pp.CaselessKeyword('True'),
             syntax.TRUE)
FALSE = Named(pp.CaselessKeyword('False'),
              syntax.FALSE)

# Equality
VALUE_EQUAL = Named(pp.Literal('='),
                    syntax.EQUALITY)
NOT_VALUE_EQUAL = pp.Literal('!=')

# Unary operators
NOT = Named(pp.CaselessKeyword('Not') ^ pp.Literal('!'),
            syntax.NEGATION)

# Binary operators
AND = Named(pp.CaselessKeyword('And') ^ pp.Literal('&'),
            syntax.CONJUNCTION)
OR = Named(pp.CaselessKeyword('Or') ^ pp.Literal('|'),
           syntax.DISJUNCTION)
IMPLIES = Named(pp.CaselessKeyword('Implies') ^ pp.Literal('=>'),
                syntax.IMPLICATION)
EQUALS = Named(pp.CaselessKeyword('Equals') ^ pp.Literal('<=>'),
               syntax.EQUIVALENCE)

# Quantifiers
FOR_ALL = Named(pp.CaselessKeyword('ForAll') ^ pp.Literal('*'),
                syntax.UNIVERSAL_QUANTIFIER)
EXISTS = Named(pp.CaselessKeyword('Exists') ^ pp.Literal('?'),
               syntax.EXISTENTIAL_QUANTIFIER)

# Grammar
# -----------------------------

Keyword = (NOT | VALUE_EQUAL | NOT_VALUE_EQUAL |
           AND | OR | IMPLIES | EQUALS |
           FOR_ALL | EXISTS)

Symbol << (~Keyword +
           pp.Word(pp.alphanums))

Variable << Symbol.copy().addParseAction(make_node(syntax.VARIABLE))

Formula << pp.infixNotation((Term ^ QuantifiedFormula), [
    (VALUE_EQUAL, 2, pp.opAssoc.LEFT, make_binary_node(syntax.FUNCTIONAL)),
    (NOT_VALUE_EQUAL, 2, pp.opAssoc.LEFT,
     negate_binary_infix(syntax.FUNCTIONAL, VALUE_EQUAL)),
    (NOT, 1, pp.opAssoc.RIGHT, make_unary_node(syntax.FORMULA)),
    (AND, 2, pp.opAssoc.LEFT, make_binary_node(syntax.FORMULA)),
    (OR, 2, pp.opAssoc.LEFT, make_binary_node(syntax.FORMULA)),
    (EQUALS, 2, pp.opAssoc.LEFT, make_binary_node(syntax.FORMULA)),
    (IMPLIES, 2, pp.opAssoc.LEFT, make_binary_node(syntax.FORMULA)),
])

QuantifiedFormula << (pp.Group(pp.delimitedList(QuantifiedVariable)) +
                      pp.Suppress(':') +
                      Formula).addParseAction(nest(syntax.FORMULA))

QuantifiedVariable << ((FOR_ALL ^ EXISTS) +
                       Variable).addParseAction(make_node(syntax.QUANTIFIER))

Term << (Functional ^ Variable)

Functional << (Symbol +
               make_list(Term)).addParseAction(make_node(syntax.FUNCTIONAL))
