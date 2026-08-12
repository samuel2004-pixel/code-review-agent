# AI Code Review Agent

An agent that reviews GitHub pull requests like a senior engineer.
It listens for PR webhook events, pulls the diff, runs linting (Ruff)
and security scanning (Bandit) as agent tools, reasons over the results
with an LLM, and posts a structured review comment back to the PR.

## Why this is different from a normal linter
Linters flag fixed rule violations. This agent *reads the diff*, decides
which files are worth deeper scanning, runs the right tools, and writes
a human-style review — bugs, missing error handling, security concerns —
in plain English, the way a reviewer would.

## Architecture
```
GitHub PR opened/updated
      │  (webhook)
      ▼
FastAPI /webhook endpoint
      │
      ▼
LangChain Tool-Calling Agent
   ├── run_ruff     (lint check)
   └── run_bandit   (security scan)
      │
      ▼
Review comment posted back to the PR via GitHub API
```

## Setup
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
export GITHUB_TOKEN=your_github_pat_with_repo_scope

cd app
uvicorn webhook:app --reload
```

Then, in your GitHub repo settings → Webhooks, add:
- Payload URL: `https://<your-host>/webhook`
- Content type: `application/json`
- Events: **Pull requests**

## Manual run (no webhook needed)
```bash
python app/reviewer.py <owner> <repo> <pr_number> --post
```
Drop `--post` to just print the review without commenting on GitHub.

## Docker
```bash
docker build -t ai-code-reviewer .
docker run -p 8000:8000 -e OPENAI_API_KEY=... -e GITHUB_TOKEN=... ai-code-reviewer
```

## Notes / next steps
- Swap `ChatOpenAI` for any LangChain-compatible LLM.
- Add inline (line-level) comments using the GitHub "review comments" API
  instead of a single summary comment.
- Cache reviews per commit SHA to avoid re-reviewing unchanged pushes.
- Add a GitHub App wrapper instead of a personal access token for
  production/multi-repo use.
