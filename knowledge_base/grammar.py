"""First-Order Logic Grammar

Symbols:

    MaxInt32                Constant (starts with uppercase letter or digit)
    person_1                Variable (starts with lowercase letter)
    FatherOf(x)             Function
    livesIn(x, Paris)       Predicate

Boolean operators:

    !x                      Negation
    x & y                   Conjunction
    x | y                   Disjunction
    x => y                  Implication
    x <=> y                 Equivalence

Equality:

    x = y                   Equality
    x != y                  Shorthand for !(x = y)

Quantifiers:

    *x: Number(x)           Universal quantification
    ?x: Number(x)           Existential quantification
    *x, ?y: x = y           Nesting (for all x, there exists y, ...)

Parenthesis:

    (x | y | z) & (g | h)

"""

import pyparsing as pp

import knowledge_base.syntax as syntax


# Helpers
# -----------------------------------------------------------------------------

def make_list(expr: pp.ParserElement,
              optional=False, opener='(', closer=')',
              delim=', ', combine=False) -> pp.ParserElement:
    """Creates enclosed delimited list. (Useful for parsing list of arguments,
    e.g. `(a, b)` or just an empty list, `()`.)"""

    inner = pp.delimitedList(expr, delim=delim, combine=combine)
    outer = pp.Optional(inner) if optional else inner

    return (pp.Suppress(opener) +
            outer +
            pp.Suppress(closer))


def named(expr: pp.ParserElement, name: str) -> pp.ParserElement:
    """Tags parsed expression and standardizes its name."""

    expr.setName(name)  # tag
    expr.addParseAction(pp.replaceWith(name))  # standardize
    return expr


# Syntax tree
# -----------------------------------------------------------------------------

def make_node(type_: str):
    """Parses list of at least one token into a `Node`."""

    def parse_action(tokens):
        assert len(tokens) >= 1
        return syntax.Node(type_=type_,
                           value=tokens[0],
                           children=tokens[1:])

    return parse_action


def unary_operator(type_: str):
    """Parses unary operator into a `Node`."""

    def parse_action(tokens):
        assert len(tokens) == 1
        tokens = tokens[0]
        assert len(tokens) == 2
        return syntax.Node(type_=type_,
                           value=tokens[0],
                           children=tokens[1:])

    return parse_action


def binary_operator(type_: str):
    """Parses binary operator into a `Node`."""

    def parse_action(tokens):
        assert len(tokens) == 1
        tokens = tokens[0]
        return syntax.Node(type_=type_,
                           value=tokens[1],
                           children=tokens[::2])

    return parse_action


def negate_binary_operator(type_: str, expr: pp.ParserElement):
    """Replaces binary operator with its negation."""

    # replace expressions of type `x != y` with `!(x = y)`
    def parse_action(tokens):
        assert len(tokens) == 1
        tokens = tokens[0]
        rv = syntax.Node(type_=type_,
                         value=expr.name,
                         children=tokens[::2])
        return rv.negate()

    return parse_action


def nest_quantified_formulas(type_: str):
    """Nests quantified formulas."""

    # replace expressions of type `?x, ?y: foo` with `?x: ?y: foo`
    def parse_action(tokens):
        assert len(tokens) == 2
        quantifiers = tokens[0]
        formula = tokens[1]

        inner = formula
        for h in reversed(quantifiers):
            inner = syntax.Node(type_=type_,
                                value=h,
                                children=[inner])
        return inner

    return parse_action


# Grammar
# -----------------------------------------------------------------------------

ConstantSymbol = pp.Forward()
VariableSymbol = pp.Forward()
Constant = pp.Forward()
Variable = pp.Forward()
Function = pp.Forward()
Predicate = pp.Forward()
Term = pp.Forward()
AtomicFormula = pp.Forward()
ComplexFormula = pp.Forward()
Formula = pp.Forward()
QuantifiedFormula = pp.Forward()
QuantifiedVariable = pp.Forward()

# Keywords
# -----------------------------

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

# Equality
VALUE_EQUAL = named(pp.Literal('='),
                    syntax.EQUALITY)
VALUE_NOT_EQUAL = pp.Literal('!=')

# Quantifiers
FOR_ALL = named(pp.CaselessKeyword('ForAll') ^ pp.Literal('*'),
                syntax.UNIVERSAL_QUANTIFIER)
EXISTS = named(pp.CaselessKeyword('Exists') ^ pp.Literal('?'),
               syntax.EXISTENTIAL_QUANTIFIER)

# Grammar
# -----------------------------

Keyword = (NOT | AND | OR | IMPLIES | EQUALS |
           VALUE_EQUAL | VALUE_NOT_EQUAL |
           FOR_ALL | EXISTS)

ConstantSymbol << (~Keyword + ~pp.Literal('_') +
                   pp.Word(pp.alphanums.upper(), pp.alphanums + '_'))

Constant << ConstantSymbol
Constant.addParseAction(make_node(syntax.CONSTANT))

VariableSymbol << (~Keyword + ~pp.Literal('_') +
                   pp.Word(pp.alphas.lower(), pp.alphanums + '_'))

Variable << VariableSymbol
Variable.addParseAction(make_node(syntax.VARIABLE))

Formula << (AtomicFormula ^ ComplexFormula ^ QuantifiedFormula)

AtomicFormula << (Predicate ^ pp.infixNotation(Term, [
    (VALUE_EQUAL, 2, pp.opAssoc.LEFT, binary_operator(syntax.FUNCTION)),
    (VALUE_NOT_EQUAL, 2, pp.opAssoc.LEFT,
     negate_binary_operator(syntax.FUNCTION, VALUE_EQUAL)),
]))

ComplexFormula << pp.infixNotation(AtomicFormula ^ QuantifiedFormula, [
    (NOT, 1, pp.opAssoc.RIGHT, unary_operator(syntax.FORMULA)),
    (AND, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
    (OR, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
    (EQUALS, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
    (IMPLIES, 2, pp.opAssoc.LEFT, binary_operator(syntax.FORMULA)),
])

QuantifiedFormula << (pp.Group(pp.delimitedList(QuantifiedVariable)) +
                      pp.Suppress(':') +
                      Formula)
QuantifiedFormula.addParseAction(nest_quantified_formulas(syntax.FORMULA))

QuantifiedVariable << ((FOR_ALL ^ EXISTS) + Variable)
QuantifiedVariable.addParseAction(make_node(syntax.QUANTIFIER))

Term << (Constant ^ Variable ^ Function)

Function << (ConstantSymbol + make_list(Term))
Function.addParseAction(make_node(syntax.FUNCTION))

Predicate << (VariableSymbol + make_list(Term))
Predicate.addParseAction(make_node(syntax.PREDICATE))


# Parsing
# -----------------------------------------------------------------------------

def parse(s: str) -> syntax.Node:
    """Parses First-Order Logic expression into `Node`.

    :param s: The expression to parse.
    :returns: Syntax tree representing the parsed expression.
    :raises ValueError: If the expression does not have proper syntax.
    """

    try:
        tokens = Formula.parseString(s, parseAll=True)
    except pp.ParseException as e:
        raise ValueError(str(e)) from e
    else:
        assert len(tokens) == 1
        rv: syntax.Node = tokens[0]
        return rv.normalize()
