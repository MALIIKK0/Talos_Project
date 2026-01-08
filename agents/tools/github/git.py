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
<<<<<<< HEAD
    Path must be relative to repo root.
=======
    Path must be relative to force-app/main/default/classes inside the repo.
>>>>>>> 754bb64d906ae5488224821736a0146af0de0344
    """
    if file_path.startswith("/") or ".." in file_path:
        raise ValueError("Invalid file path")

<<<<<<< HEAD
    full_path = os.path.join(_repo_path(), file_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(full_path)
=======
    full_path = os.path.join(_repo_path(), "force-app", "main", "default", "classes", file_path)

    # Ensure the folder exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
>>>>>>> 754bb64d906ae5488224821736a0146af0de0344

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Updated {file_path}"

<<<<<<< HEAD
=======
    
>>>>>>> 754bb64d906ae5488224821736a0146af0de0344

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
<<<<<<< HEAD
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
=======
    Stage all changes and create a git commit if there are changes.
    """
    _run(["git", "add", "."])

    # Check if there is anything staged to commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=_repo_path()
    )
    if result.returncode == 0:
        # No changes to commit
        return "Nothing to commit"

    # Proceed with commit
    _run(["git", "commit", "-m", message])
    return message

@tool
def git_push(branch_name: str) -> str:
    """
    Push a branch to origin and set upstream, then return to the original branch.
    """
    # Get current branch
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=_repo_path(),
        capture_output=True,
        text=True,
        check=True
    )
    current_branch = result.stdout.strip()

    # Push the new branch
    _run(["git", "push", "-u", "origin", branch_name])

    # Return to the original branch
    #if current_branch and current_branch != branch_name:
    #    _run(["git", "checkout", current_branch])
    _run(["git", "checkout", "main"])
    

    return f"Pushed {branch_name}, returned to {current_branch}"
>>>>>>> 754bb64d906ae5488224821736a0146af0de0344
