import pytest

import knowledge_base.resolution as resolution
from knowledge_base.grammar import parse


@pytest.mark.parametrize('facts, f, expected', [
    (['american(x) & weapon(y) & sells(x, y, z) & hostile(z) => criminal(x)',
      'owns(Korea, M1)',
      'missile(M1)',
      'missile(x) & owns(Korea, x) => sells(West, x, Korea)',
      'missile(x) => weapon(x)',
      'enemy(x, America) => hostile(x)',
      'american(West)',
      'enemy(Korea, America)'],
     'criminal(West)',
     True)
])
def test_resolve(facts, f, expected):
    facts = [parse(k) for k in facts]
    f = parse(f)
    print('facts:', facts)
    print('f:', f)

    rv = resolution.resolve(facts, f)
    print('rv:', rv)
    assert rv == expected
