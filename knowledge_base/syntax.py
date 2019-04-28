import copy
import json
from typing import Callable, Dict, Iterator, List, NamedTuple, TypeVar, Union

import yaml
import yaml.representer

T = TypeVar('T')

# Node Types
# -----------------------------------------------------------------------------

# These are the only possible values to appear under `Node.type_`.

CONSTANT = 'Constant'
VARIABLE = 'Variable'
FUNCTION = 'Function'
PREDICATE = 'Predicate'
FORMULA = 'Formula'
QUANTIFIER = 'Quantifier'

# Node Values
# -----------------------------------------------------------------------------

# These are one of the possible values to appear under `Node.value`. Remaining
# possible values are constant and variable symbols.

# Unary operators
NEGATION = 'Not'

# Binary operators
CONJUNCTION = 'And'
DISJUNCTION = 'Or'
IMPLICATION = 'Implies'
EQUIVALENCE = 'Equals'

# Equality
EQUALITY = 'Equality'

# Quantifiers
UNIVERSAL_QUANTIFIER = 'ForAll'
EXISTENTIAL_QUANTIFIER = 'Exists'

# Syntax Tree Node
# -----------------------------------------------------------------------------

T_Value = Union[str, 'Node']
T_Children = List['Node']
T_Subsitution = Dict[str, 'Node']  # replaces term (value) with variable (key)


class Node(NamedTuple):
    """Syntax tree node."""

    #: Type of the node.
    #:
    #: E.g.: constant, variable symbol, ...
    type_: str

    #: Value of the node.
    #:
    #: E.g.: Name of the symbol, name of the operator, ...
    #: If this node is a quantified formula, then value is node which contains
    #: the quantified variable.
    value: T_Value

    #: Children of the node.
    #:
    #: Node has 0-N children.
    children: T_Children

    # Expressions
    # -------------------------------------------------------------------------

    def is_formula(self) -> bool:
        return self.type_ == FORMULA

    # Atomic Expressions
    # -------------------------------------------------------------------------

    def _is_atomic(self) -> bool:
        return (self.is_constant()
                or self.is_variable()
                or self.is_function()
                or self.is_predicate()
                or (self.is_negation() and self.children[0]._is_atomic()))

    def is_constant(self) -> bool:
        return self.type_ == CONSTANT

    def is_variable(self) -> bool:
        return self.type_ == VARIABLE

    def is_function(self) -> bool:
        return self.type_ == FUNCTION

    def is_equality(self) -> bool:
        return (self.is_function()
                and self.value == EQUALITY)

    def is_predicate(self) -> bool:
        return self.type_ == PREDICATE

    # Complex Expressions
    # -------------------------------------------------------------------------

    def negate(self) -> 'Node':
        if self.is_negation():
            children = self.children
            assert len(children) == 1
            return children[0]
        else:
            return Node(type_=FORMULA, value=NEGATION, children=[self])

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

    # Quantified Expressions
    # -------------------------------------------------------------------------

    def is_quantified(self) -> bool:
        value = self.value
        return (self.is_formula()
                and isinstance(value, Node)
                and value.is_quantifier())

    def is_quantifier(self) -> bool:
        return self.type_ == QUANTIFIER

    def get_quantifier_type(self) -> str:
        if self.is_quantified():
            return self.value.get_quantifier_type()
        elif self.is_quantifier():
            return self.value
        else:
            raise TypeError()

    def get_quantified_variable(self) -> 'Node':
        if self.is_quantified():
            return self.value.get_quantified_variable()
        elif self.is_quantifier():
            return self.children[0]
        else:
            raise TypeError()

    def is_universally_quantified(self) -> bool:
        return self.get_quantifier_type() == UNIVERSAL_QUANTIFIER

    def is_existentially_quantified(self) -> bool:
        return self.get_quantifier_type() == EXISTENTIAL_QUANTIFIER

    # Substitutions
    # -------------------------------------------------------------------------

    def occurs_in(self, node: 'Node') -> bool:
        if not self.is_variable():
            raise TypeError()
        if node.is_function():
            return any((c.value == self.value
                        if c.is_variable()
                        else self.occurs_in(c))
                       for c in node.children)
        else:
            return False

    def apply(self, subsitutions: T_Subsitution) -> 'Node':
        if self.is_variable():
            for k, v in subsitutions.items():
                if k == self.value:
                    return v
            return self
        else:
            return Node(type_=self.type_,
                        value=self.value,
                        children=[c.apply(subsitutions)
                                  for c in self.children])

    # CNF
    # -------------------------------------------------------------------------

    def is_cnf(self) -> bool:
        return (self._is_cnf_conjunction()
                or self._is_cnf_disjunction()
                or self._is_atomic())

    def _is_cnf_conjunction(self) -> bool:
        return (self.is_conjunction()
                and all((x._is_cnf_disjunction() or x._is_atomic())
                        for x in self.children))

    def _is_cnf_disjunction(self) -> bool:
        return (self.is_disjunction()
                and all(x._is_atomic()
                        for x in self.children))

    def as_disjunction_clauses(self) -> Iterator['Node']:
        assert self.is_cnf()
        if self.is_conjunction():
            for k in self.children:
                yield from k.as_disjunction_clauses()
        else:
            yield self

    # Normalization
    # -------------------------------------------------------------------------

    def normalize(self) -> 'Node':
        rv = self
        rv = rv._unfold()
        rv = rv._sort()
        return rv

    def denormalize(self) -> 'Node':
        rv = self
        rv = rv._fold()
        return rv

    def _unfold(self) -> 'Node':
        """Flattens nodes of the same type into one node."""

        children = [k._unfold() for k in self.children]

        if self._is_foldable():
            flattened = []
            for k in children:
                if k.type_ == self.type_ and k.value == self.value:
                    flattened.extend(k.children)
                else:
                    flattened.append(k)
            children = flattened

        return Node(type_=self.type_,
                    value=self.value,
                    children=children)

    def _fold(self) -> 'Node':
        children = [k._fold() for k in self.children]

        if self._is_foldable():
            inner = children.pop()
            for k in reversed(children):
                inner = Node(type_=self.type_,
                             value=self.value,
                             children=[k, inner])
            return inner
        else:
            return Node(type_=self.type_,
                        value=self.value,
                        children=children)

    def _is_foldable(self) -> bool:
        return (self.is_conjunction()
                or self.is_disjunction()
                or self.is_implication()
                or self.is_equivalence()
                or self.is_equality())

    def _sort(self) -> 'Node':
        """Sorts nodes lexicographically by symbol names."""

        children = [k._sort() for k in self.children]

        if self._is_sortable():
            children = list(sorted(children))

        return Node(type_=self.type_,
                    value=self.value,
                    children=children)

    def _is_sortable(self) -> bool:
        return (self.is_conjunction()
                or self.is_disjunction()
                or self.is_equivalence()
                or self.is_equality())

    # Serialization
    # -------------------------------------------------------------------------

    def dumps(self,
              compact: bool = False,
              format_: str = 'yaml',
              **kwargs) -> str:
        rv = _dump(self, compact)
        if format_ == 'yaml':
            return yaml.dump(rv, **kwargs, Dumper=_YamlDumper)
        elif format_ == 'json':
            return json.dumps(rv, **kwargs)
        else:
            raise ValueError('format_')

    @classmethod
    def loads(cls, value):
        try:
            # loads JSON as well, since JSON is a subset of YAML
            value = yaml.load(value)
        except AttributeError:
            pass
        rv = _load(value)
        rv = rv.normalize()
        return rv

    # Formatting
    # -------------------------------------------------------------------------

    def __str__(self):
        if self.is_formula():
            if self.is_quantified():
                child = self.children[0]
                return f'{self.value}: {self._enclose(child)}'
            elif self.is_negation():
                child = self.children[0]
                return f'!{self._enclose(child)}'
            else:
                op = f' {self._operator_str()} '
                return op.join(self._enclose(x) for x in self.children)

        elif self.is_quantifier():
            child = self.children[0]
            return f'{self._quantifier_str()}{self._enclose(child)}'

        elif self.is_constant() or self.is_variable():
            return self.value

        elif self.is_function() or self.is_predicate():
            if self.is_equality():
                return ' = '.join(self._enclose(x) for x in self.children)
            else:
                args = ', '.join((self._enclose(x) for x in self.children))
                return f'{self.value}({args})'

        raise ValueError()

    __repr__ = __str__

    def _operator_str(self) -> str:
        """Operator string."""

        if self.is_conjunction():
            return '&'
        elif self.is_disjunction():
            return '|'
        elif self.is_implication():
            return '=>'
        elif self.is_equivalence():
            return '<=>'
        else:
            return self.value

    def _quantifier_str(self) -> str:
        """Quantifier string."""

        if self.is_universally_quantified():
            return '*'
        else:
            assert self.is_existentially_quantified()
            return '?'

    def _enclose(self, child) -> str:
        """Parenthesize the node."""

        return (f'({child})'
                if self._should_enclose(child)
                else str(child))

    def _should_enclose(self, child: 'Node') -> bool:
        """Whether the node should be parenthesized."""

        ops = (NEGATION, CONJUNCTION, DISJUNCTION,
               EQUALITY, EQUIVALENCE, IMPLICATION)

        try:
            return ops.index(self.value) < ops.index(child.value)
        except ValueError:
            return not (child.is_constant()
                        or child.is_variable()
                        or child.is_function()
                        or child.is_predicate())


# Navigation
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


# Builders
# -----------------------------------------------------------------------------

def make_formula(value: T_Value, children: T_Children) -> Node:
    return Node(type_=FORMULA,
                value=value,
                children=children)


def make_quantifier(value: T_Value, name: str) -> Node:
    return Node(type_=QUANTIFIER,
                value=value,
                children=[make_variable(name)])


def make_function(value: str, *args: str) -> Node:
    return Node(type_=FUNCTION,
                value=value,
                children=[make_variable(a) for a in args])


def make_variable(name: str) -> Node:
    return Node(type_=VARIABLE,
                value=name,
                children=[])


# Serialization
# -----------------------------------------------------------------------------

class _YamlDumper(yaml.Dumper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Preserve order of dict keys. (Default implementation sorts them
        # alphabetically. Note that there's no functional reason for doing
        # this, it just feel more easier to me to skim through the tree if I
        # see at first the `Value` and then the `Children`.)
        self.add_representer(
            dict,
            lambda s, data: yaml.representer.SafeRepresenter.represent_dict(
                s,
                data.items()))


T_Deserialized = Union[Node, List[Node], str]
T_Serialized = Union[dict, List[dict], str]


def _dump(node: T_Deserialized, compact: bool) -> T_Serialized:
    """Makes serializable representation of the syntax tree."""

    if isinstance(node, Node):
        value = _dump(node.value, compact)
        children = _dump(node.children, compact)
        if compact and (node.is_constant() or node.is_variable()):
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
        assert isinstance(node, str)
        return node


def _load(node: T_Serialized) -> T_Deserialized:
    """Makes syntax tree from the serialized representation. Inverse of
    `_dump(original, compact=False)`. """

    if isinstance(node, dict):
        assert len(node) == 1
        type_, node = next(iter(node.items()))
        value = _load(node['Value'])
        children = _load(node.get('Children', []))
        return Node(type_=type_,
                    value=value,
                    children=children)

    elif isinstance(node, list):
        return [_load(k) for k in node]

    else:
        assert isinstance(node, str)
        return node
