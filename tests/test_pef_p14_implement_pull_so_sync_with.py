import branch_fixer.services.git.repository as repository_module
from branch_fixer.services.git.repository import GitRepository
from branch_fixer.services.git.exceptions import GitError


def test_sync_with_remote_never_propagates_not_implemented_error():
    gr = repository_module.GitRepository.__new__(GitRepository)

    # Success path: pull and push both succeed -> True
    gr.pull = lambda *a, **k: None
    gr.push = lambda *a, **k: None
    assert gr.sync_with_remote() is True

    # GitError path: pull raises GitError -> False
    gr.pull = lambda *a, **k: (_ for _ in ()).throw(GitError("pull fail"))
    gr.push = lambda *a, **k: None
    assert gr.sync_with_remote() is False

    # Finding F68: pull() is unimplemented and raises NotImplementedError
    # (repository.py:352). sync_with_remote() must resolve to a bool (False)
    # and must never let NotImplementedError escape to the caller.
    gr.pull = lambda *a, **k: (_ for _ in ()).throw(
        NotImplementedError("pull method is not implemented yet.")
    )
    gr.push = lambda *a, **k: None
    try:
        result = gr.sync_with_remote()
    except NotImplementedError:
        result = "RAISED_NOT_IMPLEMENTED_ERROR"

    assert result is False, (
        "sync_with_remote() must catch NotImplementedError raised by pull() "
        f"and return False, not propagate it (got: {result!r})"
    )
