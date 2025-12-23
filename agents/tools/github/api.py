# tools/github/api.py


def create_branch(name: str):
    return {"branch": name}




def create_pr(title: str, body: str, branch: str):
    return {"pr_url": f"https://github.com/example/repo/pull/{branch}"}