"""First order logic grammar."""

import pyparsing as pp


# Helpers
# -----------------------------------------------------------------------------

def make_list(expr,
              optional=True, opener='(', closer=')',
              delim=', ', combine=False, ):
    inner = pp.delimitedList(expr, delim=delim, combine=combine)
    outer = pp.Optional(inner) if optional else inner

    return (pp.Suppress(opener) +
            outer +
            pp.Suppress(closer))


def rename(expr, replacement):
    return expr.addParseAction(pp.replaceWith(replacement))


# Nodes
# -----------------------------------------------------------------------------

class SymbolNode:
    def __init__(self, tokens):
        self.value = tokens[0]

    def __repr__(self):
        return str(self.value)


class UnaryOperatorNode:
    def __init__(self, tokens):
        self.operator = tokens[0][0]
        self.operands = [tokens[0][1]]

    def __repr__(self):
        return f"{self.operator}({self.operands})"


class BinaryOperatorNode:
    def __init__(self, tokens):
        self.operator = tokens[0][1]
        self.operands = tokens[0][::2]

    def __repr__(self):
        return f"{self.operator}({self.operands})"


class BoundFormulaNode:
    def __init__(self, tokens):
        self.variables = tokens[0]
        self.formula = tokens[1]

    def __repr__(self):
        return f"{self.variables}: ({self.formula})"


class BoundVariableNode:
    def __init__(self, tokens):
        self.quantifier = tokens[0]
        self.variable = tokens[1]

    def __repr__(self):
        return f"{self.quantifier}({self.variable})"


class FunctionalNode:
    def __init__(self, tokens):
        self.name = tokens[0]
        self.args = tokens[1]

    def __repr__(self):
        return f"{self.name}({self.args})"


# Grammar
# -----------------------------------------------------------------------------

Symbol = pp.Forward()
Formula = pp.Forward()
BoundFormula = pp.Forward()
BoundVariable = pp.Forward()
Term = pp.Forward()
Functional = pp.Forward()

# Keywords

NOT = rename(pp.CaselessKeyword('Not') ^ pp.Literal('!'), 'Not')
VALEQ = rename(pp.CaselessKeyword('='), 'ValueEqual')
VALNOTEQ = rename(pp.Literal('!='), 'ValueNotEqual')
AND = rename(pp.CaselessKeyword('And') ^ pp.Literal('&'), 'And')
OR = rename(pp.CaselessKeyword('Or') ^ pp.Literal('|'), 'Or')
IMPLIES = rename(pp.CaselessKeyword('Implies') ^ pp.Literal('=>'), 'Implies')
EQUALS = rename(pp.CaselessKeyword('Equals') ^ pp.Literal('<=>'), 'Equals')
FORALL = rename(pp.CaselessKeyword('ForAll') ^ pp.Literal('*'), 'ForAll')
EXISTS = rename(pp.CaselessKeyword('Exists') ^ pp.Literal('?'), 'Exists')

KEYWORDS = (NOT | VALEQ | VALNOTEQ |
            AND | OR | IMPLIES | EQUALS |
            FORALL | EXISTS)

# Grammar

Symbol << (~KEYWORDS + pp.Word(pp.alphanums)).setParseAction(SymbolNode)

Formula << pp.infixNotation((Term ^ BoundFormula), [
    ((VALEQ ^ VALNOTEQ), 2, pp.opAssoc.LEFT, BinaryOperatorNode),
    (NOT, 1, pp.opAssoc.RIGHT, UnaryOperatorNode),
    (AND, 2, pp.opAssoc.LEFT, BinaryOperatorNode),
    (OR, 2, pp.opAssoc.LEFT, BinaryOperatorNode),
    (EQUALS, 2, pp.opAssoc.LEFT, BinaryOperatorNode),
    (IMPLIES, 2, pp.opAssoc.LEFT, BinaryOperatorNode),
])

BoundFormula << (pp.Group(pp.delimitedList(BoundVariable)) +
                 pp.Suppress(':') +
                 Formula).setParseAction(BoundFormulaNode)

BoundVariable << ((FORALL ^ EXISTS) + Symbol).setParseAction(BoundVariableNode)

Term << (Functional ^ Symbol)

Functional << (Symbol +
               pp.Group(make_list(Term))).setParseAction(FunctionalNode)
