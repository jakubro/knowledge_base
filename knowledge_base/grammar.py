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


def parse(s: str, _allow_private_symbols=False) -> syntax.Node:
    """Parses First-Order Logic expression into `Node`.

    :param s: The expression to parse.
    :returns: Syntax tree representing the parsed expression.
    :raises ValueError: If the expression does not have proper syntax.
    """

    grammar = build_grammar()
    try:
        tokens = grammar.parseString(s, parseAll=True)
    except pp.ParseException as e:
        raise ValueError(str(e)) from e
    else:
        assert len(tokens) == 1
        rv: syntax.Node = tokens[0]

        if not _allow_private_symbols:
            if _has_private_symbols(rv):
                raise ValueError("")  # todo

        return rv.normalize()


def _has_private_symbols(node):
    if not isinstance(node, syntax.Node):
        return False
    elif _is_private_symbol(node):
        return False
    else:
        return any(_has_private_symbols(n)
                   for n in (node.value, *node.children))


def _is_private_symbol(node: syntax.Node) -> bool:
    if (node.is_constant() or node.is_variable()
            or node.is_function() or node.is_predicate()):
        return node.value.startswith('_')
    return False


# noinspection PyPep8Naming
def build_grammar() -> pp.ParserElement:
    # Define each used element as `Forward`. This makes working with the
    # grammar a lot easier.

    Keyword = pp.Forward()
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
    NOT = named(pp.Literal('!'), syntax.NEGATION)

    # Binary operators
    AND = named(pp.Literal('&'), syntax.CONJUNCTION)
    OR = named(pp.Literal('|'), syntax.DISJUNCTION)
    IMPLIES = named(pp.Literal('=>'), syntax.IMPLICATION)
    EQUALS = named(pp.Literal('<=>'), syntax.EQUIVALENCE)

    # Equality
    VALUE_EQUAL = named(pp.Literal('='), syntax.EQUALITY)
    VALUE_NOT_EQUAL = pp.Literal('!=')  # is parsed to NOT(VALUE_EQUAL)

    # Quantifiers
    FOR_ALL = named(pp.Literal('*'), syntax.UNIVERSAL_QUANTIFIER)
    EXISTS = named(pp.Literal('?'), syntax.EXISTENTIAL_QUANTIFIER)

    # Grammar Rules
    # -----------------------------

    Keyword << (NOT | AND | OR | IMPLIES | EQUALS |
                VALUE_EQUAL | VALUE_NOT_EQUAL |
                FOR_ALL | EXISTS)

    # Constants and Functions

    def symbol(init_chars: str) -> pp.ParserElement:
        rv = pp.Combine(pp.Optional('_') +
                        pp.Word(init_chars, pp.alphanums + '_'))
        return ~Keyword + rv

    ConstantSymbol << symbol(pp.alphanums.upper())
    VariableSymbol << symbol(pp.alphanums.lower())

    Constant << ConstantSymbol
    Constant.addParseAction(make_node(syntax.CONSTANT))

    Variable << VariableSymbol
    Variable.addParseAction(make_node(syntax.VARIABLE))

    Function << (ConstantSymbol + make_list(Term))
    Function.addParseAction(make_node(syntax.FUNCTION))

    Predicate << (VariableSymbol + make_list(Term))
    Predicate.addParseAction(make_node(syntax.PREDICATE))

    # Formulas

    Term << (Constant ^ Variable ^ Function)

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

    # Quantified formulas

    QuantifiedFormula << (pp.Group(pp.delimitedList(QuantifiedVariable)) +
                          pp.Suppress(':') +
                          Formula)
    QuantifiedFormula.addParseAction(nest_quantified_formulas(syntax.FORMULA))

    QuantifiedVariable << ((FOR_ALL ^ EXISTS) + Variable)
    QuantifiedVariable.addParseAction(make_node(syntax.QUANTIFIER))

    return Formula


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
