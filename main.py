import argparse
import logging
from typing import List

import pyparsing as pp

from knowledge_base import grammar, inference, syntax

pp.ParserElement.enablePackrat()


class KnowledgeBase:
    def __init__(self, facts: List[syntax.Node] = None):
        self._facts = facts or []

    @property
    def facts(self) -> List[syntax.Node]:
        return self._facts

    def _add_fact(self, f: syntax.Node):
        self._facts.append(f)

    def add_axiom(self, f: syntax.Node):
        self._add_fact(f)

    def add_lemma(self, f: syntax.Node) -> bool:
        if self.prove(f):
            self._add_fact(f)
            return True
        else:
            return False

    def prove(self, f: syntax.Node) -> bool:
        return inference.infer(self._facts, f) is not None

    def query(self, f: syntax.Node) -> syntax.T_Substitution:
        return inference.infer(self._facts, f)


def main():
    parser = argparse.ArgumentParser(description="Knowledge base")
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help="Be verbose.")
    parser.add_argument(
        '-vv', '--debug', action='store_true',
        help="Be even more verbose.")
    args = parser.parse_args()
    setup_logging(args)

    print("Knowledge base")
    print()
    usage()

    kb = KnowledgeBase()
    while True:
        print(">> ", end="")
        v = input()
        command, *rest = v.split(maxsplit=1)

        command = command.lower()
        rest = rest[0].strip() if rest else None

        if command == 'list':
            list_content(kb)
        elif command == 'axiom':
            add_axiom(kb, rest)
        elif command == 'lemma':
            add_lemma(kb, rest)
        elif command == 'prove':
            prove(kb, rest)
        elif command == 'query':
            query(kb, rest)
        else:
            usage()


def usage():
    print("Usage: ")
    print("""
        help                Show this help screen
        list                List content of the knowledge base
        axiom <formula>     Add axiom to the knowledge base
        lemma <formula>     Prove and add lemma to the knowledge base
        prove <formula>     Prove formula
        query <formula>     Shows binding list that satisfies the formula
    """)


def list_content(kb: KnowledgeBase) -> None:
    for f in kb.facts:
        print(f)


def add_axiom(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax")
        return

    kb.add_axiom(f)
    print("Axiom was added to the knowledge base.")


def add_lemma(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax")
        return

    rv = kb.add_lemma(f)
    if rv:
        print(f"Lemma was proven and was added to the knowledge base.")
    else:
        print(f"Lemma was not proven and was not added to the knowledge base.")


def prove(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax")
        return

    rv = kb.prove(f)
    if rv:
        print(f"Formula is entailed by the knowledge base.")
    else:
        print(f"Formula is not entailed by the knowledge base.")


def query(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax")
        return

    rv = kb.query(f)

    if rv is None:
        print(f"Error: Query is not entailed by the knowledge base.")
        return

    for k, v in rv.items():
        print(k, "\t", v)


def setup_logging(args: argparse.Namespace) -> None:
    log = logging.getLogger()
    if args.debug:
        log.setLevel(logging.DEBUG)
    elif args.verbose:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.WARNING)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)


if __name__ == '__main__':
    main()
