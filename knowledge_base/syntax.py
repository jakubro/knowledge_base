import copy
import json
from typing import Callable, Dict, List, NamedTuple, TypeVar, Union

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
T_Substitution = Dict[str, 'Node']  # replaces term (value) with variable (key)


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

    def __hash__(self, *args, **kwargs):
        return hash((self.type_,
                     self.value,
                     tuple(self.children)))

    # Expressions
    # -------------------------------------------------------------------------

    def is_formula(self) -> bool:
        """:returns: Whether the node is a formula."""

        return self.type_ == FORMULA

    def is_term(self) -> bool:
        """:returns: Whether the node is a term."""

        return self.is_constant() or self.is_variable() or self.is_function()

    # Atomic Expressions
    # -------------------------------------------------------------------------

    def is_atomic(self) -> bool:
        return (self.is_constant()
                or self.is_variable()
                or self.is_function()
                or self.is_predicate()
                or (self.is_negation() and self.children[0].is_atomic()))

    def is_constant(self) -> bool:
        """:returns: Whether the node is a constant."""

        return self.type_ == CONSTANT

    def is_variable(self) -> bool:
        """:returns: Whether the node is a variable."""

        return self.type_ == VARIABLE

    def is_function(self) -> bool:
        """:returns: Whether the node is a function."""

        return self.type_ == FUNCTION

    def is_predicate(self) -> bool:
        """:returns: Whether the node is a predicate."""

        return self.type_ == PREDICATE

    def is_equality(self) -> bool:
        """:returns: Whether the node is an equality."""

        return (self.is_function()
                and self.value == EQUALITY)

    # Complex Expressions
    # -------------------------------------------------------------------------

    def negate(self) -> 'Node':
        """Negates the expression."""

        if self.is_negation():
            children = self.children
            assert len(children) == 1
            return children[0]
        else:
            return Node(type_=FORMULA, value=NEGATION, children=[self])

    def is_negation(self) -> bool:
        """:returns: Whether the node is negated."""

        return (self.is_formula()
                and self.value == NEGATION)

    def is_conjunction(self) -> bool:
        """:returns: Whether the node is a conjunction."""

        return (self.is_formula()
                and self.value == CONJUNCTION)

    def is_disjunction(self) -> bool:
        """:returns: Whether the node is a disjunction."""

        return (self.is_formula()
                and self.value == DISJUNCTION)

    def is_implication(self) -> bool:
        """:returns: Whether the node is an implication."""

        return (self.is_formula()
                and self.value == IMPLICATION)

    def is_equivalence(self) -> bool:
        """:returns: Whether the node is an equivalence."""

        return (self.is_formula()
                and self.value == EQUIVALENCE)

    # Quantified Expressions
    # -------------------------------------------------------------------------

    def is_quantified(self) -> bool:
        """:returns: Whether the node is a quantified formula."""

        value = self.value
        return (self.is_formula()
                and isinstance(value, Node)
                and value.is_quantifier())

    def is_quantifier(self) -> bool:
        """:returns: Whether the node is a quantifier."""

        return self.type_ == QUANTIFIER

    def get_quantifier_type(self) -> str:
        """
        :returns: Type of the quantifier. Either `UNIVERSAL_QUANTIFIER` or
        `EXISTENTIAL_QUANTIFIER`.
        :raises TypeError: If the node is not a quantified formula, neither
        quantifier.
        """

        if self.is_quantified():
            return self.value.get_quantifier_type()
        elif self.is_quantifier():
            return self.value
        else:
            raise TypeError("Node is not a quantifier, "
                            "neither a quantified formula")

    def get_quantified_variable(self) -> 'Node':
        """
        :returns: Node with quantified variable.
        :raises TypeError: If the node is not a quantified formula, neither
        quantifier.
        """

        if self.is_quantified():
            return self.value.get_quantified_variable()
        elif self.is_quantifier():
            return self.children[0]
        else:
            raise TypeError("Node is not a quantifier, "
                            "neither a quantified formula")

    # Substitutions
    # -------------------------------------------------------------------------

    def occurs_in(self, node: 'Node') -> bool:
        """
        :returns: Whether the provided node occurs as a function argument
        inside this node.
        :raises TypeError: If the provided node is not a variable.
        """

        if not self.is_variable():
            raise TypeError("Node is not a variable")

        if node.is_function() or node.is_predicate():
            for c in node.children:
                if c.is_variable() and c.value == self.value:
                    return True
        return any(self.occurs_in(c) for c in node.children)

    def apply(self, substitutions: T_Substitution) -> 'Node':
        """Applies substitutions to the node.

        :param substitutions: Substitutions to apply.
        :returns: Transformed node.
        """

        if self.is_variable():
            for k, v in substitutions.items():
                if k == self.value:
                    return v
            return self
        else:
            return Node(type_=self.type_,
                        value=self.value,
                        children=[c.apply(substitutions)
                                  for c in self.children])

    # CNF
    # -------------------------------------------------------------------------

    def is_cnf(self) -> bool:
        """:returns: Whether the node is in CNF."""

        return (self._is_cnf_conjunction()
                or self._is_cnf_disjunction()
                or self.is_atomic())

    def _is_cnf_conjunction(self) -> bool:
        return (self.is_conjunction()
                and all((x._is_cnf_disjunction() or x.is_atomic())
                        for x in self.children))

    def _is_cnf_disjunction(self) -> bool:
        return (self.is_disjunction()
                and all(x.is_atomic()
                        for x in self.children))

    # Normalization
    # -------------------------------------------------------------------------

    def normalize(self) -> 'Node':
        """Produces normalized expression. (Useful for comparing nodes.)"""

        rv = self
        rv = rv._unfold()
        rv = rv._sort()
        return rv

    def denormalize(self) -> 'Node':
        """Folds the expression. (Useful for traversing the syntax tree.)"""

        rv = self
        rv = rv._fold()
        return rv

    def _unfold(self) -> 'Node':
        """Flattens nodes of the same type into one node.

        For example this node:

        {
            'Formula': {
                'Value': 'And',
                'Children': [
                    {'Variable': {'Value': 'a'}},
                    {
                        'Formula': {
                            'Value': 'And',
                            'Children': [{'Variable': {'Value': 'b'}},
                                         {'Variable': {'Value': 'c'}}]
                        }
                    }]
            }
        }

        becomes:

        {
            'Formula': {
                'Value': 'And',
                'Children': [{'Variable': {'Value': 'a'}},
                             {'Variable': {'Value': 'b'}},
                             {'Variable': {'Value': 'c'}}]
            }
        }

        """

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
        """Inverse of `_unfold`."""

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

    def _sort_key(self) -> tuple:
        rv = [self.type_]
        if isinstance(self.value, str):
            rv.append(self.value)
        else:
            rv.extend(self.value._sort_key())
        rv.extend((k._sort_key() for k in self.children))
        return tuple(rv)

    def _sort(self) -> 'Node':
        """Sorts nodes lexicographically in a stable way."""

        children = [k._sort() for k in self.children]

        if self._is_sortable():
            # noinspection PyProtectedMember
            # justification: s is a Node
            key = lambda s: s._sort_key()
            children = list(sorted(children, key=key))

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
        """Serializes node.

        :param compact: Whether to produce more compact form.
        :param format_: Format to use. Either `yaml` or `json`.
        :param kwargs: Additional keyword arguments are passed to YAML or JSON
        serializer.
        :returns: Serialized node.
        """

        rv = _dump(self, compact)
        if format_ == 'yaml':
            return yaml.dump(rv, **kwargs, Dumper=_YamlDumper)
        elif format_ == 'json':
            return json.dumps(rv, **kwargs)
        else:
            raise ValueError("Provided 'format_' is not valid")

    @classmethod
    def loads(cls, value) -> 'Node':
        """Deserializes node.

        :param value: Serialized node. (Must not be in a compact form.)
        :returns: Deserialized node.
        """

        try:
            # loads JSON as well, since JSON is a subset of YAML
            value = yaml.load(value, Loader=yaml.SafeLoader)
        except AttributeError:
            pass
        rv = _load(value)
        rv = rv.normalize()
        return rv

    # Formatting
    # -------------------------------------------------------------------------

    def __str__(self):
        if self.is_constant() or self.is_variable():
            return self.value

        elif self.is_equality():
            return self._infix_str(' = ')

        elif self.is_function() or self.is_predicate():
            body = self._infix_str(', ')
            return f'{self.value}({body})'

        elif self.is_negation():
            child = self.children[0]
            return f'!{self._enclose(child)}'

        elif self.is_quantified():
            child = self.children[0]
            return f'{self.value}: {self._enclose(child)}'

        elif self.is_quantifier():
            child = self.children[0]
            return f'{self._quantifier_str()}{self._enclose(child)}'

        else:
            assert self.is_formula()
            op = f' {self._operator_str()} '
            return self._infix_str(op)

    __repr__ = __str__

    def _infix_str(self, op: str) -> str:
        return op.join(self._enclose(x) for x in self.children)

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

        qtype = self.get_quantifier_type()
        if qtype == UNIVERSAL_QUANTIFIER:
            return '*'
        else:
            assert qtype == EXISTENTIAL_QUANTIFIER
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
            return not ((self.is_quantified() and child.is_quantified())
                        or child.is_constant()
                        or child.is_variable()
                        or child.is_function()
                        or child.is_predicate())


# Navigation
# -----------------------------------------------------------------------------

def walk(node: T,
         func: Callable[[Node, 'WalkState'], Node],
         state: 'WalkState' = None) -> T:
    """Invokes `func` on each node and then recurses into node's value and
    children.

    :param node: The node to traverse.
    :param state: Traversing state.
    :param func: Function to apply to each node traversed. (This function
        returns the same or a modified node.)
    :returns: Traversed node.
    """

    if state is None:
        state = WalkState.make()

    if isinstance(node, Node):
        while True:
            prev = node
            node = func(node, state)
            value = walk(node.value, func, state)
            children = walk(node.children, func, state)
            node = Node(type_=node.type_, value=value, children=children)
            if node == prev:
                return prev

    elif isinstance(node, list):
        rv = []
        for child in node:
            ctx = state.copy()
            child = walk(child, func, ctx)
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

def make_constant(name: str) -> Node:
    return Node(type_=CONSTANT,
                value=name,
                children=[])


def make_variable(name: str) -> Node:
    return Node(type_=VARIABLE,
                value=name,
                children=[])


def make_function(value: str, *args: str) -> Node:
    return Node(type_=FUNCTION,
                value=value,
                children=[make_variable(a) for a in args])


def make_formula(value: T_Value, children: T_Children) -> Node:
    return Node(type_=FORMULA,
                value=value,
                children=children)


def make_quantifier(value: T_Value, name: str) -> Node:
    return Node(type_=QUANTIFIER,
                value=value,
                children=[make_variable(name)])


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
