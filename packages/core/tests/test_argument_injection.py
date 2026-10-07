import subprocess
from unittest.mock import patch

import pytest

from jupyterlab_git_core.git import Git, GitParameterError


@pytest.mark.parametrize(
    "method, args",
    [
        ("branch_delete", ("path", "--evil")),
        ("reset_to_commit", ("--evil", "path")),
        ("checkout_new_branch", ("ok", "--evil", "path")),
        ("checkout_branch", ("--evil", "path")),
        ("merge", ("--evil", "path")),
        ("push", ("--evil", "HEAD", "path")),
        ("set_tag", ("path", "--evil", "HEAD")),
        ("rebase", ("--evil", "path")),
        ("diff", ("path", "--evil")),
        ("changed_files", ("path", None, None, "--evil")),
        ("detailed_log", ("--evil", "path")),
        ("show", ("path", "--evil", "f")),
        ("_is_binary", ("f", "--evil", "path")),
    ],
)
@patch("jupyterlab_git_core.git.execute")
async def test_option_like_ref_is_rejected(mock_execute, method, args):
    # A ref starting with "-" would be parsed by git as an option, so the
    # method must reject it before any git command runs.
    with pytest.raises(GitParameterError):
        await getattr(Git(), method)(*args)
    mock_execute.assert_not_called()


async def _init_repo(path):
    run = lambda c: subprocess.run(c, cwd=path, check=True, capture_output=True)
    run(["git", "init", "-q"])
    run(["git", "config", "user.email", "a@b.c"])
    run(["git", "config", "user.name", "t"])
    (path / "f").write_text("x")
    run(["git", "add", "f"])
    run(["git", "commit", "-qm", "i"])


@pytest.mark.parametrize(
    "call",
    [
        lambda repo, out: Git().diff(str(repo), previous=f"--output={out}"),
        lambda repo, out: Git().changed_files(str(repo), single_commit=f"--output={out}"),
        lambda repo, out: Git().detailed_log(f"--output={out}", str(repo)),
        lambda repo, out: Git().show(str(repo), f"--output={out}"),
        lambda repo, out: Git()._is_binary("f", f"--output={out}", str(repo)),
    ],
)
async def test_output_option_no_longer_writes_a_file(tmp_path, call):
    # --output=<path> made git write its output to an arbitrary file. Run the
    # real exploit against a real repo and check no file is written.
    repo = tmp_path / "repo"
    repo.mkdir()
    await _init_repo(repo)
    marker = tmp_path / "pwned"

    with pytest.raises(GitParameterError):
        await call(repo, marker)

    assert not marker.exists()
