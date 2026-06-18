from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from integrations.github import GitHubTool
from integrations.sentry import SentryTool
from integrations.sentry_triage import summarize_sentry_issue


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Sentry triage helper for the transaction intelligence app.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List unresolved Sentry issues.")
    list_parser.add_argument("--query", default="is:unresolved")
    list_parser.add_argument("--limit", type=int, default=10)

    triage_parser = subparsers.add_parser("triage", help="Triage one Sentry issue with OpenAI.")
    triage_parser.add_argument("issue_id")
    triage_parser.add_argument("--events", type=int, default=5)

    resolve_parser = subparsers.add_parser("resolve", help="Mark a Sentry issue resolved.")
    resolve_parser.add_argument("issue_id")

    pr_parser = subparsers.add_parser("create-pr", help="Open a GitHub PR for an already pushed branch.")
    pr_parser.add_argument("--branch", required=True)
    pr_parser.add_argument("--title", required=True)
    pr_parser.add_argument("--body", required=True)
    pr_parser.add_argument("--base")
    pr_parser.add_argument("--draft", action="store_true")

    args = parser.parse_args()
    sentry = SentryTool()

    if args.command == "list":
        print(json.dumps(sentry.list_issues(query=args.query, limit=args.limit), indent=2, default=str))
    elif args.command == "triage":
        issue = sentry.get_issue(args.issue_id)
        events = sentry.get_issue_events(args.issue_id, limit=args.events)
        print(json.dumps(summarize_sentry_issue(issue, events), indent=2, default=str))
    elif args.command == "resolve":
        print(json.dumps(sentry.resolve_issue(args.issue_id), indent=2, default=str))
    elif args.command == "create-pr":
        github = GitHubTool()
        pull_request = github.create_pull_request(
            head_branch=args.branch,
            title=args.title,
            body=args.body,
            base_branch=args.base,
            draft=args.draft,
        )
        print(json.dumps(pull_request, indent=2, default=str))


if __name__ == "__main__":
    main()
