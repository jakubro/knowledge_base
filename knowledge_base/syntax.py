import copy
import json
from typing import (
    Callable, Dict, FrozenSet, List, NamedTuple, Tuple, TypeVar, Union,
)

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

# Quantifiers
UNIVERSAL_QUANTIFIER = 'ForAll'
EXISTENTIAL_QUANTIFIER = 'Exists'

# Equality (Encoded as a predicate with `value` set to this constant - that's
# the reason for the leading underscore.)
EQUALITY = '_Equality'

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
        node = self._sort()
        return hash((node.type_, node.value, tuple(node.children)))

    # Terms, Atoms and Literals
    # -------------------------------------------------------------------------

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

        return (self.is_predicate()
                and self.value == EQUALITY)

    def is_term(self) -> bool:
        """:returns: Whether the node is a term."""

        return ((self.is_constant()
                 or self.is_variable()
                 or self.is_function())
                and all(k.is_term() for k in self.children))

    def is_atom(self) -> bool:
        """:returns: Whether the node is an atom."""

        return (self.is_predicate()
                and all(k.is_term() for k in self.children))

    def is_literal(self) -> bool:
        """:returns: Whether the node is a literal."""

        return (self.is_atom()
                or (self.is_negation() and self.children[0].is_atom()))

    def is_formula(self):
        """:returns: Whether the node is a well-formed formula."""

        if self.is_atom():
            return True
        elif (self.is_negation()
              or self.is_conjunction()
              or self.is_disjunction()
              or self.is_implication()
              or self.is_equivalence()
              or self.is_quantified()):
            return all(k.is_formula() for k in self.children)
        else:
            return False

    # Complex Formulas
    # -------------------------------------------------------------------------

    def _is_formula(self) -> bool:
        return self.type_ == FORMULA

    def is_negation(self) -> bool:
        """:returns: Whether the node is negated."""

        return (self._is_formula()
                and self.value == NEGATION)

    def negate(self) -> 'Node':
        """Negates the expression."""

        if self.is_negation():
            children = self.children
            assert len(children) == 1
            return children[0]
        else:
            return Node(type_=FORMULA, value=NEGATION, children=[self])

    def is_conjunction(self) -> bool:
        """:returns: Whether the node is a conjunction."""

        return (self._is_formula()
                and self.value == CONJUNCTION)

    def is_disjunction(self) -> bool:
        """:returns: Whether the node is a disjunction."""

        return (self._is_formula()
                and self.value == DISJUNCTION)

    def is_implication(self) -> bool:
        """:returns: Whether the node is an implication."""

        return (self._is_formula()
                and self.value == IMPLICATION)

    def is_equivalence(self) -> bool:
        """:returns: Whether the node is an equivalence."""

        return (self._is_formula()
                and self.value == EQUIVALENCE)

    # Quantified Formulas
    # -------------------------------------------------------------------------

    def is_quantified(self) -> bool:
        """:returns: Whether the node is a quantified formula."""

        value = self.value
        return (self._is_formula()
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

    def unify(self, node: 'Node') -> T_Substitution:
        from knowledge_base import unification
        return unification.unify(self, node)

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
            rv = Node(type_=self.type_,
                      value=(self.value.apply(substitutions)
                             if isinstance(self.value, Node)
                             else self.value),
                      children=[c.apply(substitutions)
                                for c in self.children])
            rv = rv._sort()
            return rv

    def replace(self, substitutions: T_Substitution) -> 'Node':
        rv = self

        if (self.is_constant() or self.is_variable()
                or self.is_function() or self.is_predicate()):
            for k, v in substitutions.items():
                if k == self.value:
                    rv = v.replace(substitutions)
                    break

        value = rv.value
        rv = Node(type_=rv.type_,
                  value=(value.replace(substitutions)
                         if isinstance(value, Node)
                         else value),
                  children=[c.replace(substitutions)
                            for c in rv.children])
        rv = rv._sort()
        return rv

    def replace2(self: 'Node', r: 'Node', t: 'Node') -> 'Node':
        # todo: proper name

        rv = self

        if (self.is_constant() or self.is_variable()
                or self.is_function() or self.is_predicate()):
            if r == self:
                rv = t

        value = rv.value
        rv = Node(type_=rv.type_,
                  value=(value.replace2(r, t)
                         if isinstance(value, Node)
                         else value),
                  children=[c.replace2(r, t)
                            for c in rv.children])
        rv = rv._sort()
        return rv

    # CNF
    # -------------------------------------------------------------------------

    def to_cnf(self) -> Tuple['Node', T_Substitution]:
        from knowledge_base import cnf
        return cnf.convert_to_cnf(self)

    def is_cnf(self) -> bool:
        """:returns: Whether the node is in CNF."""

        return self.is_formula() and (self._is_cnf_conjunction()
                                      or self._is_cnf_disjunction()
                                      or self.is_literal())

    def _is_cnf_conjunction(self) -> bool:
        return (self.is_conjunction()
                and all((k._is_cnf_disjunction()
                         or k.is_literal())
                        for k in self.children))

    def _is_cnf_disjunction(self) -> bool:
        return (self.is_disjunction()
                and all(k.is_literal()
                        for k in self.children))

    def to_clause_form(self) -> FrozenSet[FrozenSet['Node']]:
        assert self.is_cnf()

        if self.is_conjunction():
            return frozenset({k._clause_form_disjunction()
                              for k in self.children})
        else:
            return frozenset({self._clause_form_disjunction()})

    def _clause_form_disjunction(self) -> FrozenSet['Node']:
        if self.is_disjunction():
            return frozenset({*self.children})
        else:
            return frozenset({self})

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

    def _sort_key(self) -> tuple:
        if self.is_negation():
            return self.children[0]._sort_key()

        rv = [self.type_]
        if isinstance(self.value, str):
            rv.append(self.value)
        else:
            rv.extend(self.value._sort_key())
        rv.extend((k._sort_key() for k in self.children))
        return tuple(rv)

    # Evaluation
    # -------------------------------------------------------------------------

    def eval(self, **kwargs):
        if self.is_equality():
            a, b = (k.eval(**kwargs) for k in self.children)
            return a == b

        elif self.is_function() or self.is_predicate():
            # todo: move the default value into truth_table
            #  (i.e. first collect function/predicate symbols)
            func = kwargs.get(self.value, lambda *func_args: all(func_args))
            args = (k.eval(**kwargs) for k in self.children)
            return func(*args)

        elif self.is_quantified() or self.is_quantifier():
            return self.children[0].eval(**kwargs)

        elif self.is_variable() or self.is_constant():
            return kwargs[self.value]

        elif self.is_negation():
            return not self.children[0].eval(**kwargs)

        elif self.is_conjunction():
            return all(k.eval(**kwargs) for k in self.children)

        elif self.is_disjunction():
            return any(k.eval(**kwargs) for k in self.children)

        elif self.is_implication():
            fd = self._fold()
            a, b = (k.eval(**kwargs) for k in fd.children)
            return not a or b

        else:
            assert self.is_equivalence()
            fd = self._fold()
            a, b = (k.eval(**kwargs) for k in fd.children)
            return (not a or b) and (a or not b)

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
        t = self._sort()

        if t.is_constant() or t.is_variable():
            return t.value

        elif t.is_equality():
            return t._infix_str(' = ')

        elif t.is_function() or t.is_predicate():
            body = t._infix_str(', ')
            return f'{t.value}({body})'

        elif t.is_negation():
            child = t.children[0]
            return f'!{t._enclose(child)}'

        elif t.is_quantified():
            child = t.children[0]
            return f'{t.value}: {t._enclose(child)}'

        elif t.is_quantifier():
            child = t.children[0]
            return f'{t._quantifier_str()}{t._enclose(child)}'

        else:
            assert t._is_formula()
            op = f' {t._operator_str()} '
            return t._infix_str(op)

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
                        or child.is_function()  # equality handled via `ops`
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


def dumps(value: Union[Node, List[Node]],
          compact: bool = False,
          format_: str = 'yaml',
          **kwargs) -> str:

    rv = _dump(value, compact)
    if format_ == 'yaml':
        return yaml.dump(rv, **kwargs, Dumper=_YamlDumper)
    elif format_ == 'json':
        return json.dumps(rv, **kwargs)
    else:
        raise ValueError("Provided 'format_' is not valid")


def loads(value: str) -> Union[Node, List[Node]]:
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
    if isinstance(rv, Node):
        return rv.normalize()
    else:
        assert isinstance(rv, list)
        return [k.normalize() for k in rv]


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
