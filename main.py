import argparse
import json
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
        '-p', '--path', type=str,
        help="Path to a file where to persist content of the knowledge base.")
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
    repl_usage()

    facts = None
    if args.path:
        try:
            with open(args.path) as f:
                facts = syntax.loads(f.read())
        except IOError:
            pass

    kb = KnowledgeBase(facts=facts)
    try:
        while True:
            repl_loop(kb)
    except KeyboardInterrupt:
        if args.path:
            with open(args.path, 'w') as f:
                f.write(syntax.dumps(kb.facts,
                                     compact=False,
                                     format_='json'))


def repl_loop(kb: KnowledgeBase) -> None:
    print(">> ", end="")
    command = input()

    command, _ = command.split('#', maxsplit=1)  # remove comments
    command, *args = command.split(maxsplit=1)  # <verb> [args ...]

    command = command.strip().lower()
    args = [k.strip() for k in args]

    if command == 'list':
        list_content(kb)
    elif command == 'axiom':
        add_axiom(kb, *args)
    elif command == 'lemma':
        add_lemma(kb, *args)
    elif command == 'prove':
        prove(kb, *args)
    elif command == 'query':
        query(kb, *args)
    elif command:
        if command != 'help':
            print(f"Error: '{command}' is not a valid command")
        repl_usage()


def repl_usage():
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
    print()


def add_axiom(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument\n")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax\n")
        return

    kb.add_axiom(f)


def add_lemma(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument\n")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax\n")
        return

    rv = kb.add_lemma(f)
    if rv:
        print(f"Lemma was proven and was added to the "
              f"knowledge base.\n")
    else:
        print(f"Lemma was not proven and was not added to the "
              f"knowledge base.\n")


def prove(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument\n")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax\n")
        return

    rv = kb.prove(f)
    if rv:
        print(f"Formula is entailed by the knowledge base.\n")
    else:
        print(f"Formula is not entailed by the knowledge base.\n")


def query(kb: KnowledgeBase, arg: str) -> None:
    if not arg:
        print("Error: Expected 1 argument\n")
        return

    try:
        f = grammar.parse(arg)
    except grammar.InvalidSyntaxError:
        print("Error: Invalid syntax\n")
        return

    rv = kb.query(f)

    if rv is None:
        print(f"Error: Query is not entailed by the knowledge base.\n")
        return

    for k, v in rv.items():
        print(f"{k} = {v}")
    print()


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
