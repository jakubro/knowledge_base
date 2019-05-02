import pytest

import knowledge_base.utils as utils


@pytest.mark.parametrize('before', [None, 0, 1])
@pytest.mark.parametrize('default', [None, 0, 1])
def test_incrementdefault(before, default):
    obj = {'key': before}
    obj = {k: v for k, v in obj.items() if v is not None}

    args = (x for x in (obj, 'key', default) if x is not None)
    rv = utils.incrementdefault(*args)
    assert obj['key'] is rv

    if before is not None:
        assert rv == before + 1
    elif default is not None:
        assert rv == default + 1
    else:
        assert rv == 1


@pytest.mark.parametrize('before', [None, [], ['foo']])
@pytest.mark.parametrize('default', [None, [], ['foo']])
def test_appenddefault(before, default):
    obj = {'key': before}
    obj = {k: v for k, v in obj.items() if v is not None}

    val = 'bar'
    args = (x for x in (obj, 'key', val, default) if x is not None)
    rv = utils.appenddefault(*args)
    assert obj['key'] is rv

    if before is not None:
        assert rv is before
    elif default is not None:
        assert rv is default
    else:
        assert rv == [val]
