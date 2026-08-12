"""
FastAPI webhook listener for GitHub pull_request events.
Point a GitHub webhook at POST /webhook, subscribed to "Pull requests".
"""

from fastapi import FastAPI, Request, BackgroundTasks
from reviewer import review_pull_request

app = FastAPI(title="AI Code Review Agent")


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    action = payload.get("action")
    if action not in ("opened", "synchronize"):
        return {"status": "ignored", "action": action}

    pr = payload.get("pull_request", {})
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    if not pr or "/" not in repo_full_name:
        return {"status": "ignored", "reason": "missing PR or repo info"}

    owner, repo = repo_full_name.split("/")
    pr_number = pr.get("number")

    background_tasks.add_task(review_pull_request, owner, repo, pr_number, True)
    return {"status": "review_queued", "pr": pr_number}
