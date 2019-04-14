from typing import List, TypeVar, Union

import syntax

T = TypeVar('T')
T_Value = Union[str, syntax.Node]
T_Children = List[syntax.Node]


class KnowledgeBase:
    def __init__(self):
        self._axioms = []
        self._lemmas = []
        self._facts = []

    def add_axiom(self, formula):
        self._axioms.append(formula)

    def add_lemma(self, formula) -> bool:
        rv = self.verify(formula)
        if rv:
            self._lemmas.append(formula)
        return rv

    def verify(self, formula) -> bool:
        raise NotImplementedError()

    def get_binding_list(self, formula):
        raise NotImplementedError()
