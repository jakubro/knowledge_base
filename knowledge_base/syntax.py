from typing import List, NamedTuple, Tuple, Union

import yaml
import yaml.representer

# Types
# -----------------------------

FORMULA = 'Formula'
QUANTIFIER = 'Quantifier'  # defines quantified variable
VARIABLE = 'Variable'  # variable (quantified) or a constant (not-quantified)
FUNCTIONAL = 'Functional'

# Values
# -----------------------------

# Truth literals
TRUE = 'True'
FALSE = 'False'

# Equality
EQUALITY = 'Equality'

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


# Nodes
# -----------------------------

class Node(NamedTuple):
    type_: str
    value: Union[str, 'Node']
    children: List['Node']

    def dumps(self, compact: bool = False) -> str:
        data = _dump(self, compact)
        return yaml.dump(data, Dumper=_YamlDumper)

    def negate(self) -> 'Node':
        if self.value == NEGATION:
            children = self.children
            assert len(children) == 1
            return children[0]
        else:
            return Node(type_=FORMULA, value=NEGATION, children=[self])

    def get_quantifier(self) -> Tuple[str, str]:
        type_ = self.type_
        value = self.value
        if type_ == FORMULA and isinstance(value, Node):
            return value.as_quantifier()
        raise ValueError()

    def as_quantifier(self) -> Tuple[str, str]:
        if self.type_ == QUANTIFIER:
            value = self.value
            children = self.children
            assert len(children) == 1

            child = children[0]
            assert child.type_ == VARIABLE

            name = child.value
            return value, name
        raise ValueError()

    def __repr__(self):
        return self.dumps(compact=True)

    def __str__(self):
        type_ = self.type_
        value = self.value
        children = self.children

        # parenthesis treatment
        lpar, rpar = '', ''
        if ((type_ == FORMULA or (type_ == FUNCTIONAL and value == EQUALITY))
                and children[0].type_ == FORMULA):
            lpar, rpar = '(', ')'

        if type_ == FORMULA:
            if isinstance(value, Node):
                return f'{lpar}{value}: {children[0]}{rpar}'
            elif value == NEGATION:
                return f'!{lpar}{children[0]}{rpar}'
            else:
                if value == CONJUNCTION:
                    value = '&'
                elif value == DISJUNCTION:
                    value = '|'
                elif value == IMPLICATION:
                    value = '=>'
                elif value == EQUIVALENCE:
                    value = '<=>'
                return f'{lpar}{children[0]} {value} {children[1]}{rpar}'

        elif type_ == QUANTIFIER:
            if value == UNIVERSAL_QUANTIFIER:
                value = '*'
            elif value == EXISTENTIAL_QUANTIFIER:
                value = '?'
            return f'{lpar}{value}{children[0]}{rpar}'

        elif type_ == VARIABLE:
            return f'{lpar}{value}{rpar}'

        elif type_ == FUNCTIONAL:
            if value == EQUALITY:
                return f'{lpar}{children[0]} = {children[1]}{rpar}'
            else:
                value = str(value)
                args = (str(x) for x in self.children)
                return f'{lpar}{value}({", ".join(args)}){rpar}'

        raise ValueError()


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

        if compact and node.type_ == VARIABLE:
            assert not children
            return value

        rv = {'Value': value, 'Children': children}
        if not children:
            del rv['Children']
        return {node.type_: rv}
    elif isinstance(node, list):
        return [_dump(k, compact) for k in node]
    elif isinstance(node, dict):
        return {_dump(k, compact): _dump(v, compact) for k, v in node.items()}
    else:
        return node
