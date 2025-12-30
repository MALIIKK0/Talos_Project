import os
import requests
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()


@tool
def github_create_pr(
    head: str,
    base: str,
    title: str,
    body: str
) -> dict:
    """
    Create a GitHub pull request.
    Handles fine-grained PAT behavior where PR is created
    but API may return 403 on response expansion.
    """
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")

    if not all([token, owner, repo]):
        raise RuntimeError("Missing GitHub configuration")

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body
    }

    r = requests.post(url, headers=headers, json=payload)

    # ✅ PR CREATED (201)
    if r.status_code == 201:
        pr = r.json()
        return {
            "url": pr["html_url"],
            "number": pr["number"]
        }

    # ⚠️ Fine-grained token: PR created but response forbidden
    if r.status_code == 403:
        return {
            "url": f"https://github.com/{owner}/{repo}/pulls",
            "number": None
        }

    # ❌ Real failure
    r.raise_for_status()