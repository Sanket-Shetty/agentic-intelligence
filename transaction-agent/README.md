# Transaction Intelligence AI Agent

An OpenAI function-calling agent that builds a unified transaction intelligence report for a Bungee transaction hash or user address by querying:

- Metabase backed by Postgres
- Loki transaction API
- Mixpanel analytics export/profile APIs

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with your real credentials. No credentials are hardcoded in this project.

## Run

```bash
python main.py 0xTRANSACTION_HASH
```

You can also pass a wallet address:

```bash
python main.py 0xUSER_ADDRESS
```

The agent uses OpenAI tool calling to decide which data sources to query and how to merge the results into a coherent report.

## Run the API and Frontend

Start the backend:

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend calls `POST http://localhost:8000/api/intelligence`.

## Sentry Auto-Triage Workflow

The app can now connect to Sentry and GitHub for an operator-assisted auto-fix loop:

1. Pull unresolved Sentry issues.
2. Fetch recent issue events and stack/event context.
3. Use OpenAI to decide whether the issue is a likely real bug.
4. Generate a Codex-ready fix prompt, test plan, PR title, and PR body.
5. Create a GitHub PR from a branch that already contains the fix.
6. After the PR is merged, mark the Sentry issue as resolved.

Add these values to `.env`:

```env
SENTRY_DSN=
SENTRY_BASE_URL=https://sentry.io
SENTRY_AUTH_TOKEN=
SENTRY_ORG=
SENTRY_PROJECT=
SENTRY_TRIAGE_MODEL=gpt-4.1-mini

GITHUB_TOKEN=
GITHUB_REPOSITORY=Sanket-Shetty/agentic-intelligence
GITHUB_BASE_BRANCH=main
GITHUB_REVIEWER_HANDLE=
```

The Sentry token needs read access for issue triage and write access for resolving issues. The GitHub token needs permission to open pull requests and request reviewers.

### API Endpoints

```bash
curl -X POST http://localhost:8000/api/sentry/issues \
  -H 'Content-Type: application/json' \
  -d '{"query":"is:unresolved","limit":10}'

curl -X POST http://localhost:8000/api/sentry/issues/<issue_id>/triage \
  -H 'Content-Type: application/json' \
  -d '{"events_limit":5}'

curl -X POST http://localhost:8000/api/github/pull-request \
  -H 'Content-Type: application/json' \
  -d '{"head_branch":"codex/fix-sentry-123","title":"Fix Sentry issue","body":"..."}'

curl -X POST http://localhost:8000/api/sentry/issues/<issue_id>/resolve
```

### CLI

```bash
python sentry_agent.py list --limit 10
python sentry_agent.py triage <issue_id>
python sentry_agent.py create-pr --branch codex/fix-sentry-123 --title "Fix Sentry issue" --body "..."
python sentry_agent.py resolve <issue_id>
```

The production-safe pattern is to let Codex or CI create the fix branch and push it, then use `create-pr` to tag the reviewer. Resolve the Sentry issue only from a merge hook or after you confirm the PR has landed.
