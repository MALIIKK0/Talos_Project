import os
import subprocess
from langchain.tools import tool


def _repo_path():
    repo = os.getenv("REPO_PATH")
    if not repo:
        raise RuntimeError("REPO_PATH not set")
    return repo


def _run(cmd):
    subprocess.run(
        cmd,
        cwd=_repo_path(),
        check=True,
        text=True
    )


@tool
def apply_apex_patch(file_path: str, content: str) -> str:
    """
    Overwrite an Apex class file with the provided content.
    Path must be relative to repo root.
    """
    if file_path.startswith("/") or ".." in file_path:
        raise ValueError("Invalid file path")

    full_path = os.path.join(_repo_path(), file_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(full_path)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Updated {file_path}"


@tool
def git_create_branch(branch_name: str) -> str:
    """
    Create and switch to a new git branch.
    """
    _run(["git", "checkout", "-b", branch_name])
    return branch_name


@tool
def git_commit(message: str) -> str:
    """
    Stage all changes and create a git commit.
    """
    _run(["git", "add", "."])
    _run(["git", "commit", "-m", message])
    return message


@tool
def git_push(branch_name: str) -> str:
    """
    Push a branch to origin and set upstream.
    """
    _run(["git", "push", "-u", "origin", branch_name])
    return branch_name