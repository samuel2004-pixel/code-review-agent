"""
AI Code Review Agent
---------------------
Listens for GitHub pull request events, pulls the diff, runs static
analysis tools as agent "tools", and uses an LLM to review the changes
like a senior engineer — then posts inline comments back to the PR.
"""

import os
import subprocess
import requests
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch the unified diff for a pull request."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers={**HEADERS, "Accept": "application/vnd.github.diff"})
    resp.raise_for_status()
    return resp.text


def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> None:
    """Post a general (non-inline) review comment on a PR."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    resp = requests.post(url, headers=HEADERS, json={"body": body})
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Static analysis tools the agent can call
# ---------------------------------------------------------------------------

@tool
def run_ruff(file_path: str) -> str:
    """Run the Ruff linter on a Python file and return findings."""
    try:
        result = subprocess.run(
            ["ruff", "check", file_path], capture_output=True, text=True, timeout=30
        )
        return result.stdout or "No lint issues found."
    except FileNotFoundError:
        return "Ruff is not installed. Run: pip install ruff"
    except Exception as e:
        return f"Error running ruff: {e}"


@tool
def run_bandit(file_path: str) -> str:
    """Run the Bandit security scanner on a Python file and return findings."""
    try:
        result = subprocess.run(
            ["bandit", "-q", file_path], capture_output=True, text=True, timeout=30
        )
        return result.stdout or "No security issues found."
    except FileNotFoundError:
        return "Bandit is not installed. Run: pip install bandit"
    except Exception as e:
        return f"Error running bandit: {e}"


SYSTEM_PROMPT = """You are a senior software engineer reviewing a pull
request diff. You have tools to run linting (run_ruff) and security
scanning (run_bandit) on individual files mentioned in the diff.

Review the diff for:
- bugs or logic errors
- code style / readability issues
- potential security problems
- missing error handling or edge cases

Use the tools where relevant. Write your review as a concise, structured
comment (bullet points), citing specific lines/files. Be direct and
actionable — this will be posted as a real PR comment."""


def build_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [run_ruff, run_bandit]
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def review_pull_request(owner: str, repo: str, pr_number: int, post_comment: bool = False) -> str:
    """Fetch a PR's diff, review it with the agent, and optionally post the review."""
    diff = get_pr_diff(owner, repo, pr_number)
    executor = build_agent()
    result = executor.invoke({
        "input": f"Review this pull request diff:\n\n{diff[:8000]}"  # truncate very large diffs
    })
    review = result["output"]

    if post_comment:
        post_pr_comment(owner, repo, pr_number, f"### 🤖 AI Code Review\n\n{review}")

    return review


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python reviewer.py <owner> <repo> <pr_number> [--post]")
        sys.exit(1)
    owner, repo, pr_number = sys.argv[1], sys.argv[2], int(sys.argv[3])
    should_post = "--post" in sys.argv
    print(review_pull_request(owner, repo, pr_number, post_comment=should_post))
