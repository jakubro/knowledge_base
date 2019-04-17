import copy
from typing import Callable, List, NamedTuple, TypeVar, Union

import yaml
import yaml.representer

T = TypeVar('T')

# Types
# -----------------------------------------------------------------------------

FORMULA = 'Formula'
QUANTIFIER = 'Quantifier'  # defines quantified variable
VARIABLE = 'Variable'  # variable (quantified) or a constant (not-quantified)
FUNCTION = 'Function'  # predicate or function

# Values
# -----------------------------------------------------------------------------

# Equality
EQUALITY = 'Equality'  # 2-ary infix function

# Unary operators
NEGATION = 'Not'

# Binary operators
CONJUNCTION = 'And'
DISJUNCTION = 'Or'
IMPLICATION = 'Implies'
EQUIVALENCE = 'Equals'

# Quantifiers
UNIVERSAL_QUANTIFIER = 'ForAll'
EXISTENTIAL_QUANTIFIER = 'Exists'

# Syntax Tree Node
# -----------------------------------------------------------------------------

T_Value = Union[str, 'Node']
T_Children = List['Node']


class Node(NamedTuple):
    type_: str
    value: T_Value
    children: T_Children

    def negate(self) -> 'Node':
        if self.is_negation():
            children = self.children
            assert len(children) == 1
            return children[0]
        else:
            return Node(type_=FORMULA, value=NEGATION, children=[self])

    def is_formula(self) -> bool:
        return self.type_ == FORMULA

    def is_quantified(self) -> bool:
        value = self.value
        return (self.is_formula()
                and isinstance(value, Node)
                and value.is_quantifier())

    def is_negation(self) -> bool:
        return (self.is_formula()
                and self.value == NEGATION)

    def is_conjunction(self) -> bool:
        return (self.is_formula()
                and self.value == CONJUNCTION)

    def is_disjunction(self) -> bool:
        return (self.is_formula()
                and self.value == DISJUNCTION)

    def is_implication(self) -> bool:
        return (self.is_formula()
                and self.value == IMPLICATION)

    def is_equivalence(self) -> bool:
        return (self.is_formula()
                and self.value == EQUIVALENCE)

    def is_quantifier(self) -> bool:
        return self.type_ == QUANTIFIER

    def get_quantifier_type(self) -> str:
        if self.is_quantified():
            return self.value.get_quantifier_type()
        elif self.is_quantifier():
            return self.value
        raise TypeError()

    def get_quantified_variable(self) -> 'Node':
        if self.is_quantified():
            return self.value.get_quantified_variable()
        elif self.is_quantifier():
            children = self.children
            assert len(children) == 1
            return children[0]
        else:
            raise TypeError()

    def is_universal_quantifier(self) -> bool:
        return (self.is_quantifier()
                and self.value == UNIVERSAL_QUANTIFIER)

    def is_existential_quantifier(self) -> bool:
        return (self.is_quantifier()
                and self.value == EXISTENTIAL_QUANTIFIER)

    def is_variable(self) -> bool:
        return self.type_ == VARIABLE

    def get_variable_name(self) -> str:
        if not self.is_variable():
            raise TypeError()
        return self.value

    def is_function(self) -> bool:
        return self.type_ == FUNCTION

    def is_equality(self) -> bool:
        return (self.is_function()
                and self.value == EQUALITY)

    def dumps(self, compact: bool = False) -> str:
        data = _dump(self, compact)
        return yaml.dump(data, Dumper=_YamlDumper)

    def __repr__(self):
        return self.dumps(compact=True)

    def __str__(self):
        if self.is_formula():
            if self.is_quantified():
                child = self.children[0]
                return f'{self.value}: {self._enclose(child)}'
            elif self.is_negation():
                child = self.children[0]
                return f'!{self._enclose(child)}'
            else:
                a, b = self.children
                return (f'{self._enclose(a)} '
                        f'{self._get_operator_str()} '
                        f'{self._enclose(b)}')

        elif self.is_quantifier():
            child = self.children[0]
            return f'{self._get_quantifier_str()}{self._enclose(child)}'

        elif self.is_variable():
            return self.value

        elif self.is_function():
            if self.is_equality():
                a, b = self.children
                return f'{self._enclose(a)} = {self._enclose(b)}'
            else:
                args = ', '.join((self._enclose(x) for x in self.children))
                return f'{self.value}({args})'

        raise ValueError()

    def _get_operator_str(self) -> str:
        """Operator string."""

        if self.is_conjunction():
            return '&'
        elif self.is_disjunction():
            return '|'
        elif self.is_implication():
            return '=>'
        else:
            assert self.is_equivalence()
            return '<=>'

    def _get_quantifier_str(self) -> str:
        """Quantifier string."""

        if self.is_universal_quantifier():
            return '*'
        else:
            assert self.is_existential_quantifier()
            return '?'

    def _enclose(self, node) -> str:
        """Parenthesize the node."""

        return f'({node})' if self._should_enclose(node) else str(node)

    def _should_enclose(self, node) -> bool:
        """Whether the node should be parenthesized."""

        return (isinstance(node, Node)
                and self.is_formula()
                and len(self.children) == 2
                and node.value != self.value
                and (node.is_formula() or node.is_equality()))


# Syntax Tree Navigation
# -----------------------------------------------------------------------------

def walk(node: T,
         state: 'WalkState',
         func: Callable[[Node, 'WalkState'], Node]) -> T:
    """Invokes `func` on each node and then recurses into node's value and
    children.

    :param node: The node to traverse.
    :param state: Traversing state.
    :param func: Function to apply to each node traversed. (This function
        returns the same or a modified node.)
    :returns: Traversed node.
    """

    if isinstance(node, Node):
        while True:
            prev = node
            node = func(node, state)
            value = walk(node.value, state, func)
            children = walk(node.children, state, func)
            node = Node(type_=node.type_, value=value, children=children)
            if node == prev:
                return prev

    elif isinstance(node, list):
        rv = []
        for child in node:
            ctx = state.copy()
            child = walk(child, ctx, func)
            rv.append(child)
        return rv

    else:
        return node


class WalkState(NamedTuple):
    #: Global dictionary.
    context: dict

    #: List maintained only within parent-child hierarchy.
    stack: list

    def copy(self):
        return WalkState(context=self.context,
                         stack=copy.deepcopy(self.stack))

    @classmethod
    def make(cls, state: 'WalkState' = None) -> 'WalkState':
        return (state.copy()
                if state
                else WalkState(context={}, stack=[]))


# Syntax Tree Builders
# -----------------------------------------------------------------------------

def make_formula(value: T_Value, children: T_Children) -> Node:
    return Node(type_=FORMULA,
                value=value,
                children=children)


def make_quantifier(value: T_Value, name: str) -> Node:
    return Node(type_=QUANTIFIER,
                value=value,
                children=[make_variable(name)])


def make_function(value: str, args: List[str]) -> Node:
    return Node(type_=FUNCTION,
                value=value,
                children=[make_variable(a) for a in args])


def make_variable(name: str) -> Node:
    return Node(type_=VARIABLE,
                value=name,
                children=[])


# Helpers
# -----------------------------------------------------------------------------

class _YamlDumper(yaml.Dumper):
    pass


_YamlDumper.add_representer(
    dict,
    lambda self, data: yaml.representer.SafeRepresenter.represent_dict(
        self,
        data.items()))


def _dump(node, compact: bool = False):
    if isinstance(node, Node):
        value = _dump(node.value, compact)
        children = _dump(node.children, compact)
        if compact and node.is_variable():
            return value
        rv = {'Value': value}
        if children:
            rv['Children'] = children
        return {node.type_: rv}
    elif isinstance(node, list):
        return [_dump(k, compact) for k in node]
    elif isinstance(node, dict):
        return {
            _dump(k, compact): _dump(v, compact)
            for k, v in node.items()
        }
    else:
        return node
