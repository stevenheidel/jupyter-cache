import os
from textwrap import dedent

import pytest

from jupyter_cache.cache import JupyterCacheBase
from jupyter_cache.base import NbValidityError


NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


def test_basic_workflow(tmp_path):
    cache = JupyterCacheBase(str(tmp_path))
    with pytest.raises(NbValidityError):
        cache.commit_notebook_file(path=os.path.join(NB_PATH, "basic.ipynb"))
    cache.commit_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    assert cache.list_commit_records()[0].uri == "basic.ipynb"
    pk = cache.match_commit_file(path=os.path.join(NB_PATH, "basic.ipynb"))
    nb_bundle = cache.get_commit_bundle(pk)
    assert nb_bundle.nb.metadata["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    assert set(nb_bundle.commit.keys()) == {
        "pk",
        "hashkey",
        "uri",
        "data",
        "created",
        "accessed",
        "description",
    }
    assert cache.get_commit_codecell(pk, 0).source == "a=1\nprint(a)"

    diff = cache.diff_nbfile_with_commit(
        pk, os.path.join(NB_PATH, "basic_failing.ipynb"), as_str=True, use_color=False
    )
    assert diff == dedent(
        """\
        nbdiff
        --- committed pk=1
        +++ other: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic_failing.ipynb
        ## inserted before nb/cells/1:
        +  code cell:
        +    source:
        +      raise Exception('oopie')

        ## deleted nb/cells/1:
        -  code cell:
        -    execution_count: 2
        -    source:
        -      a=1
        -      print(a)
        -    outputs:
        -      output 0:
        -        output_type: stream
        -        name: stdout
        -        text:
        -          1

        """
    )
    cache.remove_commit(pk)
    assert cache.list_commit_records() == []

    cache.commit_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    cache.stage_notebook_file(os.path.join(NB_PATH, "basic.ipynb"))
    assert [r.pk for r in cache.list_staged_records()] == [1]
    assert [r.pk for r in cache.list_nbs_to_exec()] == []

    cache.stage_notebook_file(os.path.join(NB_PATH, "basic_failing.ipynb"))
    assert [r.pk for r in cache.list_staged_records()] == [1, 2]
    assert [r.pk for r in cache.list_nbs_to_exec()] == [2]

    bundle = cache.get_staged_notebook(os.path.join(NB_PATH, "basic_failing.ipynb"))
    assert bundle.nb.metadata

    cache.clear_cache()
    assert cache.list_commit_records() == []


def test_execution(tmp_path):
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "basic_unrun.ipynb"))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "basic_failing.ipynb"))
    executor = load_executor("basic", db)
    assert executor.run() == [os.path.join(NB_PATH, "basic_unrun.ipynb")]
    assert db.list_commit_records()[0].pk == 1
    assert db.get_commit_codecell(1, 0) == {
        "cell_type": "code",
        "execution_count": 1,
        "metadata": {},
        "outputs": [{"name": "stdout", "output_type": "stream", "text": "1\n"}],
        "source": "a=1\nprint(a)",
    }
