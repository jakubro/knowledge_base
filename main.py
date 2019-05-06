import argparse
import logging
from typing import List

import pyparsing as pp

import knowledge_base.grammar as grammar
import knowledge_base.resolution as resolution
import knowledge_base.syntax as syntax

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
        return resolution.resolve(self._facts, f)


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
    print("Usage: ")  # todo

    kb = KnowledgeBase()
    while True:
        print(">> ", end="")
        v = input()
        command, *rest = v.split(maxsplit=1)

        command = command.lower()
        rest = rest[0].strip() if rest else None

        if command == 'help':
            pass

        elif command == 'list':
            print("\n".join(str(f) for f in kb.facts))

        elif command == 'axiom':
            if not rest:
                print("Expected 1 argument")
                continue

            try:
                f = grammar.parse(rest)
            except ValueError:
                print("Invalid syntax")
                continue

            kb.add_axiom(f)
            print("Axiom was added to the knowledge base.")

        elif command == 'lemma':
            if not rest:
                print("Expected 1 argument")
                continue

            try:
                f = grammar.parse(rest)
            except ValueError:
                print("Invalid syntax")
                continue

            rv = kb.add_lemma(f)
            if rv:
                print(f"Lemma was proven and was added to the "
                      f"knowledge base.")
            if rv:
                print(f"Lemma was not proven and was not added to the "
                      f"knowledge base.")

        elif command == 'prove':
            if not rest:
                print("Expected 1 argument")
                continue

            try:
                f = grammar.parse(rest)
            except ValueError:
                print("Invalid syntax")
                continue

            rv = kb.prove(f)
            if rv:
                print(f"Formula is entailed by the knowledge base.")
            if rv:
                print(f"Formula is not entailed by the knowledge base.")


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
